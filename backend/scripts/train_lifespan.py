#!/usr/bin/env python3
"""Deprecated, non-mutating entry point for the legacy lifespan trainer.

This file intentionally contains no training or artifact-writing code. The old
trainer used a stale schema and wrote filenames also used by the v2 pipelines.
Use ``scripts/train_lifespan_v2.py`` instead.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Deprecated legacy trainer (disabled). Use "
            "python3 scripts/train_lifespan_v2.py --help instead."
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(
        "ERROR: scripts/train_lifespan.py is disabled and did not modify any files.\n"
        "Use: python3 scripts/train_lifespan_v2.py --help",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
