"""
N8N callback router — Endpoint 1.

POST /api/n8n/callback
    Called by n8n when it finishes processing a pipeline step.
    Persists the artifact, justification and change-set to the database.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.n8n import N8NCallbackRequest, N8NCallbackResponse
from ..services.agent_log_service import AgentLogService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/n8n", tags=["n8n"])


@router.post(
    "/callback",
    response_model=N8NCallbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive agent result from n8n",
    description=(
        "Called by n8n when it finishes a pipeline step. "
        "Creates a new record in agent_logs with the artifact and change metadata."
    ),
)
def n8n_callback(
    payload: N8NCallbackRequest,
    db: Session = Depends(get_db),
) -> N8NCallbackResponse:
    """
    Endpoint 1 — Receive and persist the result sent by n8n.

    n8n must include the original `uuid` and `step` (forwarded from the
    trigger request) so the backend can correlate the record with the
    correct user session and pipeline position.
    """
    service = AgentLogService(db)

    try:
        agent_log = service.record_n8n_result(payload)
    except Exception as exc:
        log.exception("Failed to record n8n result uuid=%s", payload.uuid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist agent result.",
        ) from exc

    return N8NCallbackResponse(
        message=f"Agent result for step {payload.step} recorded successfully.",
        log_id=agent_log.id,
    )
