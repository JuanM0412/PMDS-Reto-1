from __future__ import annotations
import logging
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


async def trigger_agent(run_id: str, agent_slug: str, agent_url: str, payload: dict) -> None:
    """
    Generic trigger for any agent.
    """
    log.info(f"Triggering agent {agent_slug} at {agent_url} for run_id={run_id}")
    
    headers = {}
    if settings.n8n_api_key:
        headers["X-API-Key"] = settings.n8n_api_key

    timeout = settings.request_timeout_seconds

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(agent_url, json=payload, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        log.error(f"Failed to trigger agent {agent_slug}: {e}")
        # En un sistema real, aquí manejaríamos reintentos o marcaríamos el Run como ERROR
        raise e
