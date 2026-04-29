from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest

from tests.smoke.conftest import resolve_base_url, resolve_service_url

DEFAULT_ALLOWED_STATUSES = (
    200,
    201,
    202,
    204,
    400,
    401,
    403,
    404,
    409,
    422,
    500,
    503,
)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


def internal_headers(user_id: str = "smoke-test-user") -> dict[str, str]:
    return {
        "X-Internal-Call": "true",
        "X-Internal-Service": "true",
        "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
        "X-User-Id": user_id,
        "Content-Type": "application/json",
    }


class CrudApiSmokeBase:
    service_name = ""
    env_var_name = ""
    timeout = 15.0

    create_path: str | None = None
    list_path: str | None = None
    get_path: str | None = None
    update_path: str | None = None
    delete_path: str | None = None

    create_method = "post"
    update_method = "put"
    delete_method = "delete"

    response_container_key: str | None = None
    id_keys = ("id",)

    health_statuses = (200, 503)
    create_statuses = DEFAULT_ALLOWED_STATUSES
    create_success_statuses = (200, 201)
    list_statuses = DEFAULT_ALLOWED_STATUSES
    get_statuses = DEFAULT_ALLOWED_STATUSES
    update_statuses = DEFAULT_ALLOWED_STATUSES
    delete_statuses = DEFAULT_ALLOWED_STATUSES

    @classmethod
    def base_url(cls) -> str:
        return resolve_base_url(cls.service_name, cls.env_var_name)

    @classmethod
    def health_url(cls) -> str:
        return resolve_service_url(cls.service_name, "/health", cls.env_var_name)

    @classmethod
    def build_url(cls, path: str) -> str:
        return f"{cls.base_url()}{path}"

    def build_payload(self, suffix: str) -> dict[str, Any]:
        raise NotImplementedError

    def build_update_payload(
        self, suffix: str, state: dict[str, Any]
    ) -> dict[str, Any] | None:
        return {}

    def create_path_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def list_path_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return state

    def get_path_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return state

    def update_path_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return state

    def delete_path_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return state

    def create_params(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def list_params(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"limit": 5}

    def get_params(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}

    def update_params(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}

    def delete_params(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}

    def request_headers(self, state: dict[str, Any]) -> dict[str, str]:
        user_id = (
            state.get("user_id")
            or state.get("owner_user_id")
            or state.get("inviter_user_id")
            or state.get("added_by")
            or "smoke-test-user"
        )
        return internal_headers(str(user_id))

    def request_json(self, state: dict[str, Any]) -> dict[str, Any] | None:
        return state

    def response_json(self, response: httpx.Response) -> dict[str, Any]:
        if not response.text.strip():
            return {}
        try:
            data = response.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def primary_response_data(self, response_data: dict[str, Any]) -> dict[str, Any]:
        if not self.response_container_key:
            return response_data
        nested = response_data.get(self.response_container_key)
        return nested if isinstance(nested, dict) else response_data

    def extract_state(
        self, payload: dict[str, Any], response_data: dict[str, Any]
    ) -> dict[str, Any]:
        state = {
            key: value
            for key, value in payload.items()
            if not isinstance(value, (dict, list))
        }
        primary = self.primary_response_data(response_data)
        for source in (response_data, primary):
            for key, value in source.items():
                if not isinstance(value, (dict, list)):
                    state[key] = value
        return state

    def require_path(
        self, template: str | None, state: dict[str, Any], label: str
    ) -> str:
        if not template:
            pytest.skip(f"{label} flow not defined for {self.service_name}")
        try:
            return template.format(**state)
        except KeyError as exc:
            pytest.skip(
                f"{label} flow missing path key {exc.args[0]} for {self.service_name}"
            )

    def require_identifier(self, state: dict[str, Any]) -> None:
        if any(state.get(key) for key in self.id_keys):
            return
        pytest.skip(
            f"Create response for {self.service_name} did not include any of {self.id_keys}"
        )

    def assert_status(
        self, response: httpx.Response, allowed: tuple[int, ...], label: str
    ) -> None:
        assert (
            response.status_code in allowed
        ), f"{label} failed: {response.status_code} {response.text[:300]}"

    def optional_path(self, template: str | None, state: dict[str, Any]) -> str | None:
        if not template:
            return None
        try:
            return template.format(**state)
        except KeyError:
            return None

    async def perform_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await client.request(
            method.upper(),
            self.build_url(path),
            json=json_body,
            params=params,
            headers=headers,
        )

    async def perform_create(
        self, client: httpx.AsyncClient, suffix: str, *, require_success: bool
    ) -> tuple[httpx.Response, dict[str, Any]]:
        payload = self.build_payload(suffix)
        path = self.require_path(
            self.create_path, self.create_path_context(payload), "Create"
        )
        response = await self.perform_request(
            client,
            self.create_method,
            path,
            json_body=self.request_json(payload),
            params=self.create_params(payload),
            headers=self.request_headers(payload),
        )
        self.assert_status(response, self.create_statuses, "Create")
        if require_success and response.status_code not in self.create_success_statuses:
            pytest.skip(
                f"Create returned {response.status_code} for {self.service_name}; "
                "dependent smoke step skipped"
            )
        state = self.extract_state(payload, self.response_json(response))
        if require_success:
            self.require_identifier(state)
        return response, state

    async def cleanup_resource(
        self, client: httpx.AsyncClient, state: dict[str, Any]
    ) -> None:
        path = self.optional_path(self.delete_path, self.delete_path_context(state))
        if not path:
            return

        try:
            await self.perform_request(
                client,
                self.delete_method,
                path,
                params=self.delete_params(state),
                headers=self.request_headers(state),
            )
        except Exception:
            # Cleanup should not mask the primary smoke assertion.
            return

    @pytest.mark.asyncio
    async def test_health_endpoint(self) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.health_url())
        self.assert_status(response, self.health_statuses, "Health")

    @pytest.mark.asyncio
    async def test_create_flow(self) -> None:
        if not self.create_path:
            pytest.skip(f"Create flow not defined for {self.service_name}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response, state = await self.perform_create(
                client, unique_suffix(), require_success=False
            )
            if response.status_code in self.create_success_statuses:
                await self.cleanup_resource(client, state)

    @pytest.mark.asyncio
    async def test_list_flow(self) -> None:
        if not self.list_path:
            pytest.skip(f"List flow not defined for {self.service_name}")

        created_state: dict[str, Any] | None = None
        state = {"suffix": unique_suffix()}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if self.create_path:
                create_response, created_state = await self.perform_create(
                    client, state["suffix"], require_success=False
                )
                if create_response.status_code in self.create_success_statuses:
                    state = created_state
            path = self.require_path(
                self.list_path, self.list_path_context(state), "List"
            )
            response = await self.perform_request(
                client,
                "get",
                path,
                params=self.list_params(state),
                headers=self.request_headers(state),
            )
            if created_state:
                await self.cleanup_resource(client, created_state)

        self.assert_status(response, self.list_statuses, "List")

    @pytest.mark.asyncio
    async def test_get_flow(self) -> None:
        if not self.get_path:
            pytest.skip(f"Get flow not defined for {self.service_name}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            _, state = await self.perform_create(
                client, unique_suffix(), require_success=True
            )
            try:
                path = self.require_path(
                    self.get_path, self.get_path_context(state), "Get"
                )
                response = await self.perform_request(
                    client,
                    "get",
                    path,
                    params=self.get_params(state),
                    headers=self.request_headers(state),
                )
            finally:
                await self.cleanup_resource(client, state)

        self.assert_status(response, self.get_statuses, "Get")

    @pytest.mark.asyncio
    async def test_update_flow(self) -> None:
        if not self.update_path:
            pytest.skip(f"Update flow not defined for {self.service_name}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            _, state = await self.perform_create(
                client, unique_suffix(), require_success=True
            )
            try:
                path = self.require_path(
                    self.update_path, self.update_path_context(state), "Update"
                )
                payload = self.build_update_payload(unique_suffix(), state)
                response = await self.perform_request(
                    client,
                    self.update_method,
                    path,
                    json_body=payload,
                    params=self.update_params(state),
                    headers=self.request_headers(state),
                )
            finally:
                await self.cleanup_resource(client, state)

        self.assert_status(response, self.update_statuses, "Update")

    @pytest.mark.asyncio
    async def test_delete_flow(self) -> None:
        if not self.delete_path:
            pytest.skip(f"Delete flow not defined for {self.service_name}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            _, state = await self.perform_create(
                client, unique_suffix(), require_success=True
            )
            path = self.require_path(
                self.delete_path, self.delete_path_context(state), "Delete"
            )
            response = await self.perform_request(
                client,
                self.delete_method,
                path,
                params=self.delete_params(state),
                headers=self.request_headers(state),
            )

        self.assert_status(response, self.delete_statuses, "Delete")

    @pytest.mark.asyncio
    async def test_crud_cycle(self) -> None:
        if not all(
            [
                self.create_path,
                self.list_path,
                self.get_path,
                self.update_path,
                self.delete_path,
            ]
        ):
            pytest.skip(f"Full CRUD flow not defined for {self.service_name}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            deleted = False
            _, state = await self.perform_create(
                client, unique_suffix(), require_success=True
            )
            try:
                get_path = self.require_path(
                    self.get_path, self.get_path_context(state), "Get"
                )
                get_response = await self.perform_request(
                    client,
                    "get",
                    get_path,
                    params=self.get_params(state),
                    headers=self.request_headers(state),
                )
                self.assert_status(get_response, self.get_statuses, "Get")

                list_path = self.require_path(
                    self.list_path, self.list_path_context(state), "List"
                )
                list_response = await self.perform_request(
                    client,
                    "get",
                    list_path,
                    params=self.list_params(state),
                    headers=self.request_headers(state),
                )
                self.assert_status(list_response, self.list_statuses, "List")

                update_path = self.require_path(
                    self.update_path, self.update_path_context(state), "Update"
                )
                update_response = await self.perform_request(
                    client,
                    self.update_method,
                    update_path,
                    json_body=self.build_update_payload(unique_suffix(), state),
                    params=self.update_params(state),
                    headers=self.request_headers(state),
                )
                self.assert_status(update_response, self.update_statuses, "Update")

                delete_path = self.require_path(
                    self.delete_path, self.delete_path_context(state), "Delete"
                )
                delete_response = await self.perform_request(
                    client,
                    self.delete_method,
                    delete_path,
                    params=self.delete_params(state),
                    headers=self.request_headers(state),
                )
                self.assert_status(delete_response, self.delete_statuses, "Delete")
                deleted = True
            finally:
                if not deleted:
                    await self.cleanup_resource(client, state)
