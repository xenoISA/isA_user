from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.session_service.clients.session_client import SessionServiceClient


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_response(payload=None):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload if payload is not None else {}
    return response


async def test_get_user_sessions_uses_canonical_query_route():
    client = SessionServiceClient(base_url="http://session.local")
    client.client.get = AsyncMock(return_value=_make_response({"sessions": []}))

    result = await client.get_user_sessions(
        user_id="user-1",
        active_only=True,
        page=2,
        page_size=10,
    )

    assert result == {"sessions": []}
    client.client.get.assert_awaited_once_with(
        "http://session.local/api/v1/sessions",
        params={
            "user_id": "user-1",
            "active_only": True,
            "page": 2,
            "page_size": 10,
        },
    )
    await client.close()


async def test_export_user_data_collects_sessions_and_messages():
    client = SessionServiceClient(base_url="http://session.local")
    client.get_user_sessions = AsyncMock(
        return_value={
            "sessions": [
                {"session_id": "sess-1", "title": "Launch plan"},
                {"id": "sess-2", "title": "Review"},
            ],
            "total": 2,
        }
    )
    client.get_messages = AsyncMock(
        side_effect=[
            {
                "messages": [
                    {"message_id": "msg-1", "session_id": "sess-1", "role": "user"}
                ]
            },
            {"messages": []},
        ]
    )

    result = await client.export_user_data(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )

    assert result["schema_version"] == "session-export-v1"
    assert result["service"] == "session_service"
    assert result["user_id"] == "user-1"
    assert result["organization_id"] == "org-1"
    assert result["gdpr_request_id"] == "gdpr_req_1"
    assert result["sessions"]["sessions"][0]["session_id"] == "sess-1"
    assert result["session_messages"]["sess-1"]["messages"][0]["message_id"] == "msg-1"
    assert result["session_messages"]["sess-2"]["messages"] == []
    assert result["counts"] == {
        "records": 3,
        "sections": {"sessions": 2, "messages": 1},
    }
    client.get_user_sessions.assert_awaited_once_with(
        user_id="user-1",
        active_only=False,
        page=1,
        page_size=1000,
    )
    assert client.get_messages.await_count == 2
    await client.close()


async def test_export_user_data_returns_empty_payload_when_user_has_no_sessions():
    client = SessionServiceClient(base_url="http://session.local")
    client.get_user_sessions = AsyncMock(return_value=None)
    client.get_messages = AsyncMock()

    result = await client.export_user_data(
        user_id="missing-user",
        organization_id=None,
        request_id="gdpr_req_missing",
    )

    assert result["user_id"] == "missing-user"
    assert result["organization_id"] is None
    assert result["gdpr_request_id"] == "gdpr_req_missing"
    assert result["sessions"] == {}
    assert result["session_messages"] == {}
    assert result["counts"] == {
        "records": 0,
        "sections": {"sessions": 0, "messages": 0},
    }
    client.get_messages.assert_not_called()
    await client.close()
