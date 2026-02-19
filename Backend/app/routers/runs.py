from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Agent, Run
from ..orchestration import build_context_for_agent, get_first_pipeline_agent
from ..schemas import AgentResponse, RunCreateRequest, RunResponse
from ..services import trigger_agent
from ..utils.ids import generate_run_id

router = APIRouter(prefix="/runs", tags=["runs"])


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


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    body: RunCreateRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    first_agent = get_first_pipeline_agent(db)
    if not first_agent:
        raise HTTPException(status_code=500, detail="No pipeline agents are configured")

    run_id = generate_run_id()
    now = datetime.utcnow()
    run = Run(
        id=run_id,
        domain=body.domain,
        brief=body.brief,
        status=f"IN_PROGRESS_{first_agent.slug.upper()}",
        current_agent_id=first_agent.id,
        is_waiting_for_user=False,
        created_at=now,
        updated_at=now,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    payload = {
        "run_id": run.id,
        "context": build_context_for_agent(first_agent.slug, run, {}),
        "is_feedback": False,
        "feedback": "",
    }
    bg.add_task(trigger_agent, run.id, first_agent.slug, first_agent.n8n_webhook_url, payload)

    return _to_run_response(run)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_run_response(run)
