"""Agent Service Client (read-only).

Used by billing_service to fetch counts for the usage overview aggregator
(Story #458). Connects to isA_Agent (`/api/v1/agents/configs`) over HTTP.

Failures are non-fatal — callers should treat any exception as
"agent service unavailable" and degrade gracefully.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AgentClient:
    """Minimal read-only client for isA_Agent."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url or os.getenv(
            "AGENT_SERVICE_URL", "http://localhost:8080"
        )
        self.timeout = timeout

    async def count_agents(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[int]:
        """Return number of agent configs visible to user/org.

        Returns None on error so the caller can include a "warning" in the
        aggregated overview without failing the whole response.
        """
        params = {}
        if status:
            params["status"] = status
        headers = {"X-User-Id": user_id}
        if organization_id:
            headers["X-Organization-Id"] = organization_id

        url = f"{self.base_url}/api/v1/agents/configs"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list):
                    return len(payload)
                if isinstance(payload, dict):
                    items = payload.get("agents") or payload.get("items") or []
                    if isinstance(items, list):
                        return len(items)
                return 0
        except Exception as e:
            logger.warning(f"AgentClient.count_agents failed: {e}")
            return None
