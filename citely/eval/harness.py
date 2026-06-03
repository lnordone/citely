"""Eval harness: runs metrics; supports config sweeps -> comparison tables.

# TODO(phase 9): load fixtures, run retrieval/generation, compute metrics, sweep configs.
"""

from __future__ import annotations

from citely.config import Config


async def run_eval(cfg: Config, sweep: dict | None = None) -> dict:
    """Run the eval suite; return a results table (optionally over a config sweep)."""
    raise NotImplementedError  # TODO(phase 9)
