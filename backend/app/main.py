"""
FastAPI application entry point.

Wires together configuration, middleware, database initialisation and routers.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from .config import settings
from .database import Base, engine
from .routers.chat_router import router as chat_router
from .routers.n8n_router import router as n8n_router
from .utils.logging import setup_logging

# Configure structured logging as the very first action
setup_logging(level="DEBUG" if settings.debug else "INFO")


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Ensure the `agents` PostgreSQL schema exists, then create tables.

    In production use Alembic migrations; this is fine for local dev.
    """
    # Import models so SQLAlchemy registers them with the metadata
    from .models import agent_log  # noqa: F401

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS agents"))

    Base.metadata.create_all(bind=engine)
    yield


# ---------------------------------------------------------------------------
# FastAPI instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend for the multi-agent pipeline. "
        "Bridges the Vue frontend with n8n-powered AI agents."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(chat_router)
app.include_router(n8n_router)


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"], summary="Health check")
def health() -> dict[str, str]:
    """Returns 200 OK when the service is up."""
    return {"status": "ok", "environment": settings.environment}
