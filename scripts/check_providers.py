#!/usr/bin/env python
"""Phase 1 sanity check: exercise embed + generate through the provider interfaces.

Proves the central principle — provider swap works via config alone. Run it once with
your config, then again with ``--provider``/``--embedding-provider`` overrides and watch
the same interface calls hit a different backend with no other code change.

    python scripts/check_providers.py
    python scripts/check_providers.py --provider openai --embedding-provider openai
    python scripts/check_providers.py --provider anthropic --embedding-provider local

Backend errors (no Ollama server, missing API key) are reported clearly and do not mean
the interface is wrong — the wiring is what this script verifies.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running as a plain script (python scripts/check_providers.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from citely.config import (
    EmbeddingProviderKind,
    LLMProviderKind,
    load_config,
)
from citely.logging import configure_logging, get_logger
from citely.providers.base import GenerationConfig, Message
from citely.providers.factory import (
    build_embedding_provider,
    build_llm_provider,
)

log = get_logger("check_providers")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument(
        "--provider",
        choices=[k.value for k in LLMProviderKind],
        default=None,
        help="override cfg.provider (LLM)",
    )
    p.add_argument(
        "--embedding-provider",
        choices=[k.value for k in EmbeddingProviderKind],
        default=None,
        help="override cfg.embedding_provider",
    )
    p.add_argument(
        "--prompt",
        default="In one sentence, what is retrieval-augmented generation?",
        help="prompt sent through LLMProvider.generate",
    )
    return p.parse_args(argv)


async def check_llm(provider, prompt: str) -> bool:
    print(f"\n[LLM] provider class : {type(provider).__name__}")
    print(f"[LLM] model_name     : {provider.model_name}")
    messages = [
        Message("system", "You are concise."),
        Message("user", prompt),
    ]
    try:
        text = await provider.generate(messages, GenerationConfig(max_tokens=128))
        print(f"[LLM] generate() ok  : {text.strip()[:200]!r}")
    except Exception as exc:
        print(f"[LLM] generate() FAILED ({type(exc).__name__}): {exc}")
        return False

    try:
        print("[LLM] stream()       : ", end="", flush=True)
        got = 0
        async for delta in provider.stream(messages, GenerationConfig(max_tokens=64)):
            got += len(delta)
            print(delta, end="", flush=True)
        print(f"\n[LLM] stream() ok    : {got} chars")
    except Exception as exc:
        print(f"\n[LLM] stream() FAILED ({type(exc).__name__}): {exc}")
        return False

    try:
        schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["answer"],
        }
        obj = await provider.generate_json(
            [Message("user", "Return JSON with keys 'answer' (string) and 'confidence' "
                             "(0-1) answering: what is a vector embedding?")],
            schema,
            GenerationConfig(max_tokens=256),
        )
        assert isinstance(obj, dict), "generate_json must return a dict"
        print(f"[LLM] generate_json  : {obj}")
    except Exception as exc:
        print(f"[LLM] generate_json FAILED ({type(exc).__name__}): {exc}")
        return False
    return True


async def check_embedding(provider) -> bool:
    print(f"\n[EMB] provider class : {type(provider).__name__}")
    print(f"[EMB] model_name     : {provider.model_name}")
    texts = ["hybrid retrieval combines sparse and dense signals", "the cat sat on the mat"]
    try:
        vectors = await provider.embed(texts)
    except Exception as exc:
        print(f"[EMB] embed() FAILED ({type(exc).__name__}): {exc}")
        return False

    if len(vectors) != len(texts):
        print(f"[EMB] embed() FAILED : order/count mismatch ({len(vectors)} != {len(texts)})")
        return False
    dim = len(vectors[0])
    print(f"[EMB] embed() ok     : {len(vectors)} vectors, dim={dim}")
    try:
        declared = provider.dimension
        print(f"[EMB] dimension      : {declared}")
        if declared != dim:
            print(f"[EMB] WARNING        : declared dim {declared} != embedded dim {dim}")
            return False
    except Exception as exc:
        print(f"[EMB] dimension FAILED ({type(exc).__name__}): {exc}")
        return False
    return True


async def main_async(args: argparse.Namespace) -> int:
    configure_logging()
    cfg = load_config(args.config)

    overrides: dict = {}
    if args.provider:
        overrides["provider"] = LLMProviderKind(args.provider)
    if args.embedding_provider:
        overrides["embedding_provider"] = EmbeddingProviderKind(args.embedding_provider)
    if overrides:
        cfg = cfg.model_copy(update=overrides)

    print("=" * 70)
    print(f"LLM provider       : {cfg.provider.value}")
    print(f"Embedding provider : {cfg.embedding_provider.value}")
    print("=" * 70)

    # The ONLY instantiation point — everything below is interface calls.
    llm = build_llm_provider(cfg)
    emb = build_embedding_provider(cfg)

    llm_ok = await check_llm(llm, args.prompt)
    emb_ok = await check_embedding(emb)

    print("\n" + "=" * 70)
    print(f"LLM   ({cfg.provider.value:>9}): {'PASS' if llm_ok else 'FAIL'}")
    print(f"EMBED ({cfg.embedding_provider.value:>9}): {'PASS' if emb_ok else 'FAIL'}")
    print("=" * 70)
    return 0 if (llm_ok and emb_ok) else 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
