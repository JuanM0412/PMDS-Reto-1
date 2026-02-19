from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, engine
from .models import Agent
from .orchestration import PIPELINE_STEPS
from .routers.artifacts import router as artifacts_router
from .routers.orchestrator import router as orchestrator_router
from .routers.runs import router as runs_router
from .settings import settings
from .utils.logging import setup_logging

setup_logging()

# Create tables (for this challenge; migrate to Alembic later)
Base.metadata.create_all(bind=engine)


def apply_sqlite_compat_migrations() -> None:
    """
    Minimal compatibility migration for local SQLite.
    Keeps old app.db files working after model changes.
    """
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as conn:
        runs_cols = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info('runs')").fetchall()
        }

        if "current_agent_id" not in runs_cols:
            conn.exec_driver_sql("ALTER TABLE runs ADD COLUMN current_agent_id INTEGER")

        if "is_waiting_for_user" not in runs_cols:
            conn.exec_driver_sql(
                "ALTER TABLE runs ADD COLUMN is_waiting_for_user BOOLEAN NOT NULL DEFAULT 0"
            )


apply_sqlite_compat_migrations()


def seed_agents() -> None:
    """
    Seed and sync the pipeline agents.
    """
    with Session(engine) as db:
        existing = {agent.slug: agent for agent in db.scalars(select(Agent)).all()}
        changed = False

        for step in PIPELINE_STEPS:
            agent = existing.get(step.slug)
            if agent is None:
                db.add(
                    Agent(
                        name=step.name,
                        slug=step.slug,
                        order=step.order,
                        n8n_webhook_url=step.webhook_url,
                    )
                )
                changed = True
                continue

            if (
                agent.name != step.name
                or agent.order != step.order
                or agent.n8n_webhook_url != step.webhook_url
            ):
                agent.name = step.name
                agent.order = step.order
                agent.n8n_webhook_url = step.webhook_url
                changed = True

        if changed:
            db.commit()
            print("Pipeline agents synced.")


seed_agents()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router)
app.include_router(artifacts_router)
app.include_router(orchestrator_router)


@app.get("/health")
def health():
    return {"status": "ok"}
