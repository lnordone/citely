"""Provider contracts: the load-bearing interfaces of the whole system.

Everything else depends on these ABCs; this module depends on nothing else in the
project. All model access in Citely flows through ``LLMProvider`` and
``EmbeddingProvider`` — no business-logic module may import an Ollama/OpenAI/Anthropic
client directly.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.2
    max_tokens: int = 2048
    # extend as needed; providers map these onto their own params


class StructuredOutputError(Exception):
    """Raised when ``generate_json`` cannot produce a valid dict (even after repair)."""


class LLMProvider(ABC):
    """Text generation: sync + streaming + structured.

    No provider reads global state; all config is injected at construction.
    """

    @abstractmethod
    async def generate(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> str:
        """Single-shot completion. Returns the full text."""

    @abstractmethod
    async def stream(
        self, messages: list[Message], cfg: GenerationConfig | None = None
    ) -> AsyncIterator[str]:
        """Yields text deltas as they arrive. Backs the SSE /review endpoint."""
        raise NotImplementedError  # pragma: no cover - overridden by subclasses

    @abstractmethod
    async def generate_json(
        self, messages: list[Message], schema: dict, cfg: GenerationConfig | None = None
    ) -> dict:
        """Structured output constrained to ``schema`` (a JSON schema dict).

        Implementations use native structured-output / JSON mode where available
        (Ollama ``format``, OpenAI/Anthropic tool/JSON mode); otherwise prompt + parse
        + repair. MUST return a parsed dict or raise ``StructuredOutputError``.
        """

    @property
    @abstractmethod
    def model_name(self) -> str: ...


class EmbeddingProvider(ABC):
    """Turn text into vectors for dense retrieval.

    ``embed`` is used for both passage indexing and query embedding (same method, same
    model) so the two spaces match. Asymmetric models (e5 query/passage prefixes) must
    encode that *inside* the implementation, never at call sites.
    """

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed. Output order matches input order. Batches internally."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension (e.g. 768 for bge-base). Asserted against the pgvector
        column width at startup — a mismatch is a hard error."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Shared structured-output helpers, used by providers without strict JSON modes.
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    """Remove surrounding ```json ... ``` fences if present."""
    return _FENCE_RE.sub("", text.strip()).strip()


def extract_json_object(text: str) -> str:
    """Best-effort: return the substring spanning the first balanced top-level object."""
    cleaned = strip_code_fences(text)
    start = cleaned.find("{")
    if start == -1:
        return cleaned
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : i + 1]
    return cleaned[start:]


def try_parse_json(text: str) -> dict | None:
    """Attempt to parse ``text`` (with fence-stripping / extraction) into a dict."""
    for candidate in (text, strip_code_fences(text), extract_json_object(text)):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
