from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base



class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    n8n_webhook_url: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 6

    runs: Mapped[list["Run"]] = relationship(back_populates="current_agent")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED")

    # Orchestration fields
    current_agent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agents.id"), nullable=True)
    is_waiting_for_user: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    current_agent: Mapped["Agent"] = relationship(back_populates="runs")
    step_executions: Mapped[list["StepExecution"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False)

    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "requirements"
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Guardamos JSON como texto (válido para SQLite). En Postgres sería JSONB.
    content_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    run: Mapped["Run"] = relationship(back_populates="artifacts")


Index("ix_artifacts_run_type_created", Artifact.run_id, Artifact.artifact_type, Artifact.created_at)


class StepExecution(Base):
    __tablename__ = "step_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..6
    agent_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_feedback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="STARTED")
    request_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="step_executions")
    logs: Mapped[list["StepLog"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
    )


class StepLog(Base):
    __tablename__ = "step_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(Integer, ForeignKey("step_executions.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    execution: Mapped["StepExecution"] = relationship(back_populates="logs")


Index("ix_step_executions_run_step_attempt", StepExecution.run_id, StepExecution.step, StepExecution.attempt)
Index("ix_step_logs_execution_created", StepLog.execution_id, StepLog.created_at)
