"""
N8N HTTP client service.

Responsible for building the outgoing request to an n8n webhook and returning
the raw response.  Business logic (what to do with the response) lives in
AgentLogService, not here (Single Responsibility Principle).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger(__name__)


class N8NService:
    """Thin HTTP client that sends trigger requests to n8n webhooks."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.n8n_base_url).rstrip("/")
        self._api_key = api_key or settings.n8n_api_key
        self._timeout = timeout if timeout is not None else settings.n8n_request_timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def trigger_agent(
        self,
        webhook_path: str,
        context: str,
        is_feedback: bool,
        feedback: str | None,
        uuid: str,
        step: int,
        callback_url: str,
    ) -> None:
        """
        Fire an HTTP POST to the n8n webhook for the given agent.

        `webhook_path` is expected to be a full URL (e.g. http://localhost:5678/webhook/…).
        The base_url is NOT prepended so that each agent config owns its complete URL.

        Raises httpx.HTTPStatusError on 4xx/5xx responses.
        """
        url = webhook_path  # already a full URL
        payload: dict[str, Any] = {
            "context": context,
            "is_feedback": is_feedback,
            "feedback": feedback,
            "uuid": uuid,
            "step": step,
            "callback_url": callback_url,
        }

        log.info("Triggering n8n agent step=%d uuid=%s url=%s", step, uuid, url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=self._build_headers())
            log.info(
                "N8N webhook responded step=%d uuid=%s status=%d body=%s",
                step,
                uuid,
                response.status_code,
                response.text[:200],
            )
            response.raise_for_status()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        # Do NOT set Content-Type here: httpx adds it automatically when
        # json= is used, and a duplicate header confuses n8n's router.
        headers: dict[str, str] = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers


# Module-level singleton, importable directly for convenience.
n8n_service = N8NService()
