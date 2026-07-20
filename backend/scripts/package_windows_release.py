#!/usr/bin/env python3
"""Validate, hash, and ZIP a staged Windows one-folder release."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import zipfile

BLOCKED_SUFFIXES = {".db", ".sqlite", ".log"}
MANIFEST_NAME = "RELEASE_MANIFEST.sha256"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def release_files(stage: Path) -> list[Path]:
    stage = stage.resolve()
    files: list[Path] = []
    blocked: list[str] = []
    for candidate in sorted(stage.rglob("*")):
        if candidate.is_symlink():
            blocked.append(f"symbolic link: {candidate.relative_to(stage)}")
        elif candidate.is_file():
            relative = candidate.relative_to(stage)
            lowered = candidate.name.casefold()
            if lowered == ".env" or lowered.startswith(".env."):
                blocked.append(f"environment file: {relative}")
            elif candidate.suffix.casefold() in BLOCKED_SUFFIXES:
                blocked.append(f"mutable runtime file: {relative}")
            elif candidate.name != MANIFEST_NAME:
                files.append(candidate)
    if blocked:
        raise ValueError("Blocked files in release stage: " + "; ".join(blocked))
    if not any(path.name.casefold() == "ewastemanagement.exe" for path in files):
        raise ValueError("EWasteManagement.exe is missing from the release stage")
    return files


def package_release(stage: Path, output: Path) -> Path:
    stage = stage.expanduser().resolve()
    output = output.expanduser().resolve()
    if not stage.is_dir():
        raise ValueError(f"Release stage does not exist: {stage}")
    files = release_files(stage)

    manifest_lines = [
        f"{sha256_file(path)}  {path.relative_to(stage).as_posix()}"
        for path in files
    ]
    manifest = stage / MANIFEST_NAME
    manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    output.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for path in [*files, manifest]:
                relative = path.relative_to(stage)
                archive.write(path, (Path(stage.name) / relative).as_posix())
        temporary.replace(output)
        with zipfile.ZipFile(output) as archive:
            corrupt = archive.testzip()
            if corrupt is not None:
                raise RuntimeError(f"ZIP integrity check failed at {corrupt}")
    except Exception:
        temporary.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        raise

    archive_hash = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{archive_hash}  {output.name}\n",
        encoding="ascii",
        newline="\n",
    )
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = package_release(args.stage, args.output)
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Release packaging failed: {exc}", file=sys.stderr)
        return 2
    print(f"Release archive: {output}")
    print(f"SHA-256 file: {output.with_suffix(output.suffix + '.sha256')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
