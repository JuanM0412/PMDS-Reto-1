from __future__ import annotations

import logging
from typing import Any

import httpx

from .settings import settings

log = logging.getLogger("services.n8n")


async def trigger_n8n_requirements(run_id: str, domain: str, brief: str) -> None:
    payload = {"run_id": run_id, "domain": domain, "brief": brief}

    headers = {}
    if settings.n8n_api_key:
        headers["X-API-Key"] = settings.n8n_api_key

    timeout = settings.request_timeout_seconds

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(str(settings.n8n_webhook_url), json=payload, headers=headers)
        resp.raise_for_status()

    log.info("Triggered n8n workflow for run_id=%s", run_id)


async def trigger_agent(
    run_id: str,
    agent_slug: str,
    agent_url: str,
    payload: dict[str, Any],
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """
    Trigger for any agent and return response metadata/body.
    """
    log.info("Triggering agent %s at %s for run_id=%s", agent_slug, agent_url, run_id)

    headers = {}
    if settings.n8n_api_key:
        headers["X-API-Key"] = settings.n8n_api_key

    timeout = timeout_seconds if timeout_seconds is not None else settings.request_timeout_seconds

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(agent_url, json=payload, headers=headers)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                body: Any = resp.json()
            else:
                text_body = resp.text
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw_text": text_body}

            return {
                "status_code": resp.status_code,
                "body": body,
            }
    except Exception:
        log.exception("Failed to trigger agent %s", agent_slug)
        raise
