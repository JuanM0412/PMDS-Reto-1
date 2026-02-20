from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration for a single pipeline agent."""

    step: int          # 1-6, corresponds to the pipeline position
    name: str          # Human-readable name
    webhook_path: str  # N8N webhook path (appended to n8n_base_url)
    artifact_types: list[str]  # Artifact types this agent produces


# Pipeline agents in execution order (step 1 → 6)
AGENTS: list[AgentConfig] = [
    AgentConfig(
        step=1,
        name="Requirements Agent",
        webhook_path="http://localhost:5678/webhook/brief-to-requirements",
        artifact_types=[
            "requirements",
        ],
    ),
    AgentConfig(
        step=2,
        name="Inception Agent",
        webhook_path="http://localhost:5678/webhook/inception",
        artifact_types=[
            "inception",
        ],
    ),
    AgentConfig(
        step=3,
        name="Agile Agent",
        webhook_path="http://localhost:5678/webhook/HU",
        artifact_types=[
            "epics",
        ],
    ),
    AgentConfig(
        step=4,
        name="Diagramacion Agent",
        webhook_path="http://localhost:5678/webhook/Diagramacion",
        artifact_types=[
            "diagrams"
        ],
    ),
    AgentConfig(
        step=5,
        name="Pseudocode Agent",
        webhook_path="http://localhost:5678/webhook/Pseudocodigo",
        artifact_types=[
            "user_story_pseudocode",
        ],
    ),
    AgentConfig(
        step=6,
        name="QA Agent",
        webhook_path="http://localhost:5678/webhook/QA",
        artifact_types=[
            "test_suites",
        ],
    ),
]

# Lookup maps for O(1) access
AGENTS_BY_STEP: dict[int, AgentConfig] = {agent.step: agent for agent in AGENTS}

# Reverse lookup: artifact_type → step number
ARTIFACT_TYPE_TO_STEP: dict[str, int] = {
    artifact_type: agent.step
    for agent in AGENTS
    for artifact_type in agent.artifact_types
}
