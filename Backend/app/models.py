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
