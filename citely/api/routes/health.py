"""GET /health — provider model names + DB connectivity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sqlalchemy import text

from citely.api.deps import AppState, get_db, get_state
from citely.api.schemas import HealthResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    state: AppState = Depends(get_state),
    session: AsyncSession = Depends(get_db),
) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # health must report status, never raise
        db_ok = False
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        llm_model=state.llm.model_name,
        embedding_model=state.embedder.model_name,
    )
