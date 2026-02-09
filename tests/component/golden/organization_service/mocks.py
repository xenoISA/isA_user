"""
Organization Service - Mock Dependencies

Mock implementations for component testing.
Returns response model objects as expected by the service.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

# Import the actual models used by the service
from microservices.organization_service.models import (
    OrganizationResponse,
    OrganizationMemberResponse,
    OrganizationPlan,
    OrganizationStatus,
    OrganizationRole,
    MemberStatus,
)


class MockOrganizationRepository:
    """Mock organization repository for component testing

    Implements OrganizationRepositoryProtocol interface.
    """

    def __init__(self):
        self._organizations: Dict[str, Dict] = {}
        self._members: Dict[str, List[Dict]] = {}  # org_id -> list of members
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_organization(
        self,
        organization_id: str,
        name: str,
        billing_email: str,
        plan: str = "free",
        status: str = "active",
        member_count: int = 1,
        credits_pool: float = 0.0,
        settings: Optional[Dict] = None,
        created_at: Optional[datetime] = None
    ):
        """Add an organization to the mock repository"""
        self._organizations[organization_id] = {
            "organization_id": organization_id,
            "name": name,
            "billing_email": billing_email,
            "plan": plan,
            "status": status,
            "member_count": member_count,
            "credits_pool": credits_pool,
            "settings": settings or {},
            "created_at": created_at or datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    def set_member(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member",
        status: str = "active",
        permissions: Optional[List[str]] = None,
        joined_at: Optional[datetime] = None
    ):
        """Add a member to the mock repository"""
        if organization_id not in self._members:
            self._members[organization_id] = []

        self._members[organization_id].append({
            "user_id": user_id,
            "organization_id": organization_id,
            "role": role,
            "status": status,
            "permissions": permissions or [],
            "joined_at": joined_at or datetime.now(timezone.utc)
        })

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    async def create_organization(
        self,
        data: Dict[str, Any],
        owner_user_id: str
    ) -> OrganizationResponse:
        """Create organization and add owner as member"""
        self._log_call("create_organization", data=data, owner_user_id=owner_user_id)

        if self._error:
            raise self._error

        org_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        org_data = {
            "organization_id": org_id,
            "name": data.get("name"),
            "domain": data.get("domain"),
            "billing_email": data.get("billing_email"),
            "plan": data.get("plan", "free"),
            "status": "active",
            "member_count": 1,
            "credits_pool": 0,
            "settings": data.get("settings", {}),
            "created_at": now,
            "updated_at": now
        }

        self._organizations[org_id] = org_data

        # Add owner as member
        self.set_member(org_id, owner_user_id, role="owner", status="active")

        return OrganizationResponse(**org_data)

    async def get_organization(self, organization_id: str) -> Optional[OrganizationResponse]:
        """Get organization by ID"""
        self._log_call("get_organization", organization_id=organization_id)

        if self._error:
            raise self._error

        org_data = self._organizations.get(organization_id)
        if org_data:
            return OrganizationResponse(**org_data)
        return None

    async def update_organization(
        self,
        organization_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[OrganizationResponse]:
        """Update organization"""
        self._log_call("update_organization", organization_id=organization_id, update_data=update_data)

        if organization_id not in self._organizations:
            return None

        org_data = self._organizations[organization_id]
        for key, value in update_data.items():
            if key in org_data:
                org_data[key] = value
        org_data["updated_at"] = datetime.now(timezone.utc)

        return OrganizationResponse(**org_data)

    async def delete_organization(self, organization_id: str) -> bool:
        """Delete organization (soft delete)"""
        self._log_call("delete_organization", organization_id=organization_id)

        if organization_id not in self._organizations:
            return False

        self._organizations[organization_id]["status"] = "deleted"
        self._organizations[organization_id]["updated_at"] = datetime.now(timezone.utc)
        return True

    async def get_user_organizations(self, user_id: str) -> List[Dict]:
        """Get all organizations for a user"""
        self._log_call("get_user_organizations", user_id=user_id)

        results = []
        for org_id, members in self._members.items():
            for member in members:
                if member["user_id"] == user_id and member["status"] == "active":
                    org_data = self._organizations.get(org_id)
                    if org_data and org_data["status"] == "active":
                        results.append(org_data)
        return results

    async def add_organization_member(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole,
        permissions: Optional[List[str]] = None
    ) -> Optional[OrganizationMemberResponse]:
        """Add member to organization"""
        self._log_call(
            "add_organization_member",
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            permissions=permissions
        )

        if organization_id not in self._organizations:
            return None

        now = datetime.now(timezone.utc)
        role_value = role.value if hasattr(role, 'value') else role

        member_data = {
            "user_id": user_id,
            "organization_id": organization_id,
            "role": OrganizationRole(role_value),
            "status": MemberStatus.ACTIVE,
            "permissions": permissions or [],
            "joined_at": now
        }

        if organization_id not in self._members:
            self._members[organization_id] = []
        self._members[organization_id].append({
            **member_data,
            "role": role_value,
            "status": "active"
        })

        # Update member count
        self._organizations[organization_id]["member_count"] += 1

        return OrganizationMemberResponse(**member_data)

    async def update_organization_member(
        self,
        organization_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[OrganizationMemberResponse]:
        """Update organization member"""
        self._log_call(
            "update_organization_member",
            organization_id=organization_id,
            user_id=user_id,
            update_data=update_data
        )

        if organization_id not in self._members:
            return None

        for member in self._members[organization_id]:
            if member["user_id"] == user_id:
                for key, value in update_data.items():
                    if key in member:
                        member[key] = value if not hasattr(value, 'value') else value.value

                return OrganizationMemberResponse(
                    user_id=member["user_id"],
                    organization_id=organization_id,
                    role=OrganizationRole(member["role"]),
                    status=MemberStatus(member["status"]),
                    permissions=member.get("permissions", []),
                    joined_at=member["joined_at"]
                )

        return None

    async def remove_organization_member(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """Remove member from organization"""
        self._log_call(
            "remove_organization_member",
            organization_id=organization_id,
            user_id=user_id
        )

        if organization_id not in self._members:
            return False

        for i, member in enumerate(self._members[organization_id]):
            if member["user_id"] == user_id:
                del self._members[organization_id][i]
                # Update member count
                self._organizations[organization_id]["member_count"] -= 1
                return True

        return False

    async def get_organization_members(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0,
        role_filter: Optional[OrganizationRole] = None
    ) -> List[OrganizationMemberResponse]:
        """Get organization members"""
        self._log_call(
            "get_organization_members",
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            role_filter=role_filter
        )

        if organization_id not in self._members:
            return []

        results = []
        filter_role = role_filter.value if hasattr(role_filter, 'value') else role_filter

        for member in self._members[organization_id]:
            if filter_role and member["role"] != filter_role:
                continue
            results.append(OrganizationMemberResponse(
                user_id=member["user_id"],
                organization_id=organization_id,
                role=OrganizationRole(member["role"]),
                status=MemberStatus(member["status"]),
                permissions=member.get("permissions", []),
                joined_at=member["joined_at"]
            ))

        return results[offset:offset + limit]

    async def get_user_organization_role(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """Get user's role in organization"""
        self._log_call(
            "get_user_organization_role",
            organization_id=organization_id,
            user_id=user_id
        )

        if organization_id not in self._members:
            return None

        for member in self._members[organization_id]:
            if member["user_id"] == user_id:
                return {
                    "role": member["role"],
                    "status": member["status"],
                    "permissions": member.get("permissions", [])
                }

        return None

    async def get_organization_stats(self, organization_id: str) -> Dict[str, Any]:
        """Get organization statistics"""
        self._log_call("get_organization_stats", organization_id=organization_id)

        if organization_id not in self._organizations:
            return {}

        org = self._organizations[organization_id]
        members = self._members.get(organization_id, [])
        active_members = sum(1 for m in members if m["status"] == "active")

        return {
            "organization_id": organization_id,
            "name": org["name"],
            "plan": org["plan"],
            "status": org["status"],
            "member_count": len(members),
            "active_members": active_members,
            "credits_pool": org["credits_pool"],
            "credits_used_this_month": 0,
            "storage_used_gb": 0.0,
            "api_calls_this_month": 0,
            "created_at": org["created_at"]
        }

    async def list_all_organizations(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[OrganizationResponse]:
        """List all organizations with filters"""
        self._log_call(
            "list_all_organizations",
            limit=limit,
            offset=offset,
            search=search,
            plan_filter=plan_filter,
            status_filter=status_filter
        )

        results = []
        for org_data in self._organizations.values():
            # Apply filters
            if search and search.lower() not in org_data["name"].lower():
                continue
            if plan_filter and org_data["plan"] != plan_filter:
                continue
            if status_filter and org_data["status"] != status_filter:
                continue

            results.append(OrganizationResponse(**org_data))

        return results[offset:offset + limit]


class MockEventBus:
    """Mock NATS event bus"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})
        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = []
            for e in self.published_events:
                # Event class stores event type as self.type (string value)
                et = getattr(e, "type", None) or getattr(e, "event_type", e)
                # Handle enum types by getting their name or value
                if isinstance(et, str):
                    event_types.append(et)
                elif hasattr(et, 'name'):
                    event_types.append(et.name)
                elif hasattr(et, 'value'):
                    event_types.append(str(et.value))
                else:
                    event_types.append(str(et))
            # Check if event_type matches (case-insensitive, supports partial match)
            event_type_lower = event_type.lower().replace("_", ".")
            assert any(event_type_lower in et.lower() or event_type.upper() in et.upper()
                      for et in event_types), f"Expected {event_type} event, got {event_types}"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def clear(self):
        """Clear published events"""
        self.published_events = []
        self._call_log = []
