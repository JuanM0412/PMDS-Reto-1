"""
AgentLog business-logic service.

Orchestrates between the repository (persistence) and the rest of the
application.  Routers depend on this service, not on the repository directly
(Dependency Inversion + Single Responsibility Principles).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from ..models.agent_log import AgentLog
from ..repositories.agent_log_repository import AgentLogRepository
from ..constants.agents import ARTIFACT_TYPE_TO_STEP
from ..schemas.n8n import N8NCallbackRequest

log = logging.getLogger(__name__)


class AgentLogService:
    """Business-logic layer for agent log operations."""

    def __init__(self, db: Session) -> None:
        self._repo = AgentLogRepository(db)
        self._db = db

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def record_n8n_result(self, payload: N8NCallbackRequest) -> AgentLog:
        """
        Persist the result returned by n8n after it finishes a pipeline step.

        N8N sends the entire structured response inside the `content` field as a
        markdown code block wrapping a JSON object with keys:
            artifact, changes_made, justification
        This method unwraps and parses that nested payload before storing.
        """
        step = payload.step or ARTIFACT_TYPE_TO_STEP.get(payload.artifact_type)
        if step is None:
            log.warning(
                "Unknown artifact_type='%s' for uuid=%s — storing step as NULL.",
                payload.artifact_type,
                payload.uuid,
            )

        parsed = self._parse_content(payload.content)

        # Determine whether the top-level parse yielded the expected structure
        # (i.e. a dict that has at least one of the known n8n response keys).
        _N8N_KEYS = {"artifact", "changes_made", "justification"}
        parsed_is_n8n_response = isinstance(parsed, dict) and bool(_N8N_KEYS & parsed.keys())

        # The actual artifact to store is the inner "artifact" dict when available,
        # otherwise the raw parsed content, keyed by artifact_type.
        inner_artifact = parsed.get("artifact") if parsed_is_n8n_response else None
        artefact = {payload.artifact_type: inner_artifact if inner_artifact is not None else parsed}

        # --- Primary path: extract metadata from the parsed content ---------------
        if parsed_is_n8n_response:
            changes = parsed.get("changes_made") or {}
            if not isinstance(changes, dict):
                changes = {}
            justification: str | None = parsed.get("justification") or None
            added: list[str] = changes.get("added") or []
            modified: list[str] = changes.get("modified") or []
            deleted: list[str] = changes.get("removed") or []
        else:
            # --- Fallback path: _parse_content did not produce the expected shape.
            # Re-use the same fence-stripping + JSON extraction that get_logs uses,
            # applied to the artefact blob we are about to store.
            meta = self._extract_metadata_from_artefact(artefact)
            justification = meta.get("justification") or payload.justification or None
            added = meta.get("added") or payload.changes_made.added or []
            modified = meta.get("modified") or payload.changes_made.modified or []
            deleted = meta.get("deleted") or payload.changes_made.removed or []

        log.debug(
            "record_n8n_result uuid=%s step=%s parsed_ok=%s just=%s added=%s",
            payload.uuid, step, parsed_is_n8n_response, bool(justification), added,
        )

        agent_log = self._repo.create(
            input=payload.context,
            uuid=payload.uuid,
            agent=step,
            artefact=artefact,
            justification=justification or None,
            added=added or None,
            modified=modified or None,
            deleted=deleted or None,
        )
        self._db.commit()
        self._db.refresh(agent_log)
        log.info(
            "Recorded n8n result id=%d uuid=%s step=%s artifact_type=%s",
            agent_log.id, payload.uuid, step, payload.artifact_type,
        )
        return agent_log

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_logs(self, uuid: str, step: int) -> list[str]:
        """
        Return human-readable log lines for a given session uuid and step.

        Each record produces a block with: timestamp, input, feedback (if any),
        justification, changes (added / modified / deleted) and artifact types.
        Falls back to parsing the artefact blob for legacy records where the
        separate metadata columns were not populated.
        Called by Endpoint 2.
        """
        records = self._repo.get_by_uuid_and_step(uuid=uuid, step=step)
        lines: list[str] = []

        for idx, record in enumerate(records, start=1):
            ts = record.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            lines.append(f"[Run {idx} — {ts}]")

            # User input / feedback
            if record.input and record.input.strip():
                lines.append(f"  Input: {record.input.strip()}")

            # Resolve metadata: prefer dedicated columns, fall back to artefact blob
            justification = record.justification
            added_raw = record.added
            modified_raw = record.modified
            deleted_raw = record.deleted

            if not all([justification, added_raw, modified_raw, deleted_raw]):
                meta = self._extract_metadata_from_artefact(record.artefact)
                if not justification:
                    justification = meta.get("justification")
                if not added_raw and meta.get("added"):
                    added_raw = json.dumps(meta["added"], ensure_ascii=False)
                if not modified_raw and meta.get("modified"):
                    modified_raw = json.dumps(meta["modified"], ensure_ascii=False)
                if not deleted_raw and meta.get("deleted"):
                    deleted_raw = json.dumps(meta["deleted"], ensure_ascii=False)

            # Agent justification
            if justification:
                lines.append(f"  Justification: {justification}")

            # Changes
            if added_raw:
                items = self._safe_json_loads(added_raw)
                if items:
                    lines.append(f"  Added: {', '.join(str(i) for i in items)}")

            if modified_raw:
                items = self._safe_json_loads(modified_raw)
                if items:
                    lines.append(f"  Modified: {', '.join(str(i) for i in items)}")

            if deleted_raw:
                items = self._safe_json_loads(deleted_raw)
                if items:
                    lines.append(f"  Deleted: {', '.join(str(i) for i in items)}")

            # Artifact types produced
            artifact_keys = list((record.artefact or {}).keys())
            if artifact_keys:
                lines.append(f"  Artifacts produced: {', '.join(artifact_keys)}")

            lines.append("")  # blank separator between runs

        return lines

    def get_artifacts(self, uuid: str, step: int) -> list[dict[str, str]]:
        """
        Return a list of artifact descriptors for a given session uuid and step.

        Scans the most recent record and extracts top-level artifact type keys.
        Each key becomes an {id, name} item so the frontend can list them.
        Called by Endpoint 4.
        """
        record = self._repo.get_latest_by_uuid_and_step(uuid=uuid, step=step)
        if record is None:
            return []

        artifact_data: dict[str, Any] = record.artefact or {}

        items: list[dict[str, str]] = []
        for key in artifact_data:
            items.append(
                {
                    "id": key,
                    "name": key.replace("_", " ").title(),
                }
            )
        return items

    def get_artifact_content(
        self, uuid: str, step: int, artifact_id: str
    ) -> dict[str, Any] | None:
        """
        Return the content of a specific artifact by its type key.

        Called by Endpoint 5.
        Content may be stored as a raw string (old records) and is parsed on read.
        """
        record = self._repo.get_latest_by_uuid_and_step(uuid=uuid, step=step)
        if record is None:
            return None

        artifact_data: dict[str, Any] = record.artefact or {}
        raw = artifact_data.get(artifact_id)
        if raw is None:
            return None

        # Parse on read for records stored before the content-parsing fix
        if isinstance(raw, str):
            parsed = self._parse_content(raw)
            if isinstance(parsed, dict):
                return parsed.get("artifact", parsed)
            return {"raw": raw}

        return raw

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metadata_from_artefact(artefact: dict | None) -> dict:
        """
        For legacy records where justification/changes_made were not stored in
        dedicated columns, extract them by parsing the artefact blob.

        The blob may look like::

            {"requirements": "```\n{\"artifact\":{...},\"changes_made\":{...},\"justification\":\"...\"}\n```"}

        Returns a dict with keys: justification, added, modified, deleted.
        """
        if not artefact:
            return {}

        for raw_value in artefact.values():
            if not isinstance(raw_value, str):
                continue
            # Reuse the existing fence-stripping + JSON parser
            parsed = AgentLogService._parse_content(raw_value)
            if not isinstance(parsed, dict):
                continue
            changes = parsed.get("changes_made", {})
            if not isinstance(changes, dict):
                changes = {}
            return {
                "justification": parsed.get("justification") or None,
                "added": changes.get("added") or [],
                "modified": changes.get("modified") or [],
                "deleted": changes.get("removed") or [],
            }

        return {}

    @staticmethod
    def _parse_content(content: Any) -> Any:
        """
        Unwrap and parse the content sent by n8n.

        N8N wraps the response JSON inside a markdown code block:
            ```
            { "artifact": {...}, "changes_made": {...}, "justification": "..." }
            ```
        This method strips the fences and parses the inner JSON.
        If content is already a dict it is returned as-is.
        If parsing fails the raw value is returned unchanged.
        """
        if isinstance(content, dict):
            return content

        if not isinstance(content, str):
            return content

        # Strip markdown code fences (``` or ```json).
        # LLMs often add preamble text before the fence, so search anywhere
        # in the string rather than requiring it to start at position 0.
        stripped = content.strip()
        fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', stripped)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except (json.JSONDecodeError, ValueError):
                pass

        # No fence — try parsing the whole string as-is.
        try:
            return json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            log.debug("Could not parse content as JSON, storing as raw string.")
            return content

    @staticmethod
    def _safe_json_loads(text: str) -> list[Any]:
        try:
            result = json.loads(text)
            return result if isinstance(result, list) else [result]
        except (json.JSONDecodeError, TypeError):
            return [text]
