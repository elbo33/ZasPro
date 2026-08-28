"""The internal FastAPI app (SPEC §16).

Read-mostly. The dashboard calls this; it never touches Postgres directly. The
API does not own or migrate the schema — Alembic does (SPEC §16).

    uv run uvicorn zaspro.api.app:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zaspro.api.deps import get_db  # re-exported for convenience

__all__ = ["create_app", "app", "get_db"]


def create_app() -> FastAPI:
    app = FastAPI(title="ZasPro internal API", version="m3")

    # the Next.js dev server runs on another port
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from zaspro.api.routers import curriculum, knowledge, review, sources

    app.include_router(review.router)
    app.include_router(knowledge.router)
    app.include_router(curriculum.router)
    app.include_router(sources.router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
