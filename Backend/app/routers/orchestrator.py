from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Agent, Artifact, Run, StepExecution, StepLog
from ..orchestration import (
    build_context_for_agent,
    get_expected_artifact_type,
    get_latest_artifact_for_type,
    get_latest_artifacts_by_type,
    get_next_pipeline_agent,
    get_pipeline_agents,
    get_pipeline_step,
)
from ..schemas import AgentResponse, RejectRunRequest, RunResponse
from ..services import trigger_agent
from ..utils.mermaid import normalize_mermaid_artifact

router = APIRouter(tags=["orchestrator"])


def _add_execution_log(db: Session, execution_id: int, message: str) -> None:
    db.add(
        StepLog(
            execution_id=execution_id,
            message=message,
            created_at=datetime.utcnow(),
        )
    )


def _to_agent_response(agent: Agent | None) -> AgentResponse | None:
    if not agent:
        return None
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        slug=agent.slug,
        n8n_webhook_url=agent.n8n_webhook_url,
        order=agent.order,
    )


def _to_run_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        domain=run.domain,
        status=run.status,
        current_agent=_to_agent_response(run.current_agent),
        is_waiting_for_user=run.is_waiting_for_user,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _save_artifact(
    db: Session,
    run_id: str,
    artifact_type: str,
    content: dict[str, Any],
) -> Artifact:
    normalized_content = normalize_mermaid_artifact(content)
    stmt = (
        select(Artifact)
        .where(Artifact.run_id == run_id, Artifact.artifact_type == artifact_type)
        .order_by(Artifact.version.desc())
        .limit(1)
    )
    last = db.execute(stmt).scalars().first()
    next_version = (last.version + 1) if last else 1

    artifact = Artifact(
        run_id=run_id,
        artifact_type=artifact_type,
        version=next_version,
        content_json=json.dumps(normalized_content, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    db.add(artifact)
    return artifact


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return [_to_agent_response(agent) for agent in get_pipeline_agents(db)]


@router.post("/callbacks/agent/{agent_slug}")
async def agent_callback(
    agent_slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.json()
    incoming = body.get("body") if isinstance(body.get("body"), dict) else body

    run_id = incoming.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="Missing run_id")

    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    agent = db.execute(select(Agent).where(Agent.slug == agent_slug)).scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    artifact_type = get_expected_artifact_type(agent_slug) or incoming.get("artifact_type") or "unknown"
    content = incoming.get("content")
    if content is None:
        content = {
            k: v
            for k, v in incoming.items()
            if k not in {"run_id", "artifact_type"}
        }
    if not isinstance(content, dict):
        content = {"value": content}

    artifact = _save_artifact(db, run_id=run_id, artifact_type=artifact_type, content=content)

    callback_step = get_pipeline_step(agent_slug)
    if callback_step:
        stmt_exec = (
            select(StepExecution)
            .where(
                StepExecution.run_id == run_id,
                StepExecution.step == callback_step.order,
                StepExecution.agent_slug == agent_slug,
            )
            .order_by(StepExecution.attempt.desc(), StepExecution.started_at.desc())
            .limit(1)
        )
        execution = db.execute(stmt_exec).scalars().first()
        if execution:
            if execution.status != "COMPLETED":
                execution.status = "ARTIFACT_RECEIVED"
            _add_execution_log(
                db,
                execution.id,
                f"Callback recibido para {agent_slug}; artefacto {artifact_type} v{artifact.version} almacenado.",
            )

    run.current_agent_id = agent.id
    run.status = f"WAITING_APPROVAL_{agent.slug.upper()}"
    run.is_waiting_for_user = True
    run.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "ok", "message": "Artifact received, waiting for user approval"}


@router.post("/runs/{run_id}/approve", response_model=RunResponse)
def approve_run(run_id: str, bg: BackgroundTasks, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if not run.is_waiting_for_user:
        raise HTTPException(status_code=400, detail="Run is not waiting for approval")

    current_agent = run.current_agent
    if not current_agent:
        raise HTTPException(status_code=500, detail="Current agent not set")

    next_agent = get_next_pipeline_agent(db, current_agent.slug)
    if not next_agent:
        run.current_agent_id = None
        run.is_waiting_for_user = False
        run.status = "COMPLETED"
        run.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(run)
        return _to_run_response(run)

    artifacts = get_latest_artifacts_by_type(db, run.id)
    context = build_context_for_agent(next_agent.slug, run, artifacts)
    payload = {
        "run_id": run.id,
        "context": context,
        "is_feedback": False,
        "feedback": "",
    }

    run.current_agent_id = next_agent.id
    run.is_waiting_for_user = False
    run.status = f"IN_PROGRESS_{next_agent.slug.upper()}"
    run.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(run)

    bg.add_task(trigger_agent, run.id, next_agent.slug, next_agent.n8n_webhook_url, payload)
    return _to_run_response(run)


@router.post("/runs/{run_id}/reject", response_model=RunResponse)
def reject_run(
    run_id: str,
    body: RejectRunRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if not run.is_waiting_for_user:
        raise HTTPException(status_code=400, detail="Run is not waiting for approval")

    current_agent = run.current_agent
    if not current_agent:
        raise HTTPException(status_code=500, detail="Current agent not set")

    artifact_type = get_expected_artifact_type(current_agent.slug) or "unknown"
    latest_artifact = get_latest_artifact_for_type(db, run.id, artifact_type)
    if not latest_artifact:
        raise HTTPException(status_code=404, detail="No artifact found to retry from")

    try:
        context = json.loads(latest_artifact.content_json)
    except json.JSONDecodeError:
        context = {"raw_content": latest_artifact.content_json}

    payload = {
        "run_id": run.id,
        "context": context,
        "is_feedback": True,
        "feedback": body.feedback,
    }

    run.is_waiting_for_user = False
    run.status = f"RETRYING_{current_agent.slug.upper()}"
    run.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(run)

    bg.add_task(
        trigger_agent,
        run.id,
        current_agent.slug,
        current_agent.n8n_webhook_url,
        payload,
    )
    return _to_run_response(run)
