from __future__ import annotations

from typing import Any


MERMAID_PREFIXES = (
    "graph ",
    "flowchart",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "quadrantChart",
    "requirementDiagram",
    "gitGraph",
    "C4Context",
    "C4Container",
    "C4Component",
    "C4Dynamic",
    "C4Deployment",
)


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if not lines:
        return text

    first_line = lines[0].strip().lower()
    if first_line not in {"```", "```mermaid"}:
        return text

    content_lines = lines[1:]
    if content_lines and content_lines[-1].strip() == "```":
        content_lines = content_lines[:-1]
    return "\n".join(content_lines).strip()


def _looks_like_mermaid(value: str) -> bool:
    text = value.strip()
    if not text:
        return False

    lowered = text.lower()
    if lowered.startswith("mermaid\n"):
        return True
    return any(text.startswith(prefix) for prefix in MERMAID_PREFIXES)


def normalize_mermaid_code(value: str) -> str:
    text = value.strip().replace("\\r\\n", "\n").replace("\\n", "\n")
    text = _strip_code_fence(text)
    text = text.strip()

    if text.lower().startswith("mermaid\n"):
        text = text.split("\n", 1)[1].strip()

    lines = [line.rstrip().replace("\t", "    ") for line in text.splitlines()]
    return "\n".join(lines).strip()


def normalize_mermaid_artifact(payload: Any) -> Any:
    if isinstance(payload, dict):
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            key_l = key.lower()
            if isinstance(value, str):
                hinted = "mermaid" in key_l or "diagram" in key_l
                if hinted or _looks_like_mermaid(value):
                    normalized[key] = normalize_mermaid_code(value)
                else:
                    normalized[key] = value
            else:
                normalized[key] = normalize_mermaid_artifact(value)
        return normalized

    if isinstance(payload, list):
        return [normalize_mermaid_artifact(item) for item in payload]

    return payload
