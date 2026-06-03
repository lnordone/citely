# Citely

Citation-grounded literature review over arXiv. Hybrid retrieval (BM25 + dense + RRF +
cross-encoder rerank) feeds a structured-output reviewer that emits claims with inline
`[S?]` citations, optionally verified for entailment.

**Core principle:** all model access goes through `LLMProvider` / `EmbeddingProvider`.
No business-logic module imports an Ollama/OpenAI/Anthropic client directly. Swapping
providers is a one-line config change.

## Architecture

```
ingest (arXiv) -> normalize -> chunk -> store (postgres + pgvector)
                                          |
                                  embedder (EmbeddingProvider) -> vectors
                                  bm25_index (SparseIndex)      -> sparse
                                          |
query -> construct -> {sparse, dense} legs -> RRF fusion -> rerank -> final_k
                                          |
                       reviewer (LLMProvider.generate_json) -> claims -> verifier -> render
```

The **providers** package is the spine. `providers/factory.py` is the only place
provider classes are instantiated; everything else receives a provider via dependency
injection.

## Quickstart

```bash
# 1. install
make install            # pip install -e ".[dev]"

# 2. config
cp config.example.yaml config.yaml      # edit provider/models
cp .env.example .env                    # add OPENAI/ANTHROPIC keys if used

# 3. Phase 1 sanity check: providers work and are swappable via config alone
python scripts/check_providers.py
python scripts/check_providers.py --provider openai --embedding-provider openai

# 4. infra (later phases)
make up                 # postgres+pgvector (+ api), connects to host Ollama
make ingest             # fetch + chunk + store arXiv papers
make eval               # retrieval / citation metrics
make test lint fmt
```

## Configuration

All runtime decisions live in `config.yaml` (schema mirrored in `config.example.yaml`).
Nothing is hardcoded; modules read their config from the typed `Config` object loaded by
`citely.config.load_config`.

## Build status

The repository is scaffolded in phases (see the spec's build sequence). Modules for
later phases are importable stubs that raise `NotImplementedError` with a
`# TODO(phase N)` marker, so the tree is runnable/importable before logic exists.

- **Phase 1 (done):** config loader, provider ABCs, factory, Ollama/OpenAI/Anthropic +
  local embedding implementations, `scripts/check_providers.py`.
- Phases 2–10: db, ingest, indexing, retrieval, query, generation, api, eval, frontend.

## Layout

See `citely/` for the package. Throwaway per-stage sanity checks live in `scripts/`.
Deterministic unit tests (provider conformance with mocked clients, RRF math, chunker,
metrics, render) live in `tests/`.
