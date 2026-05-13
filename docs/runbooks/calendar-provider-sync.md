# Calendar Provider Sync Runbook

Issue: `isA_user#391`

## Scope

`calendar_service` imports external events into `calendar.calendar_events` and
stores provider cursor state in `calendar.calendar_sync_status.sync_token`.
Google Calendar uses the Calendar API `nextSyncToken`; Microsoft Outlook uses
the full Microsoft Graph `@odata.deltaLink`.

Apple Calendar is intentionally not enabled in this slice. iCloud Calendar
requires CalDAV plus app-specific-password handling, account discovery, and
separate credential storage rules. Until that provider is implemented, Apple
sync returns an explicit CalDAV unsupported error.

## Google Calendar

Credential payload:

```json
{
  "access_token": "<google-oauth-access-token>"
}
```

Required OAuth scope:

```text
https://www.googleapis.com/auth/calendar.readonly
```

Initial sync requests events for the next year with `timeMin`, `timeMax`,
`singleEvents=true`, and `showDeleted=true`. Incremental sync sends only
`syncToken`, because Google rejects sync-token requests combined with time
window filters.

## Microsoft Outlook

Credential payload:

```json
{
  "access_token": "<microsoft-graph-access-token>"
}
```

Required Microsoft Graph permission:

```text
Calendars.Read
```

Initial sync calls `/me/calendarView/delta` with a one-year UTC window.
Incremental sync stores and reuses the complete `@odata.deltaLink` URL returned
by Graph.

## Local Verification

Use a real provider token from the OAuth flow. Do not commit tokens or paste
them into issue comments.

```bash
curl -sS -X POST "http://127.0.0.1:<calendar-port>/api/v1/calendar/sync?user_id=usr_calendar_live_test&provider=google_calendar" \
  -H "Content-Type: application/json" \
  -d '{"access_token": "<redacted>"}'
```

Then verify status and imported events:

```bash
curl -sS "http://127.0.0.1:<calendar-port>/api/v1/calendar/sync/status?user_id=usr_calendar_live_test&provider=google_calendar"
curl -sS "http://127.0.0.1:<calendar-port>/api/v1/calendar/events?user_id=usr_calendar_live_test"
```

Expected result:

- Sync status is `success`.
- `synced_events` is greater than zero for a seeded provider calendar.
- `sync_token` is present after provider sync.
- Re-running sync does not duplicate events with the same provider external id.
