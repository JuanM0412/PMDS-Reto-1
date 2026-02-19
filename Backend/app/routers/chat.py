from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Artifact, Run, StepExecution, StepLog
from ..orchestration import (
    build_context_for_agent,
    get_latest_artifacts_by_type,
    get_pipeline_step_by_order,
)
from ..services import trigger_agent
from ..settings import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])


class PostStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, le=6)
    uuid: str = Field(min_length=1, max_length=128)
    context: str = ""
    is_feedback: bool = False


class PostStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class GetLogsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logs: list[str]


class ChatArtifactItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class GetArtifactsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifacts: list[ChatArtifactItem]


def _safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_content": text}


def _extract_artifact_only(content: Any) -> Any:
    if isinstance(content, dict) and "artifact" in content:
        return content["artifact"]
    return content


def _add_step_log(db: Session, execution_id: int, message: str) -> None:
    db.add(
        StepLog(
            execution_id=execution_id,
            message=message,
            created_at=datetime.utcnow(),
        )
    )


def _get_or_create_run(db: Session, run_id: str, initial_context: str) -> Run:
    run = db.get(Run, run_id)
    if run:
        return run

    if not initial_context:
        raise HTTPException(status_code=404, detail="Run not found for this uuid")

    now = datetime.utcnow()
    run = Run(
        id=run_id,
        domain="super-app",
        brief=initial_context,
        status="CREATED",
        is_waiting_for_user=False,
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _get_latest_version(db: Session, run_id: str, artifact_type: str) -> int:
    stmt = (
        select(Artifact.version)
        .where(Artifact.run_id == run_id, Artifact.artifact_type == artifact_type)
        .order_by(desc(Artifact.version))
        .limit(1)
    )
    last_version = db.execute(stmt).scalar_one_or_none()
    return int(last_version or 0)


def _save_artifact(
    db: Session,
    run_id: str,
    artifact_type: str,
    content: dict[str, Any],
) -> Artifact:
    next_version = _get_latest_version(db, run_id, artifact_type) + 1
    artifact = Artifact(
        run_id=run_id,
        artifact_type=artifact_type,
        version=next_version,
        content_json=json.dumps(content, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    db.add(artifact)
    db.flush()
    return artifact


def _extract_artifact_from_trigger_response(response_data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not response_data:
        return None

    body = response_data.get("body")
    if isinstance(body, list) and body:
        first = body[0]
        if isinstance(first, dict) and isinstance(first.get("json"), dict):
            body = first["json"]
        elif isinstance(first, dict):
            body = first

    if isinstance(body, dict) and "artifact" in body:
        return body

    if isinstance(body, dict) and isinstance(body.get("json"), dict):
        nested = body["json"]
        if "artifact" in nested:
            return nested

    return None


def _build_agent_message(step: int, artifact: Artifact, content: Any) -> str:
    step_def = get_pipeline_step_by_order(step)
    step_name = step_def.name if step_def else f"Step {step}"

    summary = f"{step_name} completado. Artefacto v{artifact.version} listo para revision."

    if isinstance(content, dict):
        if isinstance(content.get("justification"), str) and content["justification"].strip():
            snippet = content["justification"].strip().replace("\n", " ")
            return f"{summary}\n\n{snippet[:500]}"

        artifact_section = content.get("artifact")
        if isinstance(artifact_section, dict) and artifact_section:
            keys = list(artifact_section.keys())
            return f"{summary}\n\nSecciones: {', '.join(keys[:8])}."

    return summary


async def _wait_for_new_artifact(
    db: Session,
    run_id: str,
    artifact_type: str,
    min_version: int,
    timeout_seconds: float,
) -> Artifact | None:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        stmt = (
            select(Artifact)
            .where(Artifact.run_id == run_id, Artifact.artifact_type == artifact_type)
            .order_by(desc(Artifact.version))
            .limit(1)
        )
        candidate = db.execute(stmt).scalars().first()
        if candidate and candidate.version > min_version:
            return candidate

        db.expire_all()
        await asyncio.sleep(settings.artifact_poll_interval_seconds)

    return None


@router.post("/step", response_model=PostStepResponse)
async def post_step(body: PostStepRequest, db: Session = Depends(get_db)):
    step_def = get_pipeline_step_by_order(body.step)
    if not step_def:
        raise HTTPException(status_code=400, detail="Invalid step")

    initial_context = body.context.strip() if body.step == 1 and not body.is_feedback else ""
    run = _get_or_create_run(db, body.uuid, initial_context)

    if body.step == 1 and not body.is_feedback and body.context.strip():
        run.brief = body.context.strip()

    if body.is_feedback:
        feedback_text = body.context.strip()
        if not feedback_text:
            raise HTTPException(status_code=400, detail="Feedback is required when is_feedback=true")

        stmt_feedback = (
            select(Artifact)
            .where(Artifact.run_id == run.id, Artifact.artifact_type == step_def.artifact_type)
            .order_by(desc(Artifact.version))
            .limit(1)
        )
        previous = db.execute(stmt_feedback).scalars().first()
        if not previous:
            raise HTTPException(status_code=400, detail="No artifact found to apply feedback")

        context_payload = _safe_json_loads(previous.content_json)
    else:
        feedback_text = ""
        if body.step == 1:
            context_payload = body.context.strip()
            if not context_payload:
                raise HTTPException(status_code=400, detail="Context is required for step 1")
        else:
            artifacts_by_type = get_latest_artifacts_by_type(db, run.id)
            context_payload = build_context_for_agent(step_def.slug, run, artifacts_by_type)

    payload = {
        "run_id": run.id,
        "context": context_payload,
        "is_feedback": body.is_feedback,
        "feedback": feedback_text,
    }
    request_deadline = time.monotonic() + settings.step_wait_timeout_seconds

    stmt_attempt = select(func.max(StepExecution.attempt)).where(
        StepExecution.run_id == run.id,
        StepExecution.step == body.step,
    )
    previous_attempt = db.execute(stmt_attempt).scalar_one_or_none() or 0

    execution = StepExecution(
        run_id=run.id,
        step=body.step,
        agent_slug=step_def.slug,
        attempt=int(previous_attempt) + 1,
        is_feedback=body.is_feedback,
        feedback_text=feedback_text if body.is_feedback else None,
        status="STARTED",
        request_payload_json=json.dumps(payload, ensure_ascii=False),
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    _add_step_log(db, execution.id, f"Solicitud recibida para step {body.step} ({step_def.slug}).")

    baseline_version = _get_latest_version(db, run.id, step_def.artifact_type)
    _add_step_log(
        db,
        execution.id,
        f"Enviando payload al webhook {step_def.webhook_url} (timeout total {settings.step_wait_timeout_seconds:.0f}s).",
    )

    run.status = f"IN_PROGRESS_STEP_{body.step}"
    run.current_agent_id = None
    run.is_waiting_for_user = False
    run.updated_at = datetime.utcnow()
    db.commit()

    trigger_response: dict[str, Any] | None = None
    try:
        remaining_for_trigger = request_deadline - time.monotonic()
        if remaining_for_trigger <= 0:
            timeout_message = (
                f"{step_def.name}: tiempo de espera agotado antes de ejecutar el webhook."
            )
            execution.status = "TIMEOUT"
            execution.response_message = timeout_message
            execution.finished_at = datetime.utcnow()
            run.status = f"TIMEOUT_STEP_{body.step}"
            run.updated_at = datetime.utcnow()
            _add_step_log(db, execution.id, timeout_message)
            db.commit()
            return PostStepResponse(message=timeout_message)

        trigger_response = await trigger_agent(
            run.id,
            step_def.slug,
            step_def.webhook_url,
            payload,
            timeout_seconds=remaining_for_trigger,
        )
        execution.status = "WAITING_RESULT"
        _add_step_log(db, execution.id, "Webhook ejecutado. Esperando artefacto final.")
        db.commit()
    except Exception as exc:
        execution.status = "ERROR"
        execution.finished_at = datetime.utcnow()
        error_message = f"Error ejecutando {step_def.name}: {str(exc)[:350]}"
        execution.response_message = error_message
        run.status = f"ERROR_STEP_{body.step}"
        run.updated_at = datetime.utcnow()
        _add_step_log(db, execution.id, error_message)
        db.commit()
        return PostStepResponse(message=error_message)

    artifact = await _wait_for_new_artifact(
        db,
        run.id,
        step_def.artifact_type,
        baseline_version,
        max(0.0, request_deadline - time.monotonic()),
    )

    if artifact is None:
        fallback_content = _extract_artifact_from_trigger_response(trigger_response)
        if fallback_content is not None:
            artifact = _save_artifact(db, run.id, step_def.artifact_type, fallback_content)
            _add_step_log(
                db,
                execution.id,
                "No llego callback a tiempo; se persiste artefacto desde respuesta directa del webhook.",
            )
            db.commit()

    if artifact is None:
        timeout_message = (
            f"{step_def.name}: sigue en procesamiento. Intenta consultar logs y artifacts en unos segundos."
        )
        execution.status = "TIMEOUT"
        execution.response_message = timeout_message
        execution.finished_at = datetime.utcnow()
        run.status = f"TIMEOUT_STEP_{body.step}"
        run.updated_at = datetime.utcnow()
        _add_step_log(db, execution.id, timeout_message)
        db.commit()
        return PostStepResponse(message=timeout_message)

    parsed_content = _safe_json_loads(artifact.content_json)
    message = _build_agent_message(body.step, artifact, parsed_content)

    execution.status = "COMPLETED"
    execution.response_message = message
    execution.finished_at = datetime.utcnow()

    run.status = f"WAITING_APPROVAL_STEP_{body.step}"
    run.is_waiting_for_user = True
    run.updated_at = datetime.utcnow()

    _add_step_log(
        db,
        execution.id,
        f"Artefacto recibido y guardado como {step_def.artifact_type} v{artifact.version}.",
    )

    db.commit()
    return PostStepResponse(message=message)


@router.get("/logs", response_model=GetLogsResponse)
def get_logs(
    step: int = Query(..., ge=1, le=6),
    uuid: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    run = db.get(Run, uuid)
    if not run:
        return GetLogsResponse(logs=[])

    stmt = (
        select(StepExecution)
        .where(StepExecution.run_id == uuid, StepExecution.step == step)
        .order_by(StepExecution.attempt.asc(), StepExecution.started_at.asc())
    )
    executions = db.execute(stmt).scalars().all()

    logs: list[str] = []
    for execution in executions:
        if execution.logs:
            ordered_logs = sorted(execution.logs, key=lambda log: log.created_at)
            for log in ordered_logs:
                logs.append(f"[attempt {execution.attempt}] {log.message}")
        if execution.response_message:
            logs.append(f"[attempt {execution.attempt}] response: {execution.response_message}")

    return GetLogsResponse(logs=logs)


@router.get("/artifacts", response_model=GetArtifactsResponse)
def get_artifacts(
    step: int = Query(..., ge=1, le=6),
    uuid: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    step_def = get_pipeline_step_by_order(step)
    if not step_def:
        raise HTTPException(status_code=400, detail="Invalid step")

    stmt = (
        select(Artifact)
        .where(Artifact.run_id == uuid, Artifact.artifact_type == step_def.artifact_type)
        .order_by(desc(Artifact.version), desc(Artifact.created_at))
    )
    rows = db.execute(stmt).scalars().all()

    artifacts = [
        ChatArtifactItem(
            id=str(row.id),
            name=f"{step_def.name} v{row.version} - {row.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        for row in rows
    ]
    return GetArtifactsResponse(artifacts=artifacts)


@router.get("/artifacts/download")
def download_artifact(
    step: int = Query(..., ge=1, le=6),
    uuid: str = Query(..., min_length=1),
    id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    step_def = get_pipeline_step_by_order(step)
    if not step_def:
        raise HTTPException(status_code=400, detail="Invalid step")

    try:
        artifact_id = int(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid artifact id") from exc

    artifact = db.get(Artifact, artifact_id)
    if not artifact or artifact.run_id != uuid:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.artifact_type != step_def.artifact_type:
        raise HTTPException(status_code=400, detail="Artifact does not belong to requested step")

    parsed = _safe_json_loads(artifact.content_json)
    return _extract_artifact_only(parsed)
