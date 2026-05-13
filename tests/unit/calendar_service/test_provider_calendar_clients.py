from __future__ import annotations

from datetime import date

import pytest

from microservices.calendar_service.clients.google_calendar_client import (
    _map_google_event,
)
from microservices.calendar_service.clients.outlook_calendar_client import (
    _map_outlook_event,
)


def test_google_event_mapper_handles_timed_event():
    mapped = _map_google_event(
        {
            "id": "google-1",
            "summary": "Planning",
            "description": "Roadmap",
            "location": "Room 1",
            "start": {"dateTime": "2026-05-13T09:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-05-13T10:00:00Z", "timeZone": "UTC"},
            "recurrence": ["RRULE:FREQ=WEEKLY"],
            "htmlLink": "https://calendar.google.com/event",
        }
    )

    assert mapped.external_event_id == "google-1"
    assert mapped.title == "Planning"
    assert mapped.start_time.isoformat() == "2026-05-13T09:00:00+00:00"
    assert mapped.recurrence_rule == "RRULE:FREQ=WEEKLY"
    assert mapped.metadata["provider"] == "google_calendar"


def test_google_event_mapper_handles_all_day_event():
    mapped = _map_google_event(
        {
            "id": "google-all-day",
            "summary": "Offsite",
            "start": {"date": "2026-05-13"},
            "end": {"date": "2026-05-14"},
        }
    )

    assert mapped.all_day is True
    assert mapped.start_time.date() == date(2026, 5, 13)
    assert mapped.end_time.date() == date(2026, 5, 13)


def test_outlook_event_mapper_handles_graph_event():
    mapped = _map_outlook_event(
        {
            "id": "outlook-1",
            "subject": "Review",
            "bodyPreview": "Quarterly review",
            "start": {"dateTime": "2026-05-13T09:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-05-13T09:30:00", "timeZone": "UTC"},
            "location": {"displayName": "Teams"},
            "webLink": "https://outlook.office.com/calendar/item",
            "changeKey": "abc",
        }
    )

    assert mapped.external_event_id == "outlook-1"
    assert mapped.title == "Review"
    assert mapped.location == "Teams"
    assert mapped.start_time.isoformat() == "2026-05-13T09:00:00+00:00"
    assert mapped.metadata["provider"] == "outlook"


@pytest.mark.asyncio
async def test_google_client_requires_access_token():
    from microservices.calendar_service.clients.google_calendar_client import (
        GoogleCalendarClient,
    )

    with pytest.raises(ValueError, match="access_token"):
        await GoogleCalendarClient().list_events({})


@pytest.mark.asyncio
async def test_outlook_client_requires_access_token():
    from microservices.calendar_service.clients.outlook_calendar_client import (
        OutlookCalendarClient,
    )

    with pytest.raises(ValueError, match="access_token"):
        await OutlookCalendarClient().list_events({})
