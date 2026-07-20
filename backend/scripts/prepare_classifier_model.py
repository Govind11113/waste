#!/usr/bin/env python3
"""Prepare the pinned, flat, integrity-checked offline classifier snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from huggingface_hub import snapshot_download

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MODEL_PRESET = "siglip2-base"
MODEL_REPOSITORY = "google/siglip2-base-patch16-224"
MODEL_REVISION = "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2"
MODEL_LICENSE = "Apache-2.0"
DEFAULT_OUTPUT = BACKEND_ROOT / "models" / "classifier" / MODEL_PRESET
LICENSE_SOURCE = BACKEND_ROOT / "licenses" / "Apache-2.0.txt"
SNAPSHOT_FILES = (
    "README.md",
    "config.json",
    "model.safetensors",
    "preprocessor_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict:
    """Build the runtime manifest for every distributable snapshot file."""
    files = {
        candidate.relative_to(root).as_posix(): _sha256(candidate)
        for candidate in sorted(root.rglob("*"))
        if candidate.is_file() and candidate.name != "model_manifest.json"
    }
    if not files:
        raise ValueError("classifier snapshot contains no files")
    return {"files": files}


def _verify(root: Path) -> tuple[bool, list[str]]:
    # Keep this script runnable by path without requiring package installation.
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.runtime import verify_file_manifest

    return verify_file_manifest(root)


def prepare_snapshot(output: Path, force: bool = False) -> Path:
    output = output.expanduser().resolve()
    if output.exists():
        verified, errors = _verify(output)
        metadata_path = output / "MODEL_METADATA.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            metadata = {}
        if verified and metadata.get("revision") == MODEL_REVISION:
            print(f"Pinned classifier snapshot already verified: {output}")
            return output
        if not force:
            detail = "; ".join(errors) or "metadata revision does not match"
            raise RuntimeError(
                f"Existing classifier snapshot is not valid ({detail}). "
                "Re-run with --force to replace only this generated directory."
            )
        shutil.rmtree(output)

    if not LICENSE_SOURCE.is_file():
        raise RuntimeError(f"Required license text is missing: {LICENSE_SOURCE}")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(f".{output.name}.preparing")
    if staging.exists():
        shutil.rmtree(staging)

    try:
        snapshot_download(
            repo_id=MODEL_REPOSITORY,
            revision=MODEL_REVISION,
            local_dir=staging,
            allow_patterns=list(SNAPSHOT_FILES),
            max_workers=4,
        )
        shutil.rmtree(staging / ".cache", ignore_errors=True)
        missing = [name for name in SNAPSHOT_FILES if not (staging / name).is_file()]
        if missing:
            raise RuntimeError(f"Downloaded snapshot is missing: {', '.join(missing)}")

        shutil.copy2(LICENSE_SOURCE, staging / "LICENSE.apache-2.0.txt")
        metadata = {
            "formatVersion": 1,
            "modelPreset": MODEL_PRESET,
            "repository": MODEL_REPOSITORY,
            "revision": MODEL_REVISION,
            "license": MODEL_LICENSE,
            "licenseFile": "LICENSE.apache-2.0.txt",
            "task": "zero-shot-image-classification",
            "upstreamModelCard": f"https://huggingface.co/{MODEL_REPOSITORY}/tree/{MODEL_REVISION}",
        }
        (staging / "MODEL_METADATA.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / "model_manifest.json").write_text(
            json.dumps(build_manifest(staging), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        verified, errors = _verify(staging)
        if not verified:
            raise RuntimeError(f"Prepared snapshot failed verification: {'; '.join(errors)}")
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    print(f"Prepared {MODEL_REPOSITORY}@{MODEL_REVISION}")
    print(f"Output: {output}")
    print(f"Files: {len(build_manifest(output)['files'])}")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace only an existing invalid generated classifier directory",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the selected directory without downloading",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verify_only:
        verified, errors = _verify(args.output.expanduser().resolve())
        if verified:
            print(f"Classifier snapshot verified: {args.output}")
            return 0
        print("Classifier snapshot verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2
    try:
        prepare_snapshot(args.output, force=args.force)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Classifier preparation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
