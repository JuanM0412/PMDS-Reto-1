"""
Schemas for the chat / frontend-facing endpoints.

These match the TypeScript interfaces defined in the frontend's
ChatApiInterface.ts so both sides stay in sync.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Endpoint 3 – POST /api/chat/step (frontend triggers an agent)
# ---------------------------------------------------------------------------


class PostStepRequest(BaseModel):
    """
    Request body sent by the frontend to trigger a pipeline agent.

    Matches frontend's PostStepRequestInterface.
    """

    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, le=6, description="Pipeline step (1-6).")
    uuid: str = Field(min_length=1, max_length=128, description="Session UUID.")
    context: str = Field(default="", description="Input text or artifact to correct.")
    is_feedback: bool = Field(
        default=False,
        description="True when the user is submitting feedback on a previous result.",
    )


class PostStepResponse(BaseModel):
    """
    Response returned to the frontend after triggering an agent.

    Matches frontend's PostStepResponseInterface.
    """

    model_config = ConfigDict(extra="forbid")

    message: str


# ---------------------------------------------------------------------------
# Endpoint 2 – GET /api/chat/logs
# ---------------------------------------------------------------------------


class GetLogsResponse(BaseModel):
    """
    Response for the logs endpoint.

    Matches frontend's GetLogsResponseInterface.
    """

    model_config = ConfigDict(extra="forbid")

    logs: list[str]


# ---------------------------------------------------------------------------
# Endpoints 4 & 5 – GET /api/chat/artifacts  and  /api/chat/artifacts/download
# ---------------------------------------------------------------------------


class ArtifactItem(BaseModel):
    """A single artifact descriptor returned by the artifacts list endpoint."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Artifact type identifier (e.g. 'functional_requirements').")
    name: str = Field(description="Human-readable artifact name.")


class GetArtifactsResponse(BaseModel):
    """
    Response for the artifacts list endpoint.

    Matches frontend's GetArtifactsResponseInterface.
    """

    model_config = ConfigDict(extra="forbid")

    artifacts: list[ArtifactItem]
