"""Shared models for external calendar provider clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ProviderCalendarEvent:
    external_event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    description: str | None = None
    location: str | None = None
    timezone: str = "UTC"
    recurrence_rule: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderSyncResult:
    events: list[ProviderCalendarEvent]
    sync_token: str | None = None
