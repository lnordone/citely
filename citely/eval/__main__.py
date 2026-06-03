"""CLI: python -m citely.eval [--sweep ...]

# TODO(phase 9): parse args, run harness, print comparison tables.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citely.eval")
    parser.add_argument("--sweep", default=None, help="path/spec for a config sweep")
    parser.add_argument("--config", default=None)
    parser.parse_args(argv)
    raise NotImplementedError  # TODO(phase 9)


if __name__ == "__main__":
    raise SystemExit(main())
