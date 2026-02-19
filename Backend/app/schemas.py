from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


Priority = Literal["MUST", "SHOULD", "COULD", "WONT"]


class AgentMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    model: str | None = None
    temperature: float | None = None


class ArtifactMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["requirements"]
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    run_id: str
    generated_at: datetime
    agent: AgentMeta


class Context(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: Literal["super-app"]
    brief_summary: str
    actors: list[str] = Field(default_factory=list)
    modules_in_scope: list[str] = Field(default_factory=list)


class Trace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["brief"]
    notes: str | None = None


class FunctionalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^REQ-F-\d{3}$")
    title: str
    description: str
    priority: Priority
    acceptance_criteria: list[str] = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    trace: Trace


class NonFunctionalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^REQ-NF-\d{3}$")
    quality_attribute: Literal["Security", "Performance", "Reliability", "Usability", "Maintainability", "Observability", "Privacy", "Compliance"]
    description: str
    metric_or_constraint: str | None = None


class Traceability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_artifact: Literal["brief"]
    links: list[str] = Field(default_factory=list)


class RequirementsArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact: ArtifactMeta
    context: Context
    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    traceability: Traceability

    @field_validator("functional_requirements")
    @classmethod
    def ensure_has_some(cls, v):
        # Puedes quitar esto si quieres permitir 0
        if len(v) == 0:
            raise ValueError("functional_requirements must contain at least 1 item")
        return v


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: Literal["super-app"] = "super-app"
    brief: str = Field(min_length=30, max_length=20_000)


class AgentBase(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    name: str
    slug: str
    n8n_webhook_url: str
    order: int


class AgentResponse(AgentBase):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: int


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    domain: str
    status: str
    current_agent: AgentResponse | None = None
    is_waiting_for_user: bool
    created_at: datetime
    updated_at: datetime


class ArtifactCreateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    artifact_type: str | None = None
    content: dict[str, Any] | None = None


class RejectRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feedback: str = Field(min_length=3, max_length=10_000)


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    run_id: str
    artifact_type: str
    version: int
    created_at: datetime
    content: dict[str, Any]


class ArtifactExportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_type: str
    version: int
    created_at: datetime
    artifact: Any


class RunArtifactsExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    exported_at: datetime
    artifacts: list[ArtifactExportItem]
