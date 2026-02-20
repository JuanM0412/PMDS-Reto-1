from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AgentLog(Base):
    """
    Stores the result of each agent execution.

    One row is created every time n8n completes a pipeline step
    (including re-runs triggered by user feedback).
    Mapped to the `agents.agent_logs` table in PostgreSQL.
    """

    __tablename__ = "agent_logs"
    __table_args__ = {"schema": "agents"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    input: Mapped[str] = mapped_column(Text, nullable=False)                # original context / input sent to the agent
    uuid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent: Mapped[int | None] = mapped_column(Integer, nullable=True)       # pipeline step 1-6, null if unknown
    artefact: Mapped[dict] = mapped_column(JSONB, nullable=False)           # artifact JSON returned by n8n
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)  # justification text from n8n
    added: Mapped[str | None] = mapped_column(Text, nullable=True)          # changes_made.added (JSON text)
    modified: Mapped[str | None] = mapped_column(Text, nullable=True)       # changes_made.modified (JSON text)
    deleted: Mapped[str | None] = mapped_column(Text, nullable=True)        # changes_made.removed (JSON text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
