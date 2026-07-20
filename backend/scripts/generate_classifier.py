#!/usr/bin/env python3
"""Deprecated, non-mutating classifier-generator command.

The application does not generate or train a local CNN. It performs inference
with a pre-trained SigLIP 2 or CLIP vision-language model configured in
``app/model.py``. This command is retained only to redirect old instructions.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

PRIMARY_PRESETS = (
    "siglip2-base (default)",
    "siglip2-so400m-256",
    "siglip2-so400m-384",
    "siglip2-so400m-512",
    "siglip2-large-512",
    "siglip2-giant-384",
    "clip-base",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deprecated informational command; no model is generated or trained."
    )
    parser.add_argument(
        "--show-presets",
        action="store_true",
        help="list the primary EWASTE_MODEL presets",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print("DEPRECATED: no classifier artifact was generated or modified.")
    print("Active implementation: backend/app/model.py")
    print("Start the API from the repository root: ./run_backend.sh")
    print("Default API URL: http://127.0.0.1:8000")
    print("The selected Hugging Face model downloads on first use unless already cached.")
    if args.show_presets:
        print("Primary EWASTE_MODEL presets:")
        for preset in PRIMARY_PRESETS:
            print(f"  - {preset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
