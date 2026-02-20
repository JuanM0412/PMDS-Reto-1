"""
Schemas for the N8N callback endpoint.

When an n8n agent finishes processing it sends a POST request to this
backend with the artifact it produced plus metadata about what changed.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChangesMade(BaseModel):
    """Tracks what the agent modified compared to the previous artifact version."""

    model_config = ConfigDict(extra="allow")

    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)


class N8NCallbackRequest(BaseModel):
    """
    Payload sent by n8n to POST /api/n8n/callback when it finishes a step.

    N8N sends: uuid, artifact_type, content.
    step is optional — if omitted it will be derived from artifact_type.
    """

    model_config = ConfigDict(extra="ignore")

    uuid: str = Field(min_length=1, max_length=128)
    artifact_type: str = Field(description="The artifact type key produced by the agent (e.g. 'requirements').")
    content: Any = Field(default=None, description="The artifact content produced by the agent.")
    step: int | None = Field(default=None, ge=1, le=6, description="Pipeline step (1-6). Derived from artifact_type if omitted.")
    changes_made: ChangesMade = Field(default_factory=ChangesMade)
    justification: str = Field(default="")
    context: str = Field(default="", description="Original input/context that was sent to the agent.")


class N8NCallbackResponse(BaseModel):
    """Response returned to n8n after successfully recording the result."""

    model_config = ConfigDict(extra="forbid")

    message: str
    log_id: int
