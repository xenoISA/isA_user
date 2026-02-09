"""
Unit Golden Tests: Authorization Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.authorization_service.models import (
    # Enums
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
    # Core Models
    ResourcePermission,
    UserPermissionRecord,
    OrganizationPermission,
    # Request/Response Models
    ResourceAccessRequest,
    ResourceAccessResponse,
    GrantPermissionRequest,
    RevokePermissionRequest,
    BulkPermissionRequest,
    # Summary/Analytics Models
    UserPermissionSummary,
    ResourceAccessSummary,
    OrganizationPermissionSummary,
    # Service Communication Models
    ExternalServiceUser,
    ExternalServiceOrganization,
    ServiceHealthCheck,
    # Database Operation Models
    PermissionAuditLog,
    PermissionCacheEntry,
    # Error Models
    AuthorizationError,
    ValidationError as AuthValidationError,
    # Batch Operation Models
    BatchOperationResult,
    BatchOperationSummary,
    # Base Models
    BaseResponse,
    HealthResponse,
    ServiceInfo,
    ServiceStats,
)


class TestEnumTypes:
    """Test enum type definitions"""

    def test_resource_type_values(self):
        """Test ResourceType enum values"""
        assert ResourceType.MCP_TOOL == "mcp_tool"
        assert ResourceType.PROMPT == "prompt"
        assert ResourceType.RESOURCE == "resource"
        assert ResourceType.API_ENDPOINT == "api_endpoint"
        assert ResourceType.DATABASE == "database"
        assert ResourceType.FILE_STORAGE == "file_storage"
        assert ResourceType.COMPUTE == "compute"
        assert ResourceType.AI_MODEL == "ai_model"

    def test_access_level_values(self):
        """Test AccessLevel enum values"""
        assert AccessLevel.NONE == "none"
        assert AccessLevel.READ_ONLY == "read_only"
        assert AccessLevel.READ_WRITE == "read_write"
        assert AccessLevel.ADMIN == "admin"
        assert AccessLevel.OWNER == "owner"

    def test_permission_source_values(self):
        """Test PermissionSource enum values"""
        assert PermissionSource.SUBSCRIPTION == "subscription"
        assert PermissionSource.ORGANIZATION == "organization"
        assert PermissionSource.ADMIN_GRANT == "admin_grant"
        assert PermissionSource.SYSTEM_DEFAULT == "system_default"

    def test_subscription_tier_values(self):
        """Test SubscriptionTier enum values"""
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.PRO == "pro"
        assert SubscriptionTier.ENTERPRISE == "enterprise"
        assert SubscriptionTier.CUSTOM == "custom"


class TestResourcePermissionModel:
    """Test ResourcePermission model validation"""

    def test_resource_permission_creation_with_all_fields(self):
        """Test creating resource permission with all fields"""
        now = datetime.now(timezone.utc)

        permission = ResourcePermission(
            id="perm_123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="code_editor",
            resource_category="development",
            description="Code editing tool access",
            subscription_tier_required=SubscriptionTier.PRO,
            access_level=AccessLevel.READ_WRITE,
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )

        assert permission.id == "perm_123"
        assert permission.resource_type == ResourceType.MCP_TOOL
        assert permission.resource_name == "code_editor"
        assert permission.resource_category == "development"
        assert permission.description == "Code editing tool access"
        assert permission.subscription_tier_required == SubscriptionTier.PRO
        assert permission.access_level == AccessLevel.READ_WRITE
        assert permission.is_enabled is True
        assert permission.created_at == now
        assert permission.updated_at == now

    def test_resource_permission_with_minimal_fields(self):
        """Test creating resource permission with only required fields"""
        permission = ResourcePermission(
            resource_type=ResourceType.PROMPT,
            resource_name="default_prompt",
        )

        assert permission.resource_type == ResourceType.PROMPT
        assert permission.resource_name == "default_prompt"
        assert permission.subscription_tier_required == SubscriptionTier.FREE
        assert permission.access_level == AccessLevel.READ_ONLY
        assert permission.is_enabled is True
        assert permission.id is None
        assert permission.resource_category is None
        assert permission.description is None

    def test_resource_permission_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ResourcePermission(resource_name="test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields


class TestUserPermissionRecordModel:
    """Test UserPermissionRecord model validation"""

    def test_user_permission_record_creation_with_all_fields(self):
        """Test creating user permission record with all fields"""
        # Use naive datetime since the validator uses datetime.utcnow() (naive)
        now = datetime.utcnow()
        future = now + timedelta(days=30)

        record = UserPermissionRecord(
            id="uprec_123",
            user_id="user_456",
            resource_type=ResourceType.AI_MODEL,
            resource_name="gpt4_access",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.SUBSCRIPTION,
            granted_by_user_id="admin_789",
            organization_id="org_001",
            expires_at=future,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert record.id == "uprec_123"
        assert record.user_id == "user_456"
        assert record.resource_type == ResourceType.AI_MODEL
        assert record.resource_name == "gpt4_access"
        assert record.access_level == AccessLevel.READ_WRITE
        assert record.permission_source == PermissionSource.SUBSCRIPTION
        assert record.granted_by_user_id == "admin_789"
        assert record.organization_id == "org_001"
        assert record.expires_at == future
        assert record.is_active is True

    def test_user_permission_record_with_minimal_fields(self):
        """Test creating user permission record with only required fields"""
        record = UserPermissionRecord(
            user_id="user_123",
            resource_type=ResourceType.DATABASE,
            resource_name="postgres_main",
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.SYSTEM_DEFAULT,
        )

        assert record.user_id == "user_123"
        assert record.resource_type == ResourceType.DATABASE
        assert record.resource_name == "postgres_main"
        assert record.access_level == AccessLevel.READ_ONLY
        assert record.permission_source == PermissionSource.SYSTEM_DEFAULT
        assert record.is_active is True
        assert record.granted_by_user_id is None
        assert record.organization_id is None
        assert record.expires_at is None

    def test_user_permission_record_expiry_validation_future_date(self):
        """Test that future expiry dates are accepted"""
        future = datetime.utcnow() + timedelta(days=10)

        record = UserPermissionRecord(
            user_id="user_123",
            resource_type=ResourceType.API_ENDPOINT,
            resource_name="analytics_api",
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.ORGANIZATION,
            expires_at=future,
        )

        assert record.expires_at == future

    def test_user_permission_record_expiry_validation_past_date(self):
        """Test that past expiry dates raise ValidationError"""
        past = datetime.utcnow() - timedelta(days=10)

        with pytest.raises(ValidationError) as exc_info:
            UserPermissionRecord(
                user_id="user_123",
                resource_type=ResourceType.API_ENDPOINT,
                resource_name="analytics_api",
                access_level=AccessLevel.READ_ONLY,
                permission_source=PermissionSource.ORGANIZATION,
                expires_at=past,
            )

        errors = exc_info.value.errors()
        assert any("expires_at" in str(err["loc"]) for err in errors)

    def test_user_permission_record_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            UserPermissionRecord(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields
        assert "access_level" in missing_fields
        assert "permission_source" in missing_fields


class TestOrganizationPermissionModel:
    """Test OrganizationPermission model validation"""

    def test_organization_permission_creation_with_all_fields(self):
        """Test creating organization permission with all fields"""
        now = datetime.now(timezone.utc)

        permission = OrganizationPermission(
            id="orgperm_123",
            organization_id="org_456",
            resource_type=ResourceType.COMPUTE,
            resource_name="gpu_cluster",
            access_level=AccessLevel.ADMIN,
            org_plan_required="enterprise",
            is_enabled=True,
            created_by_user_id="admin_789",
            created_at=now,
            updated_at=now,
        )

        assert permission.id == "orgperm_123"
        assert permission.organization_id == "org_456"
        assert permission.resource_type == ResourceType.COMPUTE
        assert permission.resource_name == "gpu_cluster"
        assert permission.access_level == AccessLevel.ADMIN
        assert permission.org_plan_required == "enterprise"
        assert permission.is_enabled is True
        assert permission.created_by_user_id == "admin_789"

    def test_organization_permission_with_minimal_fields(self):
        """Test creating organization permission with only required fields"""
        permission = OrganizationPermission(
            organization_id="org_123",
            resource_type=ResourceType.FILE_STORAGE,
            resource_name="shared_storage",
            access_level=AccessLevel.READ_WRITE,
        )

        assert permission.organization_id == "org_123"
        assert permission.resource_type == ResourceType.FILE_STORAGE
        assert permission.resource_name == "shared_storage"
        assert permission.access_level == AccessLevel.READ_WRITE
        assert permission.org_plan_required == "startup"
        assert permission.is_enabled is True
        assert permission.id is None
        assert permission.created_by_user_id is None

    def test_organization_permission_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationPermission(organization_id="org_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields
        assert "access_level" in missing_fields


class TestResourceAccessRequest:
    """Test ResourceAccessRequest model validation"""

    def test_resource_access_request_with_all_fields(self):
        """Test creating resource access request with all fields"""
        context = {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"}

        request = ResourceAccessRequest(
            user_id="user_123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="debugger",
            required_access_level=AccessLevel.READ_WRITE,
            organization_id="org_456",
            context=context,
        )

        assert request.user_id == "user_123"
        assert request.resource_type == ResourceType.MCP_TOOL
        assert request.resource_name == "debugger"
        assert request.required_access_level == AccessLevel.READ_WRITE
        assert request.organization_id == "org_456"
        assert request.context == context

    def test_resource_access_request_with_minimal_fields(self):
        """Test creating resource access request with only required fields"""
        request = ResourceAccessRequest(
            user_id="user_123",
            resource_type=ResourceType.PROMPT,
            resource_name="code_assistant",
        )

        assert request.user_id == "user_123"
        assert request.resource_type == ResourceType.PROMPT
        assert request.resource_name == "code_assistant"
        assert request.required_access_level == AccessLevel.READ_ONLY
        assert request.organization_id is None
        assert request.context is None

    def test_resource_access_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ResourceAccessRequest(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields


class TestResourceAccessResponse:
    """Test ResourceAccessResponse model validation"""

    def test_resource_access_response_granted(self):
        """Test creating resource access response for granted access"""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        metadata = {"trial_days_remaining": 15}

        response = ResourceAccessResponse(
            has_access=True,
            user_access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.SUBSCRIPTION,
            subscription_tier="pro",
            organization_plan=None,
            reason="User has active PRO subscription",
            expires_at=future,
            metadata=metadata,
        )

        assert response.has_access is True
        assert response.user_access_level == AccessLevel.READ_WRITE
        assert response.permission_source == PermissionSource.SUBSCRIPTION
        assert response.subscription_tier == "pro"
        assert response.reason == "User has active PRO subscription"
        assert response.expires_at == future
        assert response.metadata == metadata

    def test_resource_access_response_denied(self):
        """Test creating resource access response for denied access"""
        response = ResourceAccessResponse(
            has_access=False,
            user_access_level=AccessLevel.NONE,
            permission_source=PermissionSource.SYSTEM_DEFAULT,
            subscription_tier="free",
            organization_plan=None,
            reason="Resource requires PRO subscription",
        )

        assert response.has_access is False
        assert response.user_access_level == AccessLevel.NONE
        assert response.permission_source == PermissionSource.SYSTEM_DEFAULT
        assert response.subscription_tier == "free"
        assert response.reason == "Resource requires PRO subscription"
        assert response.expires_at is None
        assert response.metadata is None

    def test_resource_access_response_organization_based(self):
        """Test resource access response with organization access"""
        response = ResourceAccessResponse(
            has_access=True,
            user_access_level=AccessLevel.ADMIN,
            permission_source=PermissionSource.ORGANIZATION,
            subscription_tier="free",
            organization_plan="enterprise",
            reason="Access granted through enterprise organization",
        )

        assert response.has_access is True
        assert response.permission_source == PermissionSource.ORGANIZATION
        assert response.organization_plan == "enterprise"

    def test_resource_access_response_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ResourceAccessResponse(has_access=True)

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "user_access_level" in missing_fields
        assert "permission_source" in missing_fields
        assert "reason" in missing_fields


class TestGrantPermissionRequest:
    """Test GrantPermissionRequest model validation"""

    def test_grant_permission_request_with_all_fields(self):
        """Test creating grant permission request with all fields"""
        future = datetime.now(timezone.utc) + timedelta(days=90)

        request = GrantPermissionRequest(
            user_id="user_123",
            resource_type=ResourceType.AI_MODEL,
            resource_name="claude_opus",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin_456",
            organization_id="org_789",
            expires_at=future,
            reason="Beta testing program participant",
        )

        assert request.user_id == "user_123"
        assert request.resource_type == ResourceType.AI_MODEL
        assert request.resource_name == "claude_opus"
        assert request.access_level == AccessLevel.READ_WRITE
        assert request.permission_source == PermissionSource.ADMIN_GRANT
        assert request.granted_by_user_id == "admin_456"
        assert request.organization_id == "org_789"
        assert request.expires_at == future
        assert request.reason == "Beta testing program participant"

    def test_grant_permission_request_with_minimal_fields(self):
        """Test creating grant permission request with only required fields"""
        request = GrantPermissionRequest(
            user_id="user_123",
            resource_type=ResourceType.DATABASE,
            resource_name="analytics_db",
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.ORGANIZATION,
        )

        assert request.user_id == "user_123"
        assert request.resource_type == ResourceType.DATABASE
        assert request.resource_name == "analytics_db"
        assert request.access_level == AccessLevel.READ_ONLY
        assert request.permission_source == PermissionSource.ORGANIZATION
        assert request.granted_by_user_id is None
        assert request.organization_id is None
        assert request.expires_at is None
        assert request.reason is None

    def test_grant_permission_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            GrantPermissionRequest(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields
        assert "access_level" in missing_fields
        assert "permission_source" in missing_fields


class TestRevokePermissionRequest:
    """Test RevokePermissionRequest model validation"""

    def test_revoke_permission_request_with_all_fields(self):
        """Test creating revoke permission request with all fields"""
        request = RevokePermissionRequest(
            user_id="user_123",
            resource_type=ResourceType.COMPUTE,
            resource_name="gpu_instance",
            revoked_by_user_id="admin_456",
            reason="Subscription downgraded to free tier",
        )

        assert request.user_id == "user_123"
        assert request.resource_type == ResourceType.COMPUTE
        assert request.resource_name == "gpu_instance"
        assert request.revoked_by_user_id == "admin_456"
        assert request.reason == "Subscription downgraded to free tier"

    def test_revoke_permission_request_with_minimal_fields(self):
        """Test creating revoke permission request with only required fields"""
        request = RevokePermissionRequest(
            user_id="user_123",
            resource_type=ResourceType.API_ENDPOINT,
            resource_name="premium_api",
        )

        assert request.user_id == "user_123"
        assert request.resource_type == ResourceType.API_ENDPOINT
        assert request.resource_name == "premium_api"
        assert request.revoked_by_user_id is None
        assert request.reason is None

    def test_revoke_permission_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            RevokePermissionRequest(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields


class TestBulkPermissionRequest:
    """Test BulkPermissionRequest model validation"""

    def test_bulk_permission_request_with_grants(self):
        """Test creating bulk permission request with grant operations"""
        operations = [
            GrantPermissionRequest(
                user_id="user_1",
                resource_type=ResourceType.MCP_TOOL,
                resource_name="tool_a",
                access_level=AccessLevel.READ_WRITE,
                permission_source=PermissionSource.ORGANIZATION,
            ),
            GrantPermissionRequest(
                user_id="user_2",
                resource_type=ResourceType.MCP_TOOL,
                resource_name="tool_a",
                access_level=AccessLevel.READ_ONLY,
                permission_source=PermissionSource.ORGANIZATION,
            ),
        ]

        request = BulkPermissionRequest(
            operations=operations,
            executed_by_user_id="admin_123",
            batch_reason="Onboarding new team members",
        )

        assert len(request.operations) == 2
        assert request.executed_by_user_id == "admin_123"
        assert request.batch_reason == "Onboarding new team members"

    def test_bulk_permission_request_with_mixed_operations(self):
        """Test bulk permission request with mixed grant and revoke operations"""
        operations = [
            GrantPermissionRequest(
                user_id="user_1",
                resource_type=ResourceType.PROMPT,
                resource_name="advanced_prompt",
                access_level=AccessLevel.READ_WRITE,
                permission_source=PermissionSource.ADMIN_GRANT,
            ),
            RevokePermissionRequest(
                user_id="user_2",
                resource_type=ResourceType.PROMPT,
                resource_name="advanced_prompt",
            ),
        ]

        request = BulkPermissionRequest(
            operations=operations,
            executed_by_user_id="admin_456",
        )

        assert len(request.operations) == 2
        assert request.executed_by_user_id == "admin_456"
        assert request.batch_reason is None

    def test_bulk_permission_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            BulkPermissionRequest(executed_by_user_id="admin_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "operations" in missing_fields


class TestUserPermissionSummary:
    """Test UserPermissionSummary model validation"""

    def test_user_permission_summary_creation(self):
        """Test creating user permission summary"""
        now = datetime.now(timezone.utc)

        summary = UserPermissionSummary(
            user_id="user_123",
            subscription_tier="pro",
            organization_id="org_456",
            organization_plan="enterprise",
            total_permissions=15,
            permissions_by_type={
                ResourceType.MCP_TOOL: 5,
                ResourceType.AI_MODEL: 3,
                ResourceType.DATABASE: 7,
            },
            permissions_by_source={
                PermissionSource.SUBSCRIPTION: 8,
                PermissionSource.ORGANIZATION: 5,
                PermissionSource.ADMIN_GRANT: 2,
            },
            permissions_by_level={
                AccessLevel.READ_ONLY: 5,
                AccessLevel.READ_WRITE: 8,
                AccessLevel.ADMIN: 2,
            },
            expires_soon_count=3,
            last_access_check=now,
        )

        assert summary.user_id == "user_123"
        assert summary.subscription_tier == "pro"
        assert summary.organization_id == "org_456"
        assert summary.organization_plan == "enterprise"
        assert summary.total_permissions == 15
        assert summary.permissions_by_type[ResourceType.MCP_TOOL] == 5
        assert summary.permissions_by_source[PermissionSource.SUBSCRIPTION] == 8
        assert summary.permissions_by_level[AccessLevel.READ_WRITE] == 8
        assert summary.expires_soon_count == 3
        assert summary.last_access_check == now

    def test_user_permission_summary_without_organization(self):
        """Test user permission summary for individual user"""
        summary = UserPermissionSummary(
            user_id="user_123",
            subscription_tier="free",
            organization_id=None,
            organization_plan=None,
            total_permissions=3,
            permissions_by_type={ResourceType.MCP_TOOL: 3},
            permissions_by_source={PermissionSource.SYSTEM_DEFAULT: 3},
            permissions_by_level={AccessLevel.READ_ONLY: 3},
            expires_soon_count=0,
        )

        assert summary.user_id == "user_123"
        assert summary.subscription_tier == "free"
        assert summary.organization_id is None
        assert summary.organization_plan is None
        assert summary.total_permissions == 3

    def test_user_permission_summary_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            UserPermissionSummary(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "subscription_tier" in missing_fields
        assert "total_permissions" in missing_fields
        assert "permissions_by_type" in missing_fields
        assert "permissions_by_source" in missing_fields
        assert "permissions_by_level" in missing_fields
        assert "expires_soon_count" in missing_fields


class TestResourceAccessSummary:
    """Test ResourceAccessSummary model validation"""

    def test_resource_access_summary_creation(self):
        """Test creating resource access summary"""
        now = datetime.now(timezone.utc)

        summary = ResourceAccessSummary(
            resource_type=ResourceType.AI_MODEL,
            resource_name="gpt4_turbo",
            total_authorized_users=250,
            access_level_distribution={
                AccessLevel.READ_ONLY: 100,
                AccessLevel.READ_WRITE: 130,
                AccessLevel.ADMIN: 20,
            },
            permission_source_distribution={
                PermissionSource.SUBSCRIPTION: 180,
                PermissionSource.ORGANIZATION: 60,
                PermissionSource.ADMIN_GRANT: 10,
            },
            organization_access_count=8,
            expires_soon_count=12,
            last_accessed=now,
        )

        assert summary.resource_type == ResourceType.AI_MODEL
        assert summary.resource_name == "gpt4_turbo"
        assert summary.total_authorized_users == 250
        assert summary.access_level_distribution[AccessLevel.READ_WRITE] == 130
        assert summary.permission_source_distribution[PermissionSource.SUBSCRIPTION] == 180
        assert summary.organization_access_count == 8
        assert summary.expires_soon_count == 12
        assert summary.last_accessed == now

    def test_resource_access_summary_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ResourceAccessSummary(resource_type=ResourceType.DATABASE)

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_name" in missing_fields
        assert "total_authorized_users" in missing_fields


class TestOrganizationPermissionSummary:
    """Test OrganizationPermissionSummary model validation"""

    def test_organization_permission_summary_creation(self):
        """Test creating organization permission summary"""
        member_summary = [
            {"user_id": "user_1", "permission_count": 10, "highest_access": "admin"},
            {"user_id": "user_2", "permission_count": 5, "highest_access": "read_write"},
        ]

        summary = OrganizationPermissionSummary(
            organization_id="org_123",
            organization_plan="enterprise",
            total_members=25,
            total_permissions=150,
            permissions_by_type={
                ResourceType.MCP_TOOL: 50,
                ResourceType.AI_MODEL: 40,
                ResourceType.DATABASE: 30,
                ResourceType.COMPUTE: 30,
            },
            permissions_by_level={
                AccessLevel.READ_ONLY: 60,
                AccessLevel.READ_WRITE: 70,
                AccessLevel.ADMIN: 20,
            },
            member_access_summary=member_summary,
        )

        assert summary.organization_id == "org_123"
        assert summary.organization_plan == "enterprise"
        assert summary.total_members == 25
        assert summary.total_permissions == 150
        assert summary.permissions_by_type[ResourceType.MCP_TOOL] == 50
        assert summary.permissions_by_level[AccessLevel.READ_WRITE] == 70
        assert len(summary.member_access_summary) == 2

    def test_organization_permission_summary_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationPermissionSummary(organization_id="org_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "organization_plan" in missing_fields
        assert "total_members" in missing_fields
        assert "total_permissions" in missing_fields


class TestExternalServiceUser:
    """Test ExternalServiceUser model validation"""

    def test_external_service_user_creation_with_organization(self):
        """Test creating external service user with organization"""
        user = ExternalServiceUser(
            user_id="user_123",
            email="test@example.com",
            subscription_status="active",
            is_active=True,
            organization_id="org_456",
        )

        assert user.user_id == "user_123"
        assert user.email == "test@example.com"
        assert user.subscription_status == "active"
        assert user.is_active is True
        assert user.organization_id == "org_456"

    def test_external_service_user_without_organization(self):
        """Test creating external service user without organization"""
        user = ExternalServiceUser(
            user_id="user_123",
            email="individual@example.com",
            subscription_status="trial",
            is_active=True,
        )

        assert user.user_id == "user_123"
        assert user.email == "individual@example.com"
        assert user.subscription_status == "trial"
        assert user.is_active is True
        assert user.organization_id is None

    def test_external_service_user_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ExternalServiceUser(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "email" in missing_fields
        assert "subscription_status" in missing_fields
        assert "is_active" in missing_fields


class TestExternalServiceOrganization:
    """Test ExternalServiceOrganization model validation"""

    def test_external_service_organization_creation(self):
        """Test creating external service organization"""
        org = ExternalServiceOrganization(
            organization_id="org_123",
            plan="enterprise",
            is_active=True,
            member_count=50,
        )

        assert org.organization_id == "org_123"
        assert org.plan == "enterprise"
        assert org.is_active is True
        assert org.member_count == 50

    def test_external_service_organization_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ExternalServiceOrganization(organization_id="org_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "plan" in missing_fields
        assert "is_active" in missing_fields
        assert "member_count" in missing_fields


class TestServiceHealthCheck:
    """Test ServiceHealthCheck model validation"""

    def test_service_health_check_healthy(self):
        """Test creating service health check for healthy service"""
        check = ServiceHealthCheck(
            service_name="account_service",
            endpoint="http://localhost:8001/health",
            is_healthy=True,
            response_time_ms=45.2,
        )

        assert check.service_name == "account_service"
        assert check.endpoint == "http://localhost:8001/health"
        assert check.is_healthy is True
        assert check.response_time_ms == 45.2
        assert check.last_check is not None

    def test_service_health_check_unhealthy(self):
        """Test creating service health check for unhealthy service"""
        check = ServiceHealthCheck(
            service_name="billing_service",
            endpoint="http://localhost:8006/health",
            is_healthy=False,
        )

        assert check.service_name == "billing_service"
        assert check.is_healthy is False
        assert check.response_time_ms is None

    def test_service_health_check_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ServiceHealthCheck(service_name="test_service")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "endpoint" in missing_fields
        assert "is_healthy" in missing_fields


class TestPermissionAuditLog:
    """Test PermissionAuditLog model validation"""

    def test_permission_audit_log_grant(self):
        """Test creating audit log for permission grant"""
        log = PermissionAuditLog(
            id="audit_123",
            user_id="user_456",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="code_analyzer",
            action="grant",
            old_access_level=AccessLevel.NONE,
            new_access_level=AccessLevel.READ_WRITE,
            performed_by_user_id="admin_789",
            reason="Subscription upgraded to PRO",
            success=True,
        )

        assert log.id == "audit_123"
        assert log.user_id == "user_456"
        assert log.resource_type == ResourceType.MCP_TOOL
        assert log.resource_name == "code_analyzer"
        assert log.action == "grant"
        assert log.old_access_level == AccessLevel.NONE
        assert log.new_access_level == AccessLevel.READ_WRITE
        assert log.performed_by_user_id == "admin_789"
        assert log.reason == "Subscription upgraded to PRO"
        assert log.success is True
        assert log.error_message is None

    def test_permission_audit_log_revoke(self):
        """Test creating audit log for permission revoke"""
        log = PermissionAuditLog(
            user_id="user_123",
            resource_type=ResourceType.AI_MODEL,
            resource_name="claude_opus",
            action="revoke",
            old_access_level=AccessLevel.READ_WRITE,
            new_access_level=AccessLevel.NONE,
            performed_by_user_id="admin_456",
            reason="Subscription expired",
            success=True,
        )

        assert log.action == "revoke"
        assert log.old_access_level == AccessLevel.READ_WRITE
        assert log.new_access_level == AccessLevel.NONE
        assert log.success is True

    def test_permission_audit_log_check(self):
        """Test creating audit log for permission check"""
        log = PermissionAuditLog(
            user_id="user_123",
            resource_type=ResourceType.DATABASE,
            resource_name="analytics_db",
            action="check",
            success=True,
        )

        assert log.action == "check"
        assert log.old_access_level is None
        assert log.new_access_level is None
        assert log.success is True

    def test_permission_audit_log_failure(self):
        """Test creating audit log for failed operation"""
        log = PermissionAuditLog(
            user_id="user_123",
            resource_type=ResourceType.COMPUTE,
            resource_name="gpu_cluster",
            action="grant",
            performed_by_user_id="admin_789",
            success=False,
            error_message="Database connection timeout",
        )

        assert log.success is False
        assert log.error_message == "Database connection timeout"

    def test_permission_audit_log_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionAuditLog(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields
        assert "action" in missing_fields
        assert "success" in missing_fields


class TestPermissionCacheEntry:
    """Test PermissionCacheEntry model validation"""

    def test_permission_cache_entry_creation(self):
        """Test creating permission cache entry"""
        cache = PermissionCacheEntry(
            cache_key="user_123:mcp_tool:debugger",
            user_id="user_123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="debugger",
            has_access=True,
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.SUBSCRIPTION,
        )

        assert cache.cache_key == "user_123:mcp_tool:debugger"
        assert cache.user_id == "user_123"
        assert cache.resource_type == ResourceType.MCP_TOOL
        assert cache.resource_name == "debugger"
        assert cache.has_access is True
        assert cache.access_level == AccessLevel.READ_WRITE
        assert cache.permission_source == PermissionSource.SUBSCRIPTION
        assert cache.cached_at is not None
        assert cache.expires_at is not None

    def test_permission_cache_entry_is_expired_property(self):
        """Test cache entry expiry check"""
        past_expiry = datetime.utcnow() - timedelta(minutes=5)

        cache = PermissionCacheEntry(
            cache_key="test_key",
            user_id="user_123",
            resource_type=ResourceType.PROMPT,
            resource_name="test_prompt",
            has_access=True,
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.SYSTEM_DEFAULT,
        )
        cache.expires_at = past_expiry

        assert cache.is_expired is True

    def test_permission_cache_entry_is_not_expired(self):
        """Test cache entry not expired"""
        future_expiry = datetime.utcnow() + timedelta(minutes=10)

        cache = PermissionCacheEntry(
            cache_key="test_key",
            user_id="user_123",
            resource_type=ResourceType.PROMPT,
            resource_name="test_prompt",
            has_access=True,
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.SYSTEM_DEFAULT,
        )
        cache.expires_at = future_expiry

        assert cache.is_expired is False

    def test_permission_cache_entry_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionCacheEntry(cache_key="test_key")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "user_id" in missing_fields
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields
        assert "has_access" in missing_fields
        assert "access_level" in missing_fields
        assert "permission_source" in missing_fields


class TestAuthorizationError:
    """Test AuthorizationError model validation"""

    def test_authorization_error_creation_with_all_fields(self):
        """Test creating authorization error with all fields"""
        error = AuthorizationError(
            error_code="AUTH_INSUFFICIENT_PERMISSIONS",
            error_message="User does not have required access level",
            user_id="user_123",
            resource_type=ResourceType.COMPUTE,
            resource_name="gpu_cluster",
            suggested_action="Upgrade to Enterprise plan",
        )

        assert error.error_code == "AUTH_INSUFFICIENT_PERMISSIONS"
        assert error.error_message == "User does not have required access level"
        assert error.user_id == "user_123"
        assert error.resource_type == ResourceType.COMPUTE
        assert error.resource_name == "gpu_cluster"
        assert error.suggested_action == "Upgrade to Enterprise plan"
        assert error.timestamp is not None

    def test_authorization_error_with_minimal_fields(self):
        """Test creating authorization error with only required fields"""
        error = AuthorizationError(
            error_code="AUTH_SERVICE_UNAVAILABLE",
            error_message="Unable to connect to authorization service",
        )

        assert error.error_code == "AUTH_SERVICE_UNAVAILABLE"
        assert error.error_message == "Unable to connect to authorization service"
        assert error.user_id is None
        assert error.resource_type is None
        assert error.resource_name is None
        assert error.suggested_action is None

    def test_authorization_error_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AuthorizationError(error_code="AUTH_ERROR")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "error_message" in missing_fields


class TestAuthValidationError:
    """Test ValidationError model"""

    def test_validation_error_creation_with_all_fields(self):
        """Test creating validation error with all fields"""
        error = AuthValidationError(
            field="expires_at",
            error="Date must be in the future",
            provided_value="2020-01-01T00:00:00Z",
            expected_format="ISO 8601 datetime string (future date)",
        )

        assert error.field == "expires_at"
        assert error.error == "Date must be in the future"
        assert error.provided_value == "2020-01-01T00:00:00Z"
        assert error.expected_format == "ISO 8601 datetime string (future date)"

    def test_validation_error_without_expected_format(self):
        """Test creating validation error without expected format"""
        error = AuthValidationError(
            field="user_id",
            error="Field cannot be empty",
            provided_value="",
        )

        assert error.field == "user_id"
        assert error.error == "Field cannot be empty"
        assert error.provided_value == ""
        assert error.expected_format is None

    def test_validation_error_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AuthValidationError(field="test_field")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "error" in missing_fields
        assert "provided_value" in missing_fields


class TestBatchOperationResult:
    """Test BatchOperationResult model validation"""

    def test_batch_operation_result_success(self):
        """Test creating successful batch operation result"""
        result = BatchOperationResult(
            operation_id="op_123",
            operation_type="grant",
            target_user_id="user_456",
            resource_type=ResourceType.AI_MODEL,
            resource_name="gpt4_turbo",
            success=True,
        )

        assert result.operation_id == "op_123"
        assert result.operation_type == "grant"
        assert result.target_user_id == "user_456"
        assert result.resource_type == ResourceType.AI_MODEL
        assert result.resource_name == "gpt4_turbo"
        assert result.success is True
        assert result.error_message is None
        assert result.processed_at is not None

    def test_batch_operation_result_failure(self):
        """Test creating failed batch operation result"""
        result = BatchOperationResult(
            operation_id="op_456",
            operation_type="revoke",
            target_user_id="user_789",
            resource_type=ResourceType.DATABASE,
            resource_name="prod_db",
            success=False,
            error_message="Permission record not found",
        )

        assert result.success is False
        assert result.error_message == "Permission record not found"

    def test_batch_operation_result_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            BatchOperationResult(operation_id="op_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "operation_type" in missing_fields
        assert "target_user_id" in missing_fields
        assert "resource_type" in missing_fields
        assert "resource_name" in missing_fields
        assert "success" in missing_fields


class TestBatchOperationSummary:
    """Test BatchOperationSummary model validation"""

    def test_batch_operation_summary_creation(self):
        """Test creating batch operation summary"""
        started = datetime.now(timezone.utc)
        completed = started + timedelta(seconds=5)

        results = [
            BatchOperationResult(
                operation_id="op_1",
                operation_type="grant",
                target_user_id="user_1",
                resource_type=ResourceType.MCP_TOOL,
                resource_name="tool_a",
                success=True,
            ),
            BatchOperationResult(
                operation_id="op_2",
                operation_type="grant",
                target_user_id="user_2",
                resource_type=ResourceType.MCP_TOOL,
                resource_name="tool_a",
                success=False,
                error_message="User not found",
            ),
        ]

        summary = BatchOperationSummary(
            batch_id="batch_123",
            total_operations=2,
            successful_operations=1,
            failed_operations=1,
            execution_time_seconds=5.23,
            executed_by_user_id="admin_456",
            results=results,
            started_at=started,
            completed_at=completed,
        )

        assert summary.batch_id == "batch_123"
        assert summary.total_operations == 2
        assert summary.successful_operations == 1
        assert summary.failed_operations == 1
        assert summary.execution_time_seconds == 5.23
        assert summary.executed_by_user_id == "admin_456"
        assert len(summary.results) == 2
        assert summary.started_at == started
        assert summary.completed_at == completed

    def test_batch_operation_summary_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            BatchOperationSummary(batch_id="batch_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "total_operations" in missing_fields
        assert "successful_operations" in missing_fields
        assert "failed_operations" in missing_fields
        assert "execution_time_seconds" in missing_fields
        assert "results" in missing_fields
        assert "started_at" in missing_fields


class TestBaseResponse:
    """Test BaseResponse model validation"""

    def test_base_response_defaults(self):
        """Test base response with default values"""
        response = BaseResponse()

        assert response.success is True
        assert response.timestamp is not None

    def test_base_response_custom_values(self):
        """Test base response with custom values"""
        now = datetime.now(timezone.utc)

        response = BaseResponse(
            success=False,
            timestamp=now,
        )

        assert response.success is False
        assert response.timestamp == now


class TestHealthResponse:
    """Test HealthResponse model validation"""

    def test_health_response_creation(self):
        """Test creating health response"""
        response = HealthResponse(
            status="healthy",
            service="authorization_service",
            port=8003,
            version="1.0.0",
        )

        assert response.status == "healthy"
        assert response.service == "authorization_service"
        assert response.port == 8003
        assert response.version == "1.0.0"

    def test_health_response_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            HealthResponse(status="healthy")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "service" in missing_fields
        assert "port" in missing_fields
        assert "version" in missing_fields


class TestServiceInfo:
    """Test ServiceInfo model validation"""

    def test_service_info_creation(self):
        """Test creating service info"""
        capabilities = {
            "check_access": True,
            "grant_permission": True,
            "revoke_permission": True,
            "batch_operations": True,
        }

        endpoints = {
            "health": "/health",
            "check_access": "/check-access",
            "grant": "/grant",
            "revoke": "/revoke",
        }

        info = ServiceInfo(
            service="authorization_service",
            version="1.0.0",
            description="Handles resource authorization and permission management",
            capabilities=capabilities,
            endpoints=endpoints,
        )

        assert info.service == "authorization_service"
        assert info.version == "1.0.0"
        assert info.description == "Handles resource authorization and permission management"
        assert info.capabilities["check_access"] is True
        assert info.endpoints["grant"] == "/grant"

    def test_service_info_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ServiceInfo(service="test_service")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "version" in missing_fields
        assert "description" in missing_fields
        assert "capabilities" in missing_fields
        assert "endpoints" in missing_fields


class TestServiceStats:
    """Test ServiceStats model validation"""

    def test_service_stats_creation(self):
        """Test creating service stats"""
        statistics = {
            "total_checks": 15000,
            "total_grants": 500,
            "total_revokes": 50,
            "cache_hit_rate": 0.85,
            "avg_response_time_ms": 12.5,
        }

        stats = ServiceStats(
            service="authorization_service",
            version="1.0.0",
            status="healthy",
            uptime="72h 15m 30s",
            endpoints_count=8,
            statistics=statistics,
        )

        assert stats.service == "authorization_service"
        assert stats.version == "1.0.0"
        assert stats.status == "healthy"
        assert stats.uptime == "72h 15m 30s"
        assert stats.endpoints_count == 8
        assert stats.statistics["total_checks"] == 15000
        assert stats.statistics["cache_hit_rate"] == 0.85

    def test_service_stats_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ServiceStats(service="test_service")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "version" in missing_fields
        assert "status" in missing_fields
        assert "uptime" in missing_fields
        assert "endpoints_count" in missing_fields
        assert "statistics" in missing_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
