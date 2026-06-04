"""CLI: python -m citely.eval [--config path] [--sweep sweep.json]

``--sweep`` points at a JSON file mapping dotted config paths to value lists, e.g.::

    {"retrieval.rrf_k": [30, 60], "retrieval.rerank_candidates": [20, 40]}

The harness evaluates the cartesian product and prints a comparison table.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from citely.config import load_config
from citely.eval.harness import run_eval
from citely.logging import configure_logging

_METRICS = ("recall_at_k", "verifier_agreement", "citation_accuracy", "faithfulness")


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _print_table(rows: list[dict[str, Any]], param_keys: list[str]) -> None:
    headers = [*param_keys, *_METRICS]
    table = []
    for row in rows:
        params = row.get("params", {})
        cells = [_fmt(params.get(k, "")) for k in param_keys]
        cells += [_fmt(row.get(m, "")) for m in _METRICS]
        table.append(cells)

    widths = [len(h) for h in headers]
    for cells in table:
        for i, cell in enumerate(cells):
            widths[i] = max(widths[i], len(cell))

    def line(cells: list[str]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    print(line(headers))
    print("  ".join("-" * w for w in widths))
    for cells in table:
        print(line(cells))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citely.eval")
    parser.add_argument("--sweep", default=None, help="path to a JSON config-sweep spec")
    parser.add_argument("--config", default=None)
    args = parser.parse_args(argv)

    configure_logging()
    cfg = load_config(args.config)

    sweep = None
    if args.sweep:
        with open(args.sweep, encoding="utf-8") as fh:
            sweep = json.load(fh)

    results = asyncio.run(run_eval(cfg, sweep))

    print("\n" + "=" * 70)
    if "sweep" in results:
        rows = results["sweep"]
        param_keys = list(rows[0]["params"].keys()) if rows else []
        _print_table(rows, param_keys)
    else:
        _print_table([results], [])
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
