"""
Repository for AgentLog persistence.

Centralises all database access for the agent_logs table so that routers and
services remain free of raw SQLAlchemy queries (Single Responsibility Principle).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.agent_log import AgentLog


class AgentLogRepository:
    """Data-access layer for the agent_logs table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create(
        self,
        input: str,
        uuid: str,
        agent: int | None,
        artefact: dict[str, Any],
        justification: str | None,
        added: list[str] | None,
        modified: list[str] | None,
        deleted: list[str] | None,
    ) -> AgentLog:
        """Insert a new agent log record and flush to obtain its id."""
        log = AgentLog(
            input=input,
            uuid=uuid,
            agent=agent,
            artefact=artefact,
            justification=justification,
            added=json.dumps(added, ensure_ascii=False) if added is not None else None,
            modified=json.dumps(modified, ensure_ascii=False) if modified is not None else None,
            deleted=json.dumps(deleted, ensure_ascii=False) if deleted is not None else None,
            timestamp=datetime.utcnow(),
        )
        self._db.add(log)
        self._db.flush()  # populate id without committing so the caller controls the transaction
        return log

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_uuid_and_step(self, uuid: str, step: int) -> list[AgentLog]:
        """Return all log records for a given session uuid and pipeline step, ordered by timestamp asc."""
        stmt = (
            select(AgentLog)
            .where(AgentLog.uuid == uuid, AgentLog.agent == step)
            .order_by(AgentLog.timestamp.asc())
        )
        print(f"Executing query for uuid={uuid}, step={step}")
        result = list(self._db.scalars(stmt).all())
        print(f"Found {len(result)} records")
        return result

    def get_latest_by_uuid_and_step(self, uuid: str, step: int) -> AgentLog | None:
        """Return the most recent log record for a given session uuid and pipeline step."""
        stmt = (
            select(AgentLog)
            .where(AgentLog.uuid == uuid, AgentLog.agent == step)
            .order_by(AgentLog.timestamp.desc())
            .limit(1)
        )
        return self._db.scalars(stmt).first()

    def get_by_id(self, log_id: int) -> AgentLog | None:
        """Return a single log record by primary key."""
        return self._db.get(AgentLog, log_id)
