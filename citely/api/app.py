"""FastAPI app factory + lifespan (db + providers) + DI wiring.

# TODO(phase 8): build providers via the factory in the lifespan, assert embedding
# dimension against the DB schema, mount routers, store handles on app.state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_app() -> FastAPI:
    """Application factory (referenced by `uvicorn ... --factory`)."""
    raise NotImplementedError  # TODO(phase 8)
