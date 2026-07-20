#!/usr/bin/env python3
"""Evaluate the zero-shot classifier on a user-supplied labeled image manifest.

The CSV must contain ``path,label`` columns. Paths are resolved relative to the
manifest; labels must exactly match one of the 20 canonical outputs from
``app.model.ENTITY_PROMPTS``. Use a held-out, real institutional photo set for
research claims. This script never downloads data and never trains a model.

Example manifest:
    path,label
    images/laptop-001.jpg,Laptop
    images/router-001.jpg,Router / Switch

Run from ``backend/``:
    python3 scripts/evaluate_classifier.py --manifest data/evaluation/labels.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="CSV with path,label columns")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    parser.add_argument("--limit", type=int, help="deterministically evaluate only the first N sorted rows")
    parser.add_argument("--seed", type=int, default=42, help="runtime-library random seed")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="set HF_HUB_OFFLINE=1; cached model weights are required",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate paths and labels without loading the model",
    )
    return parser


def load_manifest(path: Path) -> list[dict[str, str]]:
    manifest_path = path.expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        if not {"path", "label"}.issubset(fields):
            raise ValueError("Manifest must contain path,label columns")
        rows = [
            {"path": (row.get("path") or "").strip(), "label": (row.get("label") or "").strip()}
            for row in reader
        ]
    if not rows:
        raise ValueError("Manifest contains no labeled rows")
    return sorted(rows, key=lambda row: (row["label"], row["path"]))


def validate_rows(
    rows: list[dict[str, str]], manifest: Path, allowed_labels: set[str]
) -> list[tuple[Path, str]]:
    base_dir = manifest.expanduser().resolve().parent
    validated: list[tuple[Path, str]] = []
    errors: list[str] = []
    for line_number, row in enumerate(rows, start=2):
        label = row["label"]
        raw_path = row["path"]
        if label not in allowed_labels:
            errors.append(f"row {line_number}: unsupported label {label!r}")
            continue
        if not raw_path:
            errors.append(f"row {line_number}: empty path")
            continue
        image_path = Path(raw_path).expanduser()
        if not image_path.is_absolute():
            image_path = base_dir / image_path
        image_path = image_path.resolve()
        if not image_path.is_file():
            errors.append(f"row {line_number}: image not found: {image_path}")
            continue
        validated.append((image_path, label))
    if errors:
        preview = "\n".join(errors[:20])
        remainder = len(errors) - min(len(errors), 20)
        suffix = f"\n... and {remainder} more" if remainder else ""
        raise ValueError(f"Manifest validation failed:\n{preview}{suffix}")
    return validated


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"

    random.seed(args.seed)
    import numpy as np

    np.random.seed(args.seed)
    try:
        import torch

        torch.manual_seed(args.seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
    except Exception:
        pass

    from app import model as model_module

    rows = load_manifest(args.manifest)
    if args.limit is not None:
        rows = rows[: args.limit]
    samples = validate_rows(rows, args.manifest, set(model_module.ENTITY_PROMPTS))
    print(f"Validated {len(samples)} labeled images across {len(set(label for _, label in samples))} classes.")
    if args.validate_only:
        print("Validation only: model was not loaded and no metrics were calculated.")
        return 0

    from PIL import Image

    per_class = defaultdict(lambda: {"support": 0, "recognized": 0, "correct": 0})
    records: list[dict[str, object]] = []
    correct = 0
    recognized = 0
    inference_errors = 0

    for index, (image_path, expected) in enumerate(samples, start=1):
        try:
            with Image.open(image_path) as source:
                image = source.convert("RGB")
            predicted, confidence, model_used = model_module.classifier.predict(
                image, return_confidence=True
            )
        except Exception as exc:
            inference_errors += 1
            predicted = "ERROR"
            confidence = 0.0
            model_used = f"error:{type(exc).__name__}"

        is_recognized = predicted not in {"Unrecognized", "ERROR"}
        is_correct = predicted == expected
        recognized += int(is_recognized)
        correct += int(is_correct)
        per_class[expected]["support"] += 1
        per_class[expected]["recognized"] += int(is_recognized)
        per_class[expected]["correct"] += int(is_correct)
        records.append(
            {
                "path": str(image_path),
                "expected": expected,
                "predicted": predicted,
                "confidence": float(confidence),
                "model_used": model_used,
                "correct": is_correct,
            }
        )
        print(f"[{index}/{len(samples)}] expected={expected!r} predicted={predicted!r}")

    total = len(samples)
    summary = {
        "evidence_boundary": (
            "Metrics describe only the supplied manifest. Research claims require a "
            "predefined, held-out, representative real-image evaluation set."
        ),
        "model_preset": model_module.DEFAULT_MODEL,
        "model_id": model_module.MODEL_ID,
        "seed": args.seed,
        "total": total,
        "correct": correct,
        "recognized": recognized,
        "rejected_or_unrecognized": total - recognized - inference_errors,
        "inference_errors": inference_errors,
        "accuracy_all_images": ratio(correct, total),
        "coverage": ratio(recognized, total),
        "accuracy_when_recognized": ratio(correct, recognized),
        "per_class": {
            label: {
                **counts,
                "accuracy_all_images": ratio(counts["correct"], counts["support"]),
                "coverage": ratio(counts["recognized"], counts["support"]),
            }
            for label, counts in sorted(per_class.items())
        },
        "predictions": records,
    }

    print(json.dumps({key: value for key, value in summary.items() if key != "predictions"}, indent=2))
    if args.output:
        output_path = args.output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
            handle.write("\n")
        print(f"Wrote evaluation JSON: {output_path}")
    return 0 if inference_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
