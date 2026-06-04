"""GET /models — list installed Ollama models for a frontend model picker."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from citely.api.deps import AppState, get_state
from citely.api.schemas import ModelsResponse
from citely.config import LLMProviderKind
from citely.logging import get_logger

router = APIRouter()
log = get_logger(__name__)


@router.get("/models", response_model=ModelsResponse)
async def models(state: AppState = Depends(get_state)) -> ModelsResponse:
    cfg = state.cfg
    if cfg.provider is not LLMProviderKind.ollama:
        # Model listing is only meaningful for the local Ollama server.
        return ModelsResponse(
            provider=cfg.provider.value,
            default=state.llm.model_name,
            installed=[],
            error="model listing is only supported for the ollama provider",
        )

    installed: list[str] = []
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{cfg.providers.ollama_host}/api/tags")
            resp.raise_for_status()
            installed = [m["name"] for m in resp.json().get("models", [])]
    except Exception as exc:  # surface, don't crash — the picker degrades gracefully
        error = str(exc)
        log.warning("models.list_failed", error=error)

    return ModelsResponse(
        provider=cfg.provider.value,
        default=state.llm.model_name,
        installed=installed,
        error=error,
    )
