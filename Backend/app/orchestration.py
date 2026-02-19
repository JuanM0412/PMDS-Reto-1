from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .models import Agent, Artifact, Run


@dataclass(frozen=True)
class PipelineStep:
    slug: str
    name: str
    order: int
    webhook_url: str
    artifact_type: str


PIPELINE_STEPS: list[PipelineStep] = [
    PipelineStep(
        slug="requirements",
        name="Requirements Agent",
        order=1,
        webhook_url="http://localhost:5678/webhook/brief-to-requirements",
        artifact_type="requirements",
    ),
    PipelineStep(
        slug="inception",
        name="Inception Agent",
        order=2,
        webhook_url="http://localhost:5678/webhook/inception",
        artifact_type="inception",
    ),
    PipelineStep(
        slug="agile",
        name="Agile Agent",
        order=3,
        webhook_url="http://localhost:5678/webhook/HU",
        artifact_type="agile",
    ),
    PipelineStep(
        slug="diagramacion",
        name="Diagramacion Agent",
        order=4,
        webhook_url="http://localhost:5678/webhook/Diagramacion",
        artifact_type="diagramacion",
    ),
    PipelineStep(
        slug="pseudocodigo",
        name="Pseudocodigo Agent",
        order=5,
        webhook_url="http://localhost:5678/webhook/Pseudocodigo",
        artifact_type="pseudocodigo",
    ),
    PipelineStep(
        slug="qa",
        name="QA Agent",
        order=6,
        webhook_url="http://localhost:5678/webhook/QA",
        artifact_type="qa",
    ),
]

PIPELINE_SLUGS = [step.slug for step in PIPELINE_STEPS]
PIPELINE_BY_SLUG = {step.slug: step for step in PIPELINE_STEPS}


def get_pipeline_step(slug: str) -> PipelineStep | None:
    return PIPELINE_BY_SLUG.get(slug)


def get_expected_artifact_type(agent_slug: str) -> str | None:
    step = get_pipeline_step(agent_slug)
    return step.artifact_type if step else None


def get_pipeline_agents(db: Session) -> list[Agent]:
    if not PIPELINE_SLUGS:
        return []

    agents = db.scalars(select(Agent).where(Agent.slug.in_(PIPELINE_SLUGS))).all()
    by_slug = {agent.slug: agent for agent in agents}
    return [by_slug[slug] for slug in PIPELINE_SLUGS if slug in by_slug]


def get_first_pipeline_agent(db: Session) -> Agent | None:
    agents = get_pipeline_agents(db)
    return agents[0] if agents else None


def get_next_pipeline_agent(db: Session, current_slug: str) -> Agent | None:
    if current_slug not in PIPELINE_SLUGS:
        return None

    agents_by_slug = {agent.slug: agent for agent in get_pipeline_agents(db)}
    current_index = PIPELINE_SLUGS.index(current_slug)
    for next_slug in PIPELINE_SLUGS[current_index + 1 :]:
        next_agent = agents_by_slug.get(next_slug)
        if next_agent:
            return next_agent
    return None


def get_latest_artifacts_by_type(db: Session, run_id: str) -> dict[str, dict[str, Any]]:
    stmt = (
        select(Artifact)
        .where(Artifact.run_id == run_id)
        .order_by(desc(Artifact.created_at))
    )
    latest: dict[str, dict[str, Any]] = {}
    for artifact in db.scalars(stmt).all():
        if artifact.artifact_type in latest:
            continue
        try:
            latest[artifact.artifact_type] = json.loads(artifact.content_json)
        except json.JSONDecodeError:
            latest[artifact.artifact_type] = {"raw_content": artifact.content_json}
    return latest


def get_latest_artifact_for_type(db: Session, run_id: str, artifact_type: str) -> Artifact | None:
    stmt = (
        select(Artifact)
        .where(Artifact.run_id == run_id, Artifact.artifact_type == artifact_type)
        .order_by(desc(Artifact.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


def build_context_for_agent(
    agent_slug: str,
    run: Run,
    artifacts_by_type: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    requirements = artifacts_by_type.get("requirements")
    inception = artifacts_by_type.get("inception")
    agile = artifacts_by_type.get("agile")
    diagramacion = artifacts_by_type.get("diagramacion")
    pseudocodigo = artifacts_by_type.get("pseudocodigo")

    if agent_slug == "requirements":
        return {"domain": run.domain, "brief": run.brief}

    if agent_slug == "inception":
        return _compact_dict(
            {
                "domain": run.domain,
                "brief": run.brief,
                "requirements": requirements,
            }
        )

    if agent_slug == "agile":
        return _compact_dict({"requirements": requirements, "inception": inception})

    if agent_slug == "diagramacion":
        return _compact_dict(
            {
                "requirements": requirements,
                "inception": inception,
                "agile": agile,
            }
        )

    if agent_slug == "pseudocodigo":
        return _compact_dict(
            {
                "requirements": requirements,
                "agile": agile,
                "diagramacion": diagramacion,
            }
        )

    if agent_slug == "qa":
        return _compact_dict(
            {
                "requirements": requirements,
                "inception": inception,
                "agile": agile,
                "diagramacion": diagramacion,
                "pseudocodigo": pseudocodigo,
            }
        )

    fallback = {"domain": run.domain, "brief": run.brief}
    fallback.update(artifacts_by_type)
    return fallback
