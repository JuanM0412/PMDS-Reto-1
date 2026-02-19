from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Artifact, Run
from ..orchestration import get_expected_artifact_type
from ..schemas import (
    ArtifactCreateRequest,
    ArtifactExportItem,
    ArtifactResponse,
    RunArtifactsExportResponse,
)

router = APIRouter(prefix="/runs/{run_id}/artifacts", tags=["artifacts"])


def _extract_artifact_only(content: Any) -> Any:
    if isinstance(content, dict) and "artifact" in content:
        return content["artifact"]
    return content


@router.post("", response_model=ArtifactResponse, status_code=201)
def create_artifact(run_id: str, body: ArtifactCreateRequest, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact_type = body.artifact_type
    if run.current_agent:
        expected_type = get_expected_artifact_type(run.current_agent.slug)
        if expected_type:
            artifact_type = expected_type

    if not artifact_type:
        raise HTTPException(status_code=400, detail="artifact_type is required")

    stmt = (
        select(Artifact)
        .where(Artifact.run_id == run_id, Artifact.artifact_type == artifact_type)
        .order_by(desc(Artifact.version))
        .limit(1)
    )
    last = db.execute(stmt).scalars().first()
    next_version = (last.version + 1) if last else 1

    content_dict = body.content
    if content_dict is None:
        extra_payload = dict(body.model_extra or {})
        extra_payload.pop("artifact_type", None)
        extra_payload.pop("content", None)
        if extra_payload:
            content_dict = extra_payload
        else:
            raise HTTPException(status_code=400, detail="content is required")
    artifact = Artifact(
        run_id=run_id,
        artifact_type=artifact_type,
        version=next_version,
        content_json=json.dumps(content_dict, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    db.add(artifact)

    if run.current_agent:
        run.status = f"WAITING_APPROVAL_{run.current_agent.slug.upper()}"
    else:
        run.status = "WAITING_APPROVAL"
    run.is_waiting_for_user = True
    run.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(artifact)

    return ArtifactResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        artifact_type=artifact.artifact_type,
        version=artifact.version,
        created_at=artifact.created_at,
        content=content_dict,
    )


@router.get("/latest", response_model=ArtifactResponse)
def get_latest_artifact(
    run_id: str,
    artifact_type: str | None = None,
    type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    resolved_type = artifact_type or type
    if not resolved_type:
        raise HTTPException(status_code=400, detail="artifact_type query param is required")

    stmt = (
        select(Artifact)
        .where(Artifact.run_id == run_id, Artifact.artifact_type == resolved_type)
        .order_by(desc(Artifact.created_at))
        .limit(1)
    )
    artifact = db.execute(stmt).scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    content = json.loads(artifact.content_json)
    return ArtifactResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        artifact_type=artifact.artifact_type,
        version=artifact.version,
        created_at=artifact.created_at,
        content=content,
    )


@router.get("/export", response_model=RunArtifactsExportResponse)
def export_artifacts(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    stmt = (
        select(Artifact)
        .where(Artifact.run_id == run_id)
        .order_by(desc(Artifact.created_at))
    )
    rows = db.execute(stmt).scalars().all()

    latest_by_type: dict[str, Artifact] = {}
    for row in rows:
        if row.artifact_type not in latest_by_type:
            latest_by_type[row.artifact_type] = row

    items: list[ArtifactExportItem] = []
    for artifact in latest_by_type.values():
        try:
            content = json.loads(artifact.content_json)
        except json.JSONDecodeError:
            content = {"raw_content": artifact.content_json}

        items.append(
            ArtifactExportItem(
                artifact_type=artifact.artifact_type,
                version=artifact.version,
                created_at=artifact.created_at,
                artifact=_extract_artifact_only(content),
            )
        )

    items.sort(key=lambda x: x.created_at)
    return RunArtifactsExportResponse(
        run_id=run_id,
        exported_at=datetime.utcnow(),
        artifacts=items,
    )
