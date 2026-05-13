"""Microsoft Outlook Calendar provider client using Microsoft Graph."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from .provider_models import ProviderCalendarEvent, ProviderSyncResult


class OutlookCalendarClient:
    def __init__(
        self,
        base_url: str = "https://graph.microsoft.com/v1.0",
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def list_events(
        self,
        credentials: dict[str, Any] | None,
        *,
        sync_token: str | None = None,
        days_ahead: int = 365,
    ) -> ProviderSyncResult:
        access_token = (credentials or {}).get("access_token")
        if not access_token:
            raise ValueError("Outlook Calendar sync requires OAuth access_token")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Prefer": 'outlook.timezone="UTC", odata.maxpagesize=250',
        }
        now = datetime.now(timezone.utc)
        if sync_token:
            url = sync_token
            params = None
        else:
            url = f"{self.base_url}/me/calendarView/delta"
            params = {
                "startDateTime": now.isoformat().replace("+00:00", "Z"),
                "endDateTime": (now + timedelta(days=days_ahead))
                .isoformat()
                .replace("+00:00", "Z"),
            }

        events: list[ProviderCalendarEvent] = []
        delta_link: str | None = None

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            while True:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status >= 400:
                        body = await response.text()
                        raise RuntimeError(
                            f"Microsoft Graph returned {response.status}: {body}"
                        )
                    payload = await response.json()

                events.extend(
                    _map_outlook_event(item)
                    for item in payload.get("value", [])
                    if "@removed" not in item and not item.get("isCancelled", False)
                )
                next_link = payload.get("@odata.nextLink")
                delta_link = payload.get("@odata.deltaLink") or delta_link
                if not next_link:
                    break
                url = next_link
                params = None

        return ProviderSyncResult(events=events, sync_token=delta_link)


def _parse_outlook_time(value: dict[str, Any]) -> tuple[datetime, str]:
    date_time = value.get("dateTime")
    if not date_time:
        raise ValueError("Outlook event is missing start/end time")
    normalized = date_time.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, value.get("timeZone") or "UTC"


def _map_outlook_event(item: dict[str, Any]) -> ProviderCalendarEvent:
    start_time, timezone_name = _parse_outlook_time(item.get("start", {}))
    end_time, _ = _parse_outlook_time(item.get("end", {}))
    location = item.get("location") or {}
    body_preview = item.get("bodyPreview")
    return ProviderCalendarEvent(
        external_event_id=item["id"],
        title=item.get("subject") or "(No title)",
        description=body_preview,
        location=location.get("displayName") or None,
        start_time=start_time,
        end_time=end_time,
        all_day=bool(item.get("isAllDay", False)),
        timezone=timezone_name,
        recurrence_rule=None,
        metadata={
            "web_link": item.get("webLink"),
            "change_key": item.get("changeKey"),
            "provider": "outlook",
        },
    )
