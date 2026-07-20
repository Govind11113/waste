#!/usr/bin/env python3
"""Print per-stage classifier diagnostics for local or public images.

This utility reports scores; it does not calculate accuracy. Network access is
opt-in with ``--network`` and uses Requests' normal certificate verification.
For reproducible accuracy/coverage metrics, use a fixed labeled manifest with
``scripts/evaluate_classifier.py``.

Run from ``backend/``:
    python3 scripts/diag_classifier.py --image ./photo.jpg
    python3 scripts/diag_classifier.py --network
"""

from __future__ import annotations

import argparse
import io
import os
import random
import sys
from collections.abc import Sequence
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

NETWORK_IMAGES = (
    ("mouse_internals", "https://commons.wikimedia.org/wiki/Special:FilePath/Optical_mouse_internals.jpg"),
    ("computer_mouse", "https://commons.wikimedia.org/wiki/Special:FilePath/3-Tasten-Maus_Microsoft.jpg"),
    ("motherboard", "https://commons.wikimedia.org/wiki/Special:FilePath/ASRock_K7VT4A_Pro_Mainboard.jpg"),
    ("pcb_closeup", "https://commons.wikimedia.org/wiki/Special:FilePath/Printed_Circuit_Board.jpg"),
    ("hand_control", "https://commons.wikimedia.org/wiki/Special:FilePath/Human-Hands-Front-Back.jpg"),
    ("banana_control", "https://commons.wikimedia.org/wiki/Special:FilePath/Banana-Single.jpg"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        action="append",
        type=Path,
        default=[],
        help="local image path; repeat for multiple images",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="download the built-in Wikimedia diagnostics with TLS verification",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="set HF_HUB_OFFLINE=1 before model loading; cached weights are required",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed for runtime libraries")
    parser.add_argument("--timeout", type=float, default=30.0, help="network timeout in seconds")
    return parser


def fetch_verified(url: str, timeout: float) -> bytes:
    import requests

    response = requests.get(
        url,
        headers={"User-Agent": "ewaste-classifier-diagnostic/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.content


def report(label: str, image, model_module) -> None:
    quality = model_module.assess_image_quality(image)
    gate = model_module.gate_electronics(image)
    device = model_module.classify_device(image)
    print(f"[{label}] size={image.size}")
    print(f"  quality: {quality}")
    print(
        "  gate: "
        f"is_electronic={gate['is_electronic']} "
        f"electronic={gate['electronic_score']} "
        f"non_electronic={gate['non_electronic_score']} margin={gate['margin']}"
    )
    print(
        "  classify: "
        f"entity={device['entity']!r} confidence={device['confidence']} "
        f"top2={device['top2_entity']!r}/{device['top2_confidence']} "
        f"model_used={device['model_used']}"
    )
    print("-" * 90)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.image and not args.network:
        parser.error("provide at least one --image PATH or opt in with --network")
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

    from PIL import Image
    from app import model as model_module

    print(f"MODEL={model_module.MODEL_ID} FAMILY={model_module.FAMILY}")
    print(
        "thresholds: "
        f"ELECTRONIC={model_module.ELECTRONIC_THRESHOLD} "
        f"ELECTRONIC_MARGIN={model_module.ELECTRONIC_MARGIN} "
        f"CLASSIFY={model_module.CLASSIFY_THRESHOLD} "
        f"CLASSIFY_LOW={model_module.CLASSIFY_LOW_THRESHOLD} "
        f"CLASSIFY_MARGIN={model_module.MARGIN_THRESHOLD}"
    )
    print("=" * 90)

    successes = 0
    failures = 0
    for path in args.image:
        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
            report(path.stem, image, model_module)
            successes += 1
        except Exception as exc:
            failures += 1
            print(f"[{path}] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    if args.network:
        for label, url in NETWORK_IMAGES:
            try:
                image = Image.open(io.BytesIO(fetch_verified(url, args.timeout))).convert("RGB")
                report(label, image, model_module)
                successes += 1
            except Exception as exc:
                failures += 1
                print(f"[{label}] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)

    print(f"Diagnostics completed: {successes} processed, {failures} failed.")
    print("These diagnostics are unscored and must not be reported as accuracy results.")
    return 0 if successes > 0 and failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
