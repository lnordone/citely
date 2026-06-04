"""Eval harness: runs metrics; supports config sweeps -> comparison tables.

Two independent slices, each backed by a fixture in ``eval/fixtures``:

* **generation** (``citation_cases.json``): runs the verifier over labeled claims and
  reports verifier agreement (vs the expected label), citation accuracy, and faithfulness.
  Needs only an LLM.
* **retrieval** (``recall_queries.json``): runs the live ``HybridRetriever`` and reports
  mean recall@k of retrieved arXiv ids against the labeled relevant ids. Needs the DB +
  embedder + reranker. (The shipped fixtures are placeholders — recall is only meaningful
  once the labeled papers are actually ingested.)

Heavy singletons (LLM, embedder, reranker, BM25 index) are built once and reused across a
sweep; only the cheap, config-dependent pieces (query constructor, retriever wiring) are
rebuilt per variant.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING, Any

from citely.config import Config
from citely.db.repository import PassageRepository
from citely.db.session import init_db
from citely.eval.metrics import citation_accuracy, faithfulness, recall_at_k
from citely.generation.verifier import ClaimVerifier
from citely.indexing.bm25_index import BM25Index
from citely.logging import get_logger
from citely.providers.factory import (
    build_embedding_provider,
    build_llm_provider,
    build_reranker,
)
from citely.query.construct import build_query_constructor
from citely.retrieval.dense import DenseRetriever
from citely.retrieval.retriever import HybridRetriever
from citely.retrieval.sparse import SparseRetriever
from citely.retrieval.types import Claim, RetrievedPassage

if TYPE_CHECKING:
    from citely.providers.base import EmbeddingProvider, LLMProvider
    from citely.retrieval.rerank import Reranker

log = get_logger(__name__)

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    with (_FIXTURES / name).open("r", encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return data


async def run_eval(cfg: Config, sweep: dict[str, list[Any]] | None = None) -> dict:
    """Run the eval suite; return a results table (optionally over a config sweep).

    ``sweep`` maps dotted config paths (e.g. ``"retrieval.rrf_k"``) to a list of values;
    the harness evaluates the cartesian product and returns one row per combination.
    """
    # Built once and shared: model loads dominate runtime and don't vary over the sweeps
    # we support (retrieval/generation params).
    llm = build_llm_provider(cfg)
    embedder = build_embedding_provider(cfg)
    reranker = build_reranker(cfg)

    factory = init_db(cfg)
    bm25_index = BM25Index()
    async with factory() as session:
        passages = await PassageRepository(session).list_all()
    bm25_index.build(passages)
    log.info("eval.setup", llm=llm.model_name, embedder=embedder.model_name, passages=len(passages))

    if not sweep:
        result = await _eval_once(cfg, llm, embedder, reranker, bm25_index, factory)
        return {"params": {}, **result}

    rows: list[dict] = []
    for overrides in _expand_sweep(sweep):
        variant = _with_overrides(cfg, overrides)
        log.info("eval.variant", **{k: str(v) for k, v in overrides.items()})
        metrics = await _eval_once(variant, llm, embedder, reranker, bm25_index, factory)
        rows.append({"params": overrides, **metrics})
    return {"sweep": rows}


async def _eval_once(
    cfg: Config,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    reranker: Reranker,
    bm25_index: BM25Index,
    factory: Any,
) -> dict:
    gen = await _eval_generation(cfg, llm)
    rec = await _eval_retrieval(cfg, llm, embedder, reranker, bm25_index, factory)
    return {**gen, **rec}


async def _eval_generation(cfg: Config, llm: LLMProvider) -> dict:
    """Verifier agreement / citation accuracy / faithfulness over labeled claims."""
    cases = _load_fixture("citation_cases.json")["cases"]
    if not cases:
        return {"verifier_agreement": 0.0, "citation_accuracy": 1.0, "faithfulness": 0.0}

    verifier = ClaimVerifier(llm, enabled=True)
    claim_dicts: list[dict] = []
    valid_ids: set[str] = set()
    agree = 0
    for case in cases:
        sources = [
            RetrievedPassage(passage_id=f"{sid}-p", paper_id=sid, text=text, score=1.0, source_key=sid)
            for sid, text in case["sources"].items()
        ]
        valid_ids.update(case["sources"].keys())
        claim = Claim(text=case["claim"], source_ids=list(case["source_ids"]))
        checked = await verifier.verify(claim, sources)
        claim_dicts.append({"source_ids": checked.source_ids, "supported": checked.supported})
        if checked.supported is bool(case["expected_supported"]) and checked.supported is not None:
            agree += 1

    return {
        "verifier_agreement": agree / len(cases),
        "citation_accuracy": citation_accuracy(claim_dicts, valid_ids),
        "faithfulness": faithfulness(claim_dicts),
    }


async def _eval_retrieval(
    cfg: Config,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    reranker: Reranker,
    bm25_index: BM25Index,
    factory: Any,
) -> dict:
    """Mean recall@final_k of the live HybridRetriever over labeled queries."""
    queries = _load_fixture("recall_queries.json")["queries"]
    k = cfg.retrieval.final_k
    if not queries:
        return {"recall_at_k": 0.0, "k": k, "n_queries": 0}

    recalls: list[float] = []
    async with factory() as session:
        retriever = HybridRetriever(
            cfg,
            build_query_constructor(llm, cfg),
            SparseRetriever(bm25_index),
            DenseRetriever(embedder, PassageRepository(session)),
            reranker,
        )
        for q in queries:
            try:
                result = await retriever.retrieve(q["query"])
            except Exception as exc:  # one bad query shouldn't sink the whole eval
                log.warning("eval.query_failed", query=q["query"], error=str(exc))
                recalls.append(0.0)
                continue
            retrieved = list(dict.fromkeys(p.paper_id for p in result.passages))
            recalls.append(recall_at_k(retrieved, q["relevant_arxiv_ids"], k))

    return {"recall_at_k": mean(recalls), "k": k, "n_queries": len(queries)}


def _expand_sweep(sweep: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Cartesian product of {path: [values]} -> list of {path: value} override dicts."""
    paths = list(sweep.keys())
    combos = itertools.product(*(sweep[p] for p in paths))
    return [dict(zip(paths, values, strict=True)) for values in combos]


def _with_overrides(cfg: Config, overrides: dict[str, Any]) -> Config:
    """Return a new Config with dotted-path values replaced (e.g. ``retrieval.rrf_k``)."""
    data = cfg.model_dump()
    for path, value in overrides.items():
        cursor = data
        *parents, leaf = path.split(".")
        for key in parents:
            cursor = cursor[key]
        cursor[leaf] = value
    return Config.model_validate(data)
