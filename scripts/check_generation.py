#!/usr/bin/env python
"""Sanity check for generation: citation IDs exist, verifier both directions.

Verifies, against synthetic labeled sources (no DB needed, deterministic content):
  * the reviewer produces grounded claims and every [S?] marker in the rendered review
    maps to a real source,
  * the verifier marks a clearly-entailed claim supported, and a clearly-false claim
    unsupported.

Requires a running LLM provider (default: Ollama).

    python scripts/check_generation.py
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from citely.config import load_config
from citely.generation.render import render_markdown
from citely.generation.reviewer import ReviewGenerator
from citely.generation.verifier import ClaimVerifier
from citely.logging import configure_logging
from citely.providers.factory import build_llm_provider
from citely.retrieval.types import Claim, PaperRef, RetrievedPassage

_MARKER_RE = re.compile(r"\[(S\d+)\]")


def _source(key: str, text: str, title: str) -> RetrievedPassage:
    return RetrievedPassage(
        passage_id=f"{key}-p",
        paper_id=f"{key}-paper",
        text=text,
        score=1.0,
        source_key=key,
        paper=PaperRef(f"{key}-paper", title, ["A. Researcher"], 2024, "http://example.com/x"),
    )


def _sources() -> list[RetrievedPassage]:
    return [
        _source(
            "S1",
            "The Transformer architecture relies entirely on self-attention mechanisms "
            "to model long-range dependencies, dispensing with recurrence and convolutions.",
            "Attention Is All You Need",
        ),
        _source(
            "S2",
            "BM25 is a sparse lexical ranking function that scores documents using term "
            "frequency and inverse document frequency, without any learned embeddings.",
            "Probabilistic Relevance: BM25",
        ),
    ]


async def main_async(args: argparse.Namespace) -> int:
    configure_logging()
    cfg = load_config(args.config)
    llm = build_llm_provider(cfg)
    sources = _sources()

    print("=" * 70)
    print(f"llm: {llm.model_name}")
    print("=" * 70)

    ok = True

    # --- reviewer + render: markers map to real sources ---
    reviewer = ReviewGenerator(llm, cfg)
    claims = [c async for c in reviewer.generate("How do transformers and BM25 work?", sources)]
    md = render_markdown(claims, sources)
    print(f"\n[review] {len(claims)} grounded claims\n")
    print(md)

    valid_keys = {s.source_key for s in sources}
    markers = set(_MARKER_RE.findall(md))
    dangling = markers - valid_keys
    print(f"\n[review] markers={sorted(markers)} dangling={sorted(dangling)}")
    if not claims:
        ok = False
        print("FAIL: reviewer produced no grounded claims")
    if dangling:
        ok = False
        print("FAIL: review contains citation markers with no matching source")

    # --- verifier: true vs false claim ---
    verifier = ClaimVerifier(llm, enabled=True)
    true_claim = Claim(text="Transformers use self-attention.", source_ids=["S1"])
    false_claim = Claim(
        text="Transformers are based on convolutional neural networks.", source_ids=["S1"]
    )
    true_checked = await verifier.verify(true_claim, sources)
    false_checked = await verifier.verify(false_claim, sources)
    print(f"\n[verify] true-claim supported={true_checked.supported} "
          f"(expect True)")
    print(f"[verify] false-claim supported={false_checked.supported} (expect False)")
    if true_checked.supported is not True:
        ok = False
        print("FAIL: a clearly-entailed claim was not marked supported")
    if false_checked.supported is not False:
        ok = False
        print("FAIL: a clearly-false claim was not marked unsupported")

    print("\n" + "=" * 70)
    print(f"GENERATION: {'PASS' if ok else 'FAIL'}")
    print("=" * 70)
    return 0 if ok else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
