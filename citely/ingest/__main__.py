"""CLI: python -m citely.ingest --categories cs.AI cs.LG --max 50000

# TODO(phase 3): parse args, load config, run the pipeline, print IngestStats.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citely.ingest")
    parser.add_argument("--categories", nargs="+", default=None)
    parser.add_argument("--max", type=int, default=None, dest="max_papers")
    parser.add_argument("--config", default=None)
    parser.parse_args(argv)
    raise NotImplementedError  # TODO(phase 3)


if __name__ == "__main__":
    raise SystemExit(main())
