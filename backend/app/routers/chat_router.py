"""
Chat router — Endpoints 2, 3, 4, 5.

All routes are under /api/chat to match the frontend's CHAT_ROUTES constant.

Endpoint 3  POST /api/chat/step        Trigger a pipeline agent (from frontend).
Endpoint 2  GET  /api/chat/logs        Return execution logs for a step + uuid.
Endpoint 4  GET  /api/chat/artifacts   List artifacts available for a step + uuid.
Endpoint 5  GET  /api/chat/artifacts/download  Download a specific artifact.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import settings
from ..constants.agents import AGENTS_BY_STEP
from ..database import get_db
from ..schemas.chat import (
    ArtifactItem,
    GetArtifactsResponse,
    GetLogsResponse,
    PostStepRequest,
    PostStepResponse,
)
from ..services.agent_log_service import AgentLogService
from ..services.n8n_service import N8NService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def get_agent_log_service(db: Session = Depends(get_db)) -> AgentLogService:
    return AgentLogService(db)


def get_n8n_service() -> N8NService:
    return N8NService()


# ---------------------------------------------------------------------------
# Endpoint 3 — POST /api/chat/step
# ---------------------------------------------------------------------------


@router.post(
    "/step",
    response_model=PostStepResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a pipeline agent",
    description=(
        "Received from the frontend. Triggers the n8n agent corresponding to "
        "the requested step and returns immediately. n8n will call back to "
        "POST /api/n8n/callback when it finishes."
    ),
)
async def post_step(
    body: PostStepRequest,
    n8n: N8NService = Depends(get_n8n_service),
) -> PostStepResponse:
    """
    Endpoint 3 — Receive a step trigger from the frontend and forward to n8n.

    The call to n8n is fire-and-forget (async, no waiting for the result).
    N8N will POST the result back to /api/n8n/callback asynchronously.
    """
    agent = AGENTS_BY_STEP.get(body.step)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown pipeline step: {body.step}",
        )

    callback_url = f"{settings.public_base_url}/api/n8n/callback"

    # When is_feedback is True the context field carries the feedback text.
    feedback_text: str | None = body.context if body.is_feedback else None

    try:
        await n8n.trigger_agent(
            webhook_path=agent.webhook_path,
            context=body.context,
            is_feedback=body.is_feedback,
            feedback=feedback_text,
            uuid=body.uuid,
            step=body.step,
            callback_url=callback_url,
        )
    except httpx.ConnectError as exc:
        url = f"{settings.n8n_base_url}{agent.webhook_path}"
        log.error("Connection refused to n8n step=%d url=%s", body.step, url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot connect to n8n at {url}. Is n8n running?",
        ) from exc
    except httpx.TimeoutException as exc:
        log.error("Timeout calling n8n step=%d uuid=%s", body.step, body.uuid)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Agent {body.step} timed out after {settings.n8n_request_timeout}s.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        log.error(
            "N8N returned HTTP %d for step=%d body=%s",
            exc.response.status_code,
            body.step,
            exc.response.text[:300],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"N8N webhook returned {exc.response.status_code} for step {body.step}. "
                f"Response: {exc.response.text[:300]}"
            ),
        ) from exc
    except Exception as exc:
        log.exception("Unexpected error triggering n8n step=%d uuid=%s", body.step, body.uuid)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected error calling agent {body.step}: {exc}",
        ) from exc

    return PostStepResponse(
        message=f"Agent {body.step} ({agent.name}) triggered successfully. Waiting for result."
    )


# ---------------------------------------------------------------------------
# Endpoint 2 — GET /api/chat/logs
# ---------------------------------------------------------------------------


@router.get(
    "/logs",
    response_model=GetLogsResponse,
    summary="Get execution logs for a step",
    description="Returns a list of human-readable log lines for the given uuid and step.",
)
def get_logs(
    uuid: str = Query(..., min_length=1, description="Session UUID."),
    step: int = Query(..., ge=1, le=6, description="Pipeline step (1-6)."),
    service: AgentLogService = Depends(get_agent_log_service),
) -> GetLogsResponse:
    """Endpoint 2 — Return logs for a specific uuid + step."""
    logs = service.get_logs(uuid=uuid, step=step)
    print(logs)
    return GetLogsResponse(logs=logs)


# ---------------------------------------------------------------------------
# Endpoint 4 — GET /api/chat/artifacts
# ---------------------------------------------------------------------------


@router.get(
    "/artifacts",
    response_model=GetArtifactsResponse,
    summary="List artifacts for a step",
    description=(
        "Returns the list of artifact type keys available in the latest "
        "agent result for the given uuid and step."
    ),
)
def get_artifacts(
    uuid: str = Query(..., min_length=1, description="Session UUID."),
    step: int = Query(..., ge=1, le=6, description="Pipeline step (1-6)."),
    service: AgentLogService = Depends(get_agent_log_service),
) -> GetArtifactsResponse:
    """Endpoint 4 — List artifact descriptors for a specific uuid + step."""
    items = service.get_artifacts(uuid=uuid, step=step)
    artifacts = [ArtifactItem(id=item["id"], name=item["name"]) for item in items]
    return GetArtifactsResponse(artifacts=artifacts)


# ---------------------------------------------------------------------------
# Endpoint 5 — GET /api/chat/artifacts/download
# ---------------------------------------------------------------------------


@router.get(
    "/artifacts/download",
    summary="Download a specific artifact",
    description=(
        "Returns the full JSON content of a specific artifact identified by "
        "its type key (id), for the given uuid and step."
    ),
)
def get_artifact_download(
    uuid: str = Query(..., min_length=1, description="Session UUID."),
    step: int = Query(..., ge=1, le=6, description="Pipeline step (1-6)."),
    id: str = Query(..., min_length=1, description="Artifact type key (e.g. 'functional_requirements')."),
    service: AgentLogService = Depends(get_agent_log_service),
) -> Any:
    """Endpoint 5 — Return the content of a specific artifact."""
    content = service.get_artifact_content(uuid=uuid, step=step, artifact_id=id)

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{id}' not found for uuid={uuid} step={step}.",
        )

    return content
