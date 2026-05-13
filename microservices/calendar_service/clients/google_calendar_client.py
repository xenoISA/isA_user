"""Google Calendar provider client.

Uses direct HTTP requests so calendar_service does not need the heavy Google
SDK at runtime. Callers provide an OAuth access token in the per-request
credentials payload.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

import aiohttp

from .provider_models import ProviderCalendarEvent, ProviderSyncResult


class GoogleCalendarClient:
    def __init__(
        self,
        base_url: str = "https://www.googleapis.com/calendar/v3",
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def list_events(
        self,
        credentials: dict[str, Any] | None,
        *,
        sync_token: str | None = None,
        calendar_id: str = "primary",
        days_ahead: int = 365,
    ) -> ProviderSyncResult:
        access_token = (credentials or {}).get("access_token")
        if not access_token:
            raise ValueError("Google Calendar sync requires OAuth access_token")

        params: dict[str, Any] = {
            "singleEvents": "true",
            "showDeleted": "true",
            "maxResults": 2500,
        }
        if sync_token:
            params["syncToken"] = sync_token
        else:
            now = datetime.now(timezone.utc)
            params["timeMin"] = now.isoformat().replace("+00:00", "Z")
            params["timeMax"] = (
                (now + timedelta(days=days_ahead)).isoformat().replace("+00:00", "Z")
            )

        headers = {"Authorization": f"Bearer {access_token}"}
        events: list[ProviderCalendarEvent] = []
        next_sync_token: str | None = None
        page_token: str | None = None

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            while True:
                if page_token:
                    params["pageToken"] = page_token
                async with session.get(
                    f"{self.base_url}/calendars/{calendar_id}/events",
                    headers=headers,
                    params=params,
                ) as response:
                    if response.status >= 400:
                        body = await response.text()
                        raise RuntimeError(
                            f"Google Calendar API returned {response.status}: {body}"
                        )
                    payload = await response.json()

                events.extend(
                    _map_google_event(item)
                    for item in payload.get("items", [])
                    if item.get("status") != "cancelled"
                )
                page_token = payload.get("nextPageToken")
                next_sync_token = payload.get("nextSyncToken") or next_sync_token
                if not page_token:
                    break

        return ProviderSyncResult(events=events, sync_token=next_sync_token)


def _parse_google_time(
    value: dict[str, Any], *, end: bool = False
) -> tuple[datetime, bool, str]:
    if value.get("dateTime"):
        parsed = datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00"))
        return parsed, False, value.get("timeZone") or "UTC"

    date_value = value.get("date")
    if not date_value:
        raise ValueError("Google event is missing start/end time")
    parsed_date = datetime.fromisoformat(date_value).date()
    if end:
        parsed_date = parsed_date - timedelta(days=1)
    parsed = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
    return parsed, True, value.get("timeZone") or "UTC"


def _map_google_event(item: dict[str, Any]) -> ProviderCalendarEvent:
    start_time, all_day, timezone_name = _parse_google_time(item.get("start", {}))
    end_time, _, _ = _parse_google_time(item.get("end", {}), end=all_day)
    recurrence = item.get("recurrence") or []
    return ProviderCalendarEvent(
        external_event_id=item["id"],
        title=item.get("summary") or "(No title)",
        description=item.get("description"),
        location=item.get("location"),
        start_time=start_time,
        end_time=end_time,
        all_day=all_day,
        timezone=timezone_name,
        recurrence_rule=recurrence[0] if recurrence else None,
        metadata={
            "html_link": item.get("htmlLink"),
            "etag": item.get("etag"),
            "ical_uid": item.get("iCalUID"),
            "provider": "google_calendar",
        },
    )
