#!/usr/bin/env python3
"""Deterministic smoke checks for the three-stage classifier pipeline.

This is not an accuracy evaluation: synthetic patterns are not a labeled image
corpus. By default the command checks only deterministic image-quality gates and
does not load or download a vision model. Use ``--model`` for inference smoke
checks and ``--network`` for optional, TLS-verified public-image diagnostics.

Run from ``backend/``:
    python3 scripts/test_classifier.py
    python3 scripts/test_classifier.py --model
    python3 scripts/test_classifier.py --model --network
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

NETWORK_IMAGES = (
    (
        "computer_mouse",
        "https://commons.wikimedia.org/wiki/Special:FilePath/3-Tasten-Maus_Microsoft.jpg",
    ),
    (
        "banana_control",
        "https://commons.wikimedia.org/wiki/Special:FilePath/Banana-Single.jpg",
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        action="store_true",
        help="load the configured model and run inference smoke checks",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="download fixed public diagnostics with normal TLS verification (implies --model)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="set HF_HUB_OFFLINE=1 before model loading; cached weights are required",
    )
    parser.add_argument("--seed", type=int, default=42, help="synthetic-image RNG seed")
    parser.add_argument("--timeout", type=float, default=30.0, help="network timeout in seconds")
    return parser


def make_image(
    rng: np.random.Generator,
    width: int,
    height: int,
    color: tuple[int, int, int] = (128, 128, 128),
    noise: int = 0,
) -> Image.Image:
    image = Image.new("RGB", (width, height), color)
    if noise:
        array = np.asarray(image, dtype=np.int16)
        jitter = rng.integers(-noise, noise + 1, array.shape, dtype=np.int16)
        image = Image.fromarray(np.clip(array + jitter, 0, 255).astype(np.uint8))
    return image


def make_textured_pattern(rng: np.random.Generator, width: int = 400, height: int = 300) -> Image.Image:
    x, y = np.meshgrid(np.arange(width), np.arange(height))
    red = np.clip(128 + 100 * np.sin(x / 23.0), 0, 255)
    green = np.clip(120 + 95 * np.cos(y / 19.0), 0, 255)
    blue = np.clip(110 + 90 * np.sin((x + y) / 17.0), 0, 255)
    array = np.stack((red, green, blue), axis=-1).astype(np.int16)
    jitter = rng.integers(-15, 16, array.shape, dtype=np.int16)
    return Image.fromarray(np.clip(array + jitter, 0, 255).astype(np.uint8))


def run_quality_checks(rng: np.random.Generator) -> bool:
    from app.model import assess_image_quality

    checks = (
        ("too_small", make_image(rng, 80, 80), "image_too_small"),
        ("too_dark", make_image(rng, 400, 300, (5, 5, 5)), "image_too_dark"),
        ("too_blurry", make_image(rng, 400, 300), "image_too_blurry"),
        ("low_contrast", make_image(rng, 400, 300, (127, 127, 127), noise=2), "image_low_contrast"),
    )
    passed = 0
    for name, image, expected in checks:
        result = assess_image_quality(image)
        ok = result == {"ok": False, "reason": expected}
        passed += int(ok)
        print(f"quality/{name}: {'PASS' if ok else 'FAIL'} -> {result}")
    print(f"Quality-gate checks: {passed}/{len(checks)} passed")
    return passed == len(checks)


def run_model_smoke(rng: np.random.Generator) -> bool:
    from app.model import classifier

    images = (
        ("textured_pattern", make_textured_pattern(rng)),
        ("noisy_green_control", make_image(rng, 400, 300, (34, 139, 34), noise=40)),
    )
    ok = True
    for name, image in images:
        entity, confidence, model_used = classifier.predict(image, return_confidence=True)
        valid = isinstance(entity, str) and isinstance(confidence, (int, float)) and isinstance(model_used, str)
        valid = valid and model_used != "error"
        ok = ok and valid
        print(
            f"model/{name}: {'PASS' if valid else 'FAIL'} -> "
            f"entity={entity!r}, confidence={confidence}, model_used={model_used!r}"
        )
    print("Model checks confirm execution only; they do not measure classifier accuracy.")
    return ok


def download_image(url: str, timeout: float) -> Image.Image:
    import requests

    response = requests.get(
        url,
        headers={"User-Agent": "ewaste-classifier-smoke/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def run_network_diagnostics(timeout: float) -> bool:
    from app.model import classifier

    ok = True
    for label, url in NETWORK_IMAGES:
        try:
            image = download_image(url, timeout)
            entity, confidence, model_used = classifier.predict(image, return_confidence=True)
            valid = model_used != "error"
            ok = ok and valid
            print(
                f"network/{label}: {'PASS' if valid else 'FAIL'} -> "
                f"entity={entity!r}, confidence={confidence}, model_used={model_used!r}"
            )
        except Exception as exc:
            ok = False
            print(f"network/{label}: FAIL -> {type(exc).__name__}: {exc}", file=sys.stderr)
    print("Network diagnostics are unscored examples, not an evaluation dataset.")
    return ok


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"

    rng = np.random.default_rng(args.seed)
    success = run_quality_checks(rng)
    if args.model or args.network:
        success = run_model_smoke(rng) and success
    if args.network:
        success = run_network_diagnostics(args.timeout) and success
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
