"""
Authorization Service - Unit Tests for TestDataFactory (Golden)

Tests for:
- AuthorizationTestDataFactory methods
- Request builders
- Contract validation with factory-generated data

All tests use AuthorizationTestDataFactory - zero hardcoded data.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from tests.contracts.authorization.data_contract import (
    # Enums
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
    OrganizationPlan,
    # Contracts
    ResourceAccessRequestContract,
    GrantPermissionRequestContract,
    RevokePermissionRequestContract,
    BulkPermissionRequestContract,
    ResourcePermissionConfigContract,
    OrganizationPermissionConfigContract,
    # Factory
    AuthorizationTestDataFactory,
    # Builders
    AccessCheckRequestBuilder,
    GrantPermissionRequestBuilder,
    RevokePermissionRequestBuilder,
    BulkPermissionRequestBuilder,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# Test AuthorizationTestDataFactory ID Generators
# ============================================================================


class TestFactoryIdGenerators:
    """Test factory ID generation"""

    def test_user_id_format(self):
        """User ID has correct format"""
        user_id = AuthorizationTestDataFactory.make_user_id()
        assert user_id.startswith("user_")
        assert len(user_id) > 10

    def test_user_id_uniqueness(self):
        """User IDs are unique"""
        ids = {AuthorizationTestDataFactory.make_user_id() for _ in range(100)}
        assert len(ids) == 100

    def test_admin_id_format(self):
        """Admin ID has correct format"""
        admin_id = AuthorizationTestDataFactory.make_admin_id()
        assert admin_id.startswith("admin_")

    def test_admin_id_uniqueness(self):
        """Admin IDs are unique"""
        ids = {AuthorizationTestDataFactory.make_admin_id() for _ in range(100)}
        assert len(ids) == 100

    def test_organization_id_format(self):
        """Organization ID has correct format"""
        org_id = AuthorizationTestDataFactory.make_organization_id()
        assert org_id.startswith("org_")

    def test_organization_id_uniqueness(self):
        """Organization IDs are unique"""
        ids = {AuthorizationTestDataFactory.make_organization_id() for _ in range(100)}
        assert len(ids) == 100

    def test_permission_id_format(self):
        """Permission ID has correct format"""
        perm_id = AuthorizationTestDataFactory.make_permission_id()
        assert perm_id.startswith("perm_")

    def test_operation_id_is_uuid(self):
        """Operation ID is valid UUID format"""
        op_id = AuthorizationTestDataFactory.make_operation_id()
        assert len(op_id) == 36  # UUID with hyphens
        assert "-" in op_id

    def test_batch_id_format(self):
        """Batch ID has correct format"""
        batch_id = AuthorizationTestDataFactory.make_batch_id()
        assert batch_id.startswith("batch_")

    def test_correlation_id_format(self):
        """Correlation ID has correct format"""
        corr_id = AuthorizationTestDataFactory.make_correlation_id()
        assert corr_id.startswith("corr_")


# ============================================================================
# Test AuthorizationTestDataFactory String Generators
# ============================================================================


class TestFactoryStringGenerators:
    """Test factory string generation"""

    def test_resource_name_valid_format(self):
        """Resource name has valid format"""
        name = AuthorizationTestDataFactory.make_resource_name()
        assert name.startswith("/api")
        assert 1 <= len(name) <= 255

    def test_resource_name_uniqueness(self):
        """Resource names are unique"""
        names = {AuthorizationTestDataFactory.make_resource_name() for _ in range(50)}
        assert len(names) == 50

    def test_api_endpoint_name_format(self):
        """API endpoint name has correct format"""
        endpoint = AuthorizationTestDataFactory.make_api_endpoint_name()
        assert endpoint.startswith("/api/v1/")
        assert len(endpoint) > 10

    def test_mcp_tool_name_format(self):
        """MCP tool name has correct format"""
        tool = AuthorizationTestDataFactory.make_mcp_tool_name()
        assert "_" in tool  # Contains underscore
        assert len(tool) > 5

    def test_ai_model_name_format(self):
        """AI model name has correct format"""
        model = AuthorizationTestDataFactory.make_ai_model_name()
        assert "_" in model  # Contains underscore
        assert len(model) > 5

    def test_database_name_format(self):
        """Database name has correct format"""
        db = AuthorizationTestDataFactory.make_database_name()
        assert "_db_" in db or db.endswith("_db")

    def test_resource_category_valid(self):
        """Resource category is valid value"""
        categories = {"utilities", "ai_tools", "data", "admin", "reporting", "storage"}
        for _ in range(50):
            cat = AuthorizationTestDataFactory.make_resource_category()
            assert cat in categories

    def test_reason_not_empty(self):
        """Reason is not empty"""
        reason = AuthorizationTestDataFactory.make_reason()
        assert len(reason) > 0

    def test_description_not_empty(self):
        """Description is not empty"""
        desc = AuthorizationTestDataFactory.make_description()
        assert len(desc) > 0

    def test_email_valid_format(self):
        """Email has valid format"""
        email = AuthorizationTestDataFactory.make_email()
        assert "@" in email
        assert email.endswith("@example.com")


# ============================================================================
# Test AuthorizationTestDataFactory Enum Generators
# ============================================================================


class TestFactoryEnumGenerators:
    """Test factory enum generation"""

    def test_resource_type_valid(self):
        """Resource type is valid enum"""
        for _ in range(50):
            rt = AuthorizationTestDataFactory.make_resource_type()
            assert rt in ResourceType

    def test_access_level_valid(self):
        """Access level is valid enum"""
        for _ in range(50):
            al = AuthorizationTestDataFactory.make_access_level()
            assert al in AccessLevel

    def test_permission_source_valid(self):
        """Permission source is valid enum"""
        for _ in range(50):
            ps = AuthorizationTestDataFactory.make_permission_source()
            assert ps in PermissionSource

    def test_subscription_tier_valid(self):
        """Subscription tier is valid enum"""
        for _ in range(50):
            st = AuthorizationTestDataFactory.make_subscription_tier()
            assert st in SubscriptionTier

    def test_organization_plan_valid(self):
        """Organization plan is valid enum"""
        for _ in range(50):
            op = AuthorizationTestDataFactory.make_organization_plan()
            assert op in OrganizationPlan


# ============================================================================
# Test AuthorizationTestDataFactory Timestamp Generators
# ============================================================================


class TestFactoryTimestampGenerators:
    """Test factory timestamp generation"""

    def test_timestamp_is_utc(self):
        """Timestamp is in UTC"""
        ts = AuthorizationTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_future_timestamp_is_future(self):
        """Future timestamp is after now"""
        now = datetime.now(timezone.utc)
        future = AuthorizationTestDataFactory.make_future_timestamp(days=1)
        assert future > now

    def test_past_timestamp_is_past(self):
        """Past timestamp is before now"""
        now = datetime.now(timezone.utc)
        past = AuthorizationTestDataFactory.make_past_timestamp(days=1)
        assert past < now

    def test_expires_soon_within_7_days(self):
        """Expires soon timestamp is within 7 days"""
        now = datetime.now(timezone.utc)
        expires = AuthorizationTestDataFactory.make_expires_soon_timestamp()
        assert now < expires <= now + timedelta(days=7)

    def test_timestamp_iso_format(self):
        """ISO timestamp has valid format"""
        iso = AuthorizationTestDataFactory.make_timestamp_iso()
        assert "T" in iso  # ISO format separator
        # Should be parseable
        datetime.fromisoformat(iso.replace("Z", "+00:00"))


# ============================================================================
# Test AuthorizationTestDataFactory Numeric Generators
# ============================================================================


class TestFactoryNumericGenerators:
    """Test factory numeric generation"""

    def test_positive_int_positive(self):
        """Positive int is positive"""
        for _ in range(50):
            val = AuthorizationTestDataFactory.make_positive_int()
            assert val >= 1

    def test_permission_count_reasonable(self):
        """Permission count is in reasonable range"""
        for _ in range(50):
            count = AuthorizationTestDataFactory.make_permission_count()
            assert 5 <= count <= 50

    def test_port_is_authorization_port(self):
        """Port is authorization service port"""
        port = AuthorizationTestDataFactory.make_port()
        assert port == 8203


# ============================================================================
# Test AuthorizationTestDataFactory Request Generators
# ============================================================================


class TestFactoryRequestGenerators:
    """Test factory request generation"""

    def test_access_check_request_valid(self):
        """Access check request is valid"""
        request = AuthorizationTestDataFactory.make_access_check_request()
        assert isinstance(request, ResourceAccessRequestContract)
        assert len(request.user_id) > 0
        assert request.resource_type in ResourceType

    def test_access_check_request_with_overrides(self):
        """Access check request applies overrides"""
        custom_user = AuthorizationTestDataFactory.make_user_id()
        request = AuthorizationTestDataFactory.make_access_check_request(
            user_id=custom_user,
            required_access_level=AccessLevel.ADMIN
        )
        assert request.user_id == custom_user
        assert request.required_access_level == AccessLevel.ADMIN

    def test_grant_request_valid(self):
        """Grant request is valid"""
        request = AuthorizationTestDataFactory.make_grant_request()
        assert isinstance(request, GrantPermissionRequestContract)
        assert len(request.user_id) > 0
        assert request.permission_source in PermissionSource

    def test_grant_request_with_overrides(self):
        """Grant request applies overrides"""
        request = AuthorizationTestDataFactory.make_grant_request(
            access_level=AccessLevel.OWNER,
            permission_source=PermissionSource.ORGANIZATION
        )
        assert request.access_level == AccessLevel.OWNER
        assert request.permission_source == PermissionSource.ORGANIZATION

    def test_revoke_request_valid(self):
        """Revoke request is valid"""
        request = AuthorizationTestDataFactory.make_revoke_request()
        assert isinstance(request, RevokePermissionRequestContract)
        assert len(request.user_id) > 0

    def test_revoke_request_with_overrides(self):
        """Revoke request applies overrides"""
        custom_reason = "Policy change"
        request = AuthorizationTestDataFactory.make_revoke_request(reason=custom_reason)
        assert request.reason == custom_reason

    def test_bulk_grant_request_valid(self):
        """Bulk grant request is valid"""
        request = AuthorizationTestDataFactory.make_bulk_grant_request(count=5)
        assert isinstance(request, BulkPermissionRequestContract)
        assert len(request.operations) == 5

    def test_bulk_revoke_request_valid(self):
        """Bulk revoke request is valid"""
        request = AuthorizationTestDataFactory.make_bulk_revoke_request(count=3)
        assert isinstance(request, BulkPermissionRequestContract)
        assert len(request.operations) == 3

    def test_resource_config_request_valid(self):
        """Resource config request is valid"""
        config = AuthorizationTestDataFactory.make_resource_config_request()
        assert isinstance(config, ResourcePermissionConfigContract)
        assert len(config.resource_name) > 0

    def test_org_permission_config_request_valid(self):
        """Organization permission config request is valid"""
        config = AuthorizationTestDataFactory.make_org_permission_config_request()
        assert isinstance(config, OrganizationPermissionConfigContract)
        assert config.organization_id.startswith("org_")


# ============================================================================
# Test AuthorizationTestDataFactory Response Generators
# ============================================================================


class TestFactoryResponseGenerators:
    """Test factory response generation"""

    def test_access_granted_response_structure(self):
        """Access granted response has correct structure"""
        response = AuthorizationTestDataFactory.make_access_granted_response()
        assert response["has_access"] is True
        assert "user_access_level" in response
        assert "permission_source" in response
        assert "reason" in response

    def test_access_denied_response_structure(self):
        """Access denied response has correct structure"""
        response = AuthorizationTestDataFactory.make_access_denied_response()
        assert response["has_access"] is False
        assert response["user_access_level"] == "none"
        assert "reason" in response

    def test_permission_summary_response_structure(self):
        """Permission summary response has correct structure"""
        response = AuthorizationTestDataFactory.make_permission_summary_response()
        assert "user_id" in response
        assert "subscription_tier" in response
        assert "total_permissions" in response
        assert "permissions_by_type" in response
        assert "permissions_by_source" in response
        assert "permissions_by_level" in response

    def test_accessible_resource_structure(self):
        """Accessible resource has correct structure"""
        resource = AuthorizationTestDataFactory.make_accessible_resource()
        assert "resource_type" in resource
        assert "resource_name" in resource
        assert "access_level" in resource
        assert "permission_source" in resource

    def test_accessible_resources_response_count(self):
        """Accessible resources response has correct count"""
        response = AuthorizationTestDataFactory.make_accessible_resources_response(count=7)
        assert len(response["accessible_resources"]) == 7
        assert response["total_count"] == 7

    def test_batch_result_structure(self):
        """Batch result has correct structure"""
        result = AuthorizationTestDataFactory.make_batch_result()
        assert "operation_id" in result
        assert "operation_type" in result
        assert "target_user_id" in result
        assert "success" in result
        assert "processed_at" in result

    def test_bulk_response_structure(self):
        """Bulk response has correct structure"""
        response = AuthorizationTestDataFactory.make_bulk_response(total=10)
        assert response["total_operations"] == 10
        assert response["successful"] + response["failed"] == 10
        assert len(response["results"]) == 10

    def test_health_response_structure(self):
        """Health response has correct structure"""
        response = AuthorizationTestDataFactory.make_health_response()
        assert response["status"] == "healthy"
        assert response["service"] == "authorization_service"
        assert response["port"] == 8203

    def test_error_response_structure(self):
        """Error response has correct structure"""
        response = AuthorizationTestDataFactory.make_error_response()
        assert "detail" in response
        assert "timestamp" in response


# ============================================================================
# Test AuthorizationTestDataFactory Invalid Data Generators
# ============================================================================


class TestFactoryInvalidDataGenerators:
    """Test factory invalid data generation"""

    def test_invalid_user_id_empty(self):
        """Invalid user ID is empty"""
        assert AuthorizationTestDataFactory.make_invalid_user_id_empty() == ""

    def test_invalid_user_id_whitespace(self):
        """Invalid user ID is whitespace only"""
        invalid = AuthorizationTestDataFactory.make_invalid_user_id_whitespace()
        assert invalid.strip() == ""

    def test_invalid_user_id_too_long(self):
        """Invalid user ID exceeds max length"""
        invalid = AuthorizationTestDataFactory.make_invalid_user_id_too_long()
        assert len(invalid) > 100

    def test_invalid_resource_name_empty(self):
        """Invalid resource name is empty"""
        assert AuthorizationTestDataFactory.make_invalid_resource_name_empty() == ""

    def test_invalid_resource_name_whitespace(self):
        """Invalid resource name is whitespace only"""
        invalid = AuthorizationTestDataFactory.make_invalid_resource_name_whitespace()
        assert invalid.strip() == ""

    def test_invalid_resource_name_too_long(self):
        """Invalid resource name exceeds max length"""
        invalid = AuthorizationTestDataFactory.make_invalid_resource_name_too_long()
        assert len(invalid) > 255

    def test_invalid_resource_type(self):
        """Invalid resource type is not in enum"""
        invalid = AuthorizationTestDataFactory.make_invalid_resource_type()
        assert invalid not in [e.value for e in ResourceType]

    def test_invalid_access_level(self):
        """Invalid access level is not in enum"""
        invalid = AuthorizationTestDataFactory.make_invalid_access_level()
        assert invalid not in [e.value for e in AccessLevel]

    def test_invalid_permission_source(self):
        """Invalid permission source is not in enum"""
        invalid = AuthorizationTestDataFactory.make_invalid_permission_source()
        assert invalid not in [e.value for e in PermissionSource]

    def test_invalid_expires_at_past(self):
        """Invalid expiry is in the past"""
        now = datetime.now(timezone.utc)
        invalid = AuthorizationTestDataFactory.make_invalid_expires_at_past()
        assert invalid < now

    def test_invalid_bulk_operations_empty(self):
        """Invalid bulk operations is empty"""
        assert AuthorizationTestDataFactory.make_invalid_bulk_operations_empty() == []

    def test_invalid_bulk_operations_too_many(self):
        """Invalid bulk operations exceeds max"""
        invalid = AuthorizationTestDataFactory.make_invalid_bulk_operations_too_many()
        assert len(invalid) > 100

    def test_invalid_reason_too_long(self):
        """Invalid reason exceeds max length"""
        invalid = AuthorizationTestDataFactory.make_invalid_reason_too_long()
        assert len(invalid) > 500


# ============================================================================
# Test AuthorizationTestDataFactory Edge Case Generators
# ============================================================================


class TestFactoryEdgeCaseGenerators:
    """Test factory edge case generation"""

    def test_unicode_resource_name(self):
        """Unicode resource name is valid"""
        name = AuthorizationTestDataFactory.make_unicode_resource_name()
        assert len(name) > 0
        # Contains unicode characters
        assert any(ord(c) > 127 for c in name)

    def test_special_chars_resource_name(self):
        """Special chars resource name is valid"""
        name = AuthorizationTestDataFactory.make_special_chars_resource_name()
        assert "-" in name or "_" in name

    def test_max_length_resource_name(self):
        """Max length resource name is exactly 255 chars"""
        name = AuthorizationTestDataFactory.make_max_length_resource_name()
        assert len(name) == 255

    def test_min_length_resource_name(self):
        """Min length resource name is exactly 1 char"""
        name = AuthorizationTestDataFactory.make_min_length_resource_name()
        assert len(name) == 1

    def test_max_length_user_id(self):
        """Max length user ID is exactly 100 chars"""
        user_id = AuthorizationTestDataFactory.make_max_length_user_id()
        assert len(user_id) == 100

    def test_min_length_user_id(self):
        """Min length user ID is exactly 1 char"""
        user_id = AuthorizationTestDataFactory.make_min_length_user_id()
        assert len(user_id) == 1

    def test_nonexistent_user_id(self):
        """Nonexistent user ID has distinct prefix"""
        user_id = AuthorizationTestDataFactory.make_nonexistent_user_id()
        assert user_id.startswith("nonexistent_")

    def test_nonexistent_organization_id(self):
        """Nonexistent organization ID has distinct prefix"""
        org_id = AuthorizationTestDataFactory.make_nonexistent_organization_id()
        assert org_id.startswith("nonexistent_org_")


# ============================================================================
# Test AuthorizationTestDataFactory Batch Generators
# ============================================================================


class TestFactoryBatchGenerators:
    """Test factory batch generation"""

    def test_batch_user_ids_count(self):
        """Batch user IDs has correct count"""
        for count in [1, 5, 10, 20]:
            ids = AuthorizationTestDataFactory.make_batch_user_ids(count)
            assert len(ids) == count
            assert all(id.startswith("user_") for id in ids)

    def test_batch_grant_requests_count(self):
        """Batch grant requests has correct count"""
        requests = AuthorizationTestDataFactory.make_batch_grant_requests(7)
        assert len(requests) == 7
        assert all(isinstance(r, GrantPermissionRequestContract) for r in requests)

    def test_batch_revoke_requests_count(self):
        """Batch revoke requests has correct count"""
        requests = AuthorizationTestDataFactory.make_batch_revoke_requests(4)
        assert len(requests) == 4
        assert all(isinstance(r, RevokePermissionRequestContract) for r in requests)

    def test_batch_resource_configs_count(self):
        """Batch resource configs has correct count"""
        configs = AuthorizationTestDataFactory.make_batch_resource_configs(6)
        assert len(configs) == 6
        assert all(isinstance(c, ResourcePermissionConfigContract) for c in configs)


# ============================================================================
# Test AuthorizationTestDataFactory Event Data Generators
# ============================================================================


class TestFactoryEventDataGenerators:
    """Test factory event data generation"""

    def test_permission_granted_event_data(self):
        """Permission granted event data has required fields"""
        data = AuthorizationTestDataFactory.make_permission_granted_event_data()
        assert "user_id" in data
        assert "resource_type" in data
        assert "resource_name" in data
        assert "access_level" in data
        assert "permission_source" in data
        assert "timestamp" in data

    def test_permission_revoked_event_data(self):
        """Permission revoked event data has required fields"""
        data = AuthorizationTestDataFactory.make_permission_revoked_event_data()
        assert "user_id" in data
        assert "resource_type" in data
        assert "resource_name" in data
        assert "previous_access_level" in data
        assert "timestamp" in data

    def test_access_denied_event_data(self):
        """Access denied event data has required fields"""
        data = AuthorizationTestDataFactory.make_access_denied_event_data()
        assert "user_id" in data
        assert "resource_type" in data
        assert "resource_name" in data
        assert "required_access_level" in data
        assert "reason" in data

    def test_user_deleted_event_data(self):
        """User deleted event data has required fields"""
        data = AuthorizationTestDataFactory.make_user_deleted_event_data()
        assert "user_id" in data
        assert "timestamp" in data

    def test_org_member_added_event_data(self):
        """Org member added event data has required fields"""
        data = AuthorizationTestDataFactory.make_org_member_added_event_data()
        assert "organization_id" in data
        assert "user_id" in data
        assert "role" in data
        assert "timestamp" in data

    def test_org_member_removed_event_data(self):
        """Org member removed event data has required fields"""
        data = AuthorizationTestDataFactory.make_org_member_removed_event_data()
        assert "organization_id" in data
        assert "user_id" in data
        assert "timestamp" in data


# ============================================================================
# Test Request Builders
# ============================================================================


class TestRequestBuilders:
    """Test request builder classes"""

    def test_access_check_builder_default(self):
        """Access check builder has defaults"""
        request = AccessCheckRequestBuilder().build()
        assert isinstance(request, ResourceAccessRequestContract)
        assert request.required_access_level == AccessLevel.READ_ONLY

    def test_access_check_builder_chaining(self):
        """Access check builder supports chaining"""
        request = (
            AccessCheckRequestBuilder()
            .with_user_id("custom_user")
            .with_resource_type(ResourceType.AI_MODEL)
            .with_resource_name("/models/gpt4")
            .with_required_level(AccessLevel.ADMIN)
            .with_organization("org_123")
            .with_context({"ip": "192.168.1.1"})
            .build()
        )
        assert request.user_id == "custom_user"
        assert request.resource_type == ResourceType.AI_MODEL
        assert request.resource_name == "/models/gpt4"
        assert request.required_access_level == AccessLevel.ADMIN
        assert request.organization_id == "org_123"
        assert request.context["ip"] == "192.168.1.1"

    def test_access_check_builder_build_dict(self):
        """Access check builder build_dict returns dict"""
        data = AccessCheckRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "user_id" in data
        assert "resource_type" in data

    def test_grant_permission_builder_default(self):
        """Grant permission builder has defaults"""
        request = GrantPermissionRequestBuilder().build()
        assert isinstance(request, GrantPermissionRequestContract)
        assert request.access_level == AccessLevel.READ_WRITE
        assert request.permission_source == PermissionSource.ADMIN_GRANT

    def test_grant_permission_builder_chaining(self):
        """Grant permission builder supports chaining"""
        future = AuthorizationTestDataFactory.make_future_timestamp()
        request = (
            GrantPermissionRequestBuilder()
            .with_user_id("user_001")
            .with_resource_type(ResourceType.DATABASE)
            .with_resource_name("analytics_db")
            .with_access_level(AccessLevel.OWNER)
            .with_permission_source(PermissionSource.ORGANIZATION)
            .with_granted_by("admin_001")
            .with_organization("org_001")
            .with_expiration(future)
            .with_reason("Team lead access")
            .build()
        )
        assert request.user_id == "user_001"
        assert request.resource_type == ResourceType.DATABASE
        assert request.access_level == AccessLevel.OWNER
        assert request.permission_source == PermissionSource.ORGANIZATION
        assert request.granted_by_user_id == "admin_001"
        assert request.organization_id == "org_001"
        assert request.expires_at == future
        assert request.reason == "Team lead access"

    def test_revoke_permission_builder_default(self):
        """Revoke permission builder has defaults"""
        request = RevokePermissionRequestBuilder().build()
        assert isinstance(request, RevokePermissionRequestContract)
        assert request.revoked_by_user_id is not None

    def test_revoke_permission_builder_chaining(self):
        """Revoke permission builder supports chaining"""
        request = (
            RevokePermissionRequestBuilder()
            .with_user_id("user_002")
            .with_resource_type(ResourceType.COMPUTE)
            .with_resource_name("gpu_cluster")
            .with_revoked_by("admin_002")
            .with_reason("Access review")
            .build()
        )
        assert request.user_id == "user_002"
        assert request.resource_type == ResourceType.COMPUTE
        assert request.resource_name == "gpu_cluster"
        assert request.revoked_by_user_id == "admin_002"
        assert request.reason == "Access review"

    def test_bulk_permission_builder_default(self):
        """Bulk permission builder has defaults"""
        builder = BulkPermissionRequestBuilder()
        builder.add_multiple_grants(2)
        request = builder.build()
        assert isinstance(request, BulkPermissionRequestContract)
        assert len(request.operations) == 2

    def test_bulk_permission_builder_mixed_operations(self):
        """Bulk permission builder supports mixed operations"""
        grant = AuthorizationTestDataFactory.make_grant_request()
        revoke = AuthorizationTestDataFactory.make_revoke_request()

        request = (
            BulkPermissionRequestBuilder()
            .add_grant(grant)
            .add_revoke(revoke)
            .add_multiple_grants(2)
            .add_multiple_revokes(2)
            .with_executed_by("admin_bulk")
            .with_reason("Quarterly access review")
            .build()
        )
        assert len(request.operations) == 6
        assert request.executed_by_user_id == "admin_bulk"
        assert request.batch_reason == "Quarterly access review"


# ============================================================================
# Test Contract Validation with Factory Data
# ============================================================================


class TestContractValidation:
    """Test contract validation using factory data"""

    def test_access_request_accepts_factory_data(self):
        """Access request accepts factory-generated data"""
        request = AuthorizationTestDataFactory.make_access_check_request()
        assert request.user_id is not None
        assert request.resource_type is not None
        assert request.resource_name is not None

    def test_access_request_rejects_empty_user_id(self):
        """Access request rejects empty user ID"""
        with pytest.raises(ValidationError):
            ResourceAccessRequestContract(
                user_id=AuthorizationTestDataFactory.make_invalid_user_id_empty(),
                resource_type=ResourceType.API_ENDPOINT,
                resource_name="/api/test"
            )

    def test_access_request_rejects_whitespace_user_id(self):
        """Access request rejects whitespace user ID"""
        with pytest.raises(ValidationError):
            ResourceAccessRequestContract(
                user_id=AuthorizationTestDataFactory.make_invalid_user_id_whitespace(),
                resource_type=ResourceType.API_ENDPOINT,
                resource_name="/api/test"
            )

    def test_access_request_rejects_empty_resource_name(self):
        """Access request rejects empty resource name"""
        with pytest.raises(ValidationError):
            ResourceAccessRequestContract(
                user_id=AuthorizationTestDataFactory.make_user_id(),
                resource_type=ResourceType.API_ENDPOINT,
                resource_name=AuthorizationTestDataFactory.make_invalid_resource_name_empty()
            )

    def test_grant_request_accepts_factory_data(self):
        """Grant request accepts factory-generated data"""
        request = AuthorizationTestDataFactory.make_grant_request()
        assert request.user_id is not None
        assert request.access_level is not None
        assert request.permission_source is not None

    def test_grant_request_rejects_past_expiry(self):
        """Grant request rejects past expiry date"""
        with pytest.raises(ValidationError):
            GrantPermissionRequestContract(
                user_id=AuthorizationTestDataFactory.make_user_id(),
                resource_type=ResourceType.API_ENDPOINT,
                resource_name="/api/test",
                access_level=AccessLevel.READ_WRITE,
                permission_source=PermissionSource.ADMIN_GRANT,
                expires_at=AuthorizationTestDataFactory.make_invalid_expires_at_past()
            )

    def test_bulk_request_rejects_empty_operations(self):
        """Bulk request rejects empty operations"""
        with pytest.raises(ValidationError):
            BulkPermissionRequestContract(
                operations=AuthorizationTestDataFactory.make_invalid_bulk_operations_empty()
            )

    def test_bulk_request_rejects_too_many_operations(self):
        """Bulk request rejects too many operations"""
        with pytest.raises(ValidationError):
            BulkPermissionRequestContract(
                operations=AuthorizationTestDataFactory.make_invalid_bulk_operations_too_many()
            )

    def test_resource_config_accepts_factory_data(self):
        """Resource config accepts factory-generated data"""
        config = AuthorizationTestDataFactory.make_resource_config_request()
        assert config.resource_type is not None
        assert config.resource_name is not None
        assert config.is_enabled is True

    def test_org_permission_config_accepts_factory_data(self):
        """Org permission config accepts factory-generated data"""
        config = AuthorizationTestDataFactory.make_org_permission_config_request()
        assert config.organization_id is not None
        assert config.access_level is not None


# ============================================================================
# Test Data Consistency
# ============================================================================


class TestDataConsistency:
    """Test data consistency in generated objects"""

    def test_bulk_response_counts_consistent(self):
        """Bulk response counts are consistent"""
        for _ in range(20):
            response = AuthorizationTestDataFactory.make_bulk_response(total=10)
            assert response["successful"] + response["failed"] == response["total_operations"]

    def test_permission_summary_has_valid_counts(self):
        """Permission summary has valid counts"""
        response = AuthorizationTestDataFactory.make_permission_summary_response()
        assert response["total_permissions"] >= 0
        assert response["expires_soon_count"] >= 0

    def test_batch_result_has_error_only_on_failure(self):
        """Batch result has error message only on failure"""
        for _ in range(50):
            result = AuthorizationTestDataFactory.make_batch_result()
            if result["success"]:
                assert result["error_message"] is None
            else:
                assert result["error_message"] is not None

    def test_accessible_resources_response_consistent(self):
        """Accessible resources response is consistent"""
        for count in [0, 5, 10]:
            response = AuthorizationTestDataFactory.make_accessible_resources_response(count=count)
            assert len(response["accessible_resources"]) == response["total_count"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
