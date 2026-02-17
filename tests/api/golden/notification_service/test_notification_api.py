"""
Notification Service API Tests

This test suite validates the Notification Service HTTP API endpoints:
- Request/response validation
- Error handling
- Authentication and authorization
- Rate limiting
- API contract compliance

These tests focus on API behavior without external dependencies.
"""

import pytest
import json
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import os

# Import contract components
from tests.contracts.notification.data_contract import (
    NotificationType, NotificationStatus, NotificationPriority,
    SendNotificationRequestContract, NotificationResponseContract, InAppNotificationResponseContract,
    CreateTemplateRequestContract, TemplateResponseContract, NotificationStatsResponseContract,
    NotificationTestDataFactory
)


class TestNotificationAPI:
    """Test Notification Service API endpoints"""
    
    @pytest.fixture
    def api_client(self):
        """Create HTTP client for API testing"""
        base_url = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8215")
        return httpx.Client(base_url=base_url, timeout=30.0)
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {
            "Authorization": "Bearer mock_test_token_12345",
            "X-User-ID": "api-test-user-123",
            "Content-Type": "application/json"
        }


class TestSendNotificationAPI:
    """Test POST /api/v1/notifications/send endpoint"""
    
    def test_send_email_notification_success(self, api_client, auth_headers):
        """Test successful email notification sending"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="api-test@example.com",
            content="API test email notification",
            priority=NotificationPriority.NORMAL
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify response structure
        assert "success" in response_data
        assert response_data["success"] is True
        assert "notification" in response_data
        
        notification = response_data["notification"]
        assert notification["type"] == NotificationType.EMAIL.value
        assert notification["recipient_email"] == "api-test@example.com"
        assert notification["content"] == "API test email notification"
        assert notification["priority"] == NotificationPriority.NORMAL.value
        assert notification["status"] == NotificationStatus.PENDING.value
        assert "notification_id" in notification
        assert "created_at" in notification
    
    def test_send_push_notification_success(self, api_client, auth_headers):
        """Test successful push notification sending"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.PUSH,
            recipient_id="api-test-user-123",
            title="API Push Test",
            content="API test push notification",
            data={"custom_key": "custom_value"}
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        notification = response_data["notification"]
        assert notification["type"] == NotificationType.PUSH.value
        assert notification["recipient_id"] == "api-test-user-123"
        assert notification["title"] == "API Push Test"
        assert notification["data"]["custom_key"] == "custom_value"
    
    def test_send_notification_with_template_success(self, api_client, auth_headers):
        """Test sending notification using template"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="template-test@example.com",
            template_id="tpl_test_123",
            variables={"name": "API Test User", "action": "template testing"}
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        notification = response_data["notification"]
        assert notification["template_id"] == "tpl_test_123"
        assert notification["variables"]["name"] == "API Test User"
    
    def test_send_notification_missing_required_fields(self, api_client, auth_headers):
        """Test sending notification with missing required fields"""
        
        invalid_request = {
            "type": "email"
            # Missing recipient_email or recipient_id
        }
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "error" in error_data
        assert "validation" in error_data["error"].lower()
        assert "recipient" in error_data["error"].lower()
    
    def test_send_notification_invalid_type(self, api_client, auth_headers):
        """Test sending notification with invalid type"""
        
        invalid_request = NotificationTestDataFactory.make_send_request(
            recipient_email="test@example.com",
            content="Test content"
        )
        invalid_request["type"] = "invalid_type"  # Invalid notification type
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "invalid type" in error_data["error"].lower()
    
    def test_send_notification_invalid_recipient(self, api_client, auth_headers):
        """Test sending notification with invalid recipient"""
        
        invalid_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="invalid-email-format",  # Invalid email
            content="Test content"
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=invalid_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "invalid email" in error_data["error"].lower()
    
    def test_send_notification_unauthorized(self, api_client):
        """Test sending notification without authentication"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="unauthorized@example.com",
            content="Unauthorized test"
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict()
        )
        
        assert response.status_code == 401
        error_data = response.json()
        assert "unauthorized" in error_data["error"].lower()
    
    def test_send_notification_rate_limit(self, api_client, auth_headers):
        """Test rate limiting on notification sending"""
        
        # Send multiple requests rapidly
        requests = []
        for i in range(10):
            notification_request = NotificationTestDataFactory.make_send_request(
                type=NotificationType.EMAIL,
                recipient_email=f"ratelimit{i}@example.com",
                content=f"Rate limit test {i}"
            )
            
            request = api_client.post(
                "/api/v1/notifications/send",
                json=notification_request.dict(),
                headers=auth_headers
            )
            requests.append(request)
        
        # Execute requests
        responses = []
        for request in requests:
            try:
                response = request
                responses.append(response)
            except Exception:
                pass
        
        # Should hit rate limit
        rate_limited = any(r.status_code == 429 for r in responses if hasattr(r, 'status_code'))
        assert rate_limited


class TestBatchNotificationAPI:
    """Test POST /api/v1/notifications/batch endpoint"""
    
    def test_send_batch_notifications_success(self, api_client, auth_headers):
        """Test successful batch notification sending"""
        
        batch_request = {
            "name": "API Test Batch",
            "template_id": "tpl_batch_123",
            "type": NotificationType.EMAIL.value,
            "recipients": [
                {"recipient_email": "batch1@example.com", "variables": {"name": "User 1"}},
                {"recipient_email": "batch2@example.com", "variables": {"name": "User 2"}},
                {"recipient_email": "batch3@example.com", "variables": {"name": "User 3"}}
            ],
            "priority": NotificationPriority.NORMAL.value
        }
        
        response = api_client.post(
            "/api/v1/notifications/batch",
            json=batch_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify batch response structure
        assert "success" in response_data
        assert response_data["success"] is True
        assert "batch" in response_data
        
        batch = response_data["batch"]
        assert batch["name"] == "API Test Batch"
        assert batch["total_recipients"] == 3
        assert batch["status"] in ["pending", "processing"]
        assert "batch_id" in batch
        assert batch["batch_id"].startswith("batch_")
    
    def test_send_batch_empty_recipients(self, api_client, auth_headers):
        """Test batch notification with empty recipients"""
        
        batch_request = {
            "name": "Empty Batch",
            "recipients": [],
            "type": NotificationType.EMAIL.value
        }
        
        response = api_client.post(
            "/api/v1/notifications/batch",
            json=batch_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "recipients" in error_data["error"].lower()
        assert "empty" in error_data["error"].lower()
    
    def test_send_batch_too_many_recipients(self, api_client, auth_headers):
        """Test batch notification exceeding recipient limit"""
        
        # Create batch with too many recipients (assuming limit is 1000)
        recipients = [
            {"recipient_email": f"user{i}@example.com"}
            for i in range(1001)
        ]
        
        batch_request = {
            "name": "Large Batch",
            "recipients": recipients,
            "type": NotificationType.EMAIL.value
        }
        
        response = api_client.post(
            "/api/v1/notifications/batch",
            json=batch_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "too many recipients" in error_data["error"].lower()


class TestInAppNotificationAPI:
    """Test in-app notification endpoints"""
    
    def test_list_in_app_notifications_success(self, api_client, auth_headers):
        """Test listing in-app notifications for user"""
        
        user_id = "api-test-user-123"
        response = api_client.get(
            f"/api/v1/notifications/in-app/{user_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        notifications_list = response.json()
        
        # Verify list response structure
        assert isinstance(notifications_list, list)
        
        # If there are notifications, verify structure
        if notifications_list:
            notification = notifications_list[0]
            assert "notification_id" in notification
            assert "type" in notification
            assert "title" in notification
            assert "content" in notification
            assert "is_read" in notification
            assert "created_at" in notification
    
    def test_mark_notification_as_read_success(self, api_client, auth_headers):
        """Test marking notification as read"""
        
        notification_id = "ntf_test_123"
        mark_read_request = {"is_read": True}
        
        response = api_client.patch(
            f"/api/v1/notifications/{notification_id}/read",
            json=mark_read_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
    
    def test_mark_notification_as_read_invalid_id(self, api_client, auth_headers):
        """Test marking non-existent notification as read"""
        
        notification_id = "ntf_nonexistent_123"
        mark_read_request = {"is_read": True}
        
        response = api_client.patch(
            f"/api/v1/notifications/{notification_id}/read",
            json=mark_read_request,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"].lower()


class TestTemplateAPI:
    """Test template management endpoints"""
    
    def test_create_template_success(self, api_client, auth_headers):
        """Test successful template creation"""
        
        template_request = NotificationTestDataFactory.make_create_template_request(
            name="API Test Template",
            type=NotificationType.EMAIL,
            subject="Test {{subject}} from API",
            content="Hello {{name}}, this is a {{message}} from API.",
            variables=["subject", "name", "message"]
        )
        
        response = api_client.post(
            "/api/v1/notifications/templates",
            json=template_request.dict(),
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify template response structure
        assert "success" in response_data
        assert response_data["success"] is True
        assert "template" in response_data
        
        template = response_data["template"]
        assert template["name"] == "API Test Template"
        assert template["type"] == NotificationType.EMAIL.value
        assert template["subject"] == "Test {{subject}} from API"
        assert template["content"] == "Hello {{name}}, this is a {{message}} from the API."
        assert template["variables"] == ["subject", "name", "message"]
        assert "template_id" in template
        assert template["template_id"].startswith("tpl_")
        assert template["status"] == "active"
    
    def test_create_template_invalid_syntax(self, api_client, auth_headers):
        """Test template creation with invalid variable syntax"""
        
        invalid_template_request = NotificationTestDataFactory.make_create_template_request(
            name="Invalid Syntax Template",
            type=NotificationType.EMAIL,
            subject="Invalid {{subject syntax",  # Missing closing brace
            content="Hello {{name}, invalid syntax",
            variables=["subject", "name"]
        )
        
        response = api_client.post(
            "/api/v1/notifications/templates",
            json=invalid_template_request.dict(),
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "syntax" in error_data["error"].lower()
        assert "variable" in error_data["error"].lower()
    
    def test_create_template_duplicate_name(self, api_client, auth_headers):
        """Test template creation with duplicate name"""
        
        # First template creation (mocked to succeed)
        template_request1 = NotificationTestDataFactory.make_create_template_request(
            name="Duplicate Template Name",
            type=NotificationType.EMAIL,
            subject="First template",
            content="First content"
        )
        
        # Second template with same name
        template_request2 = NotificationTestDataFactory.make_create_template_request(
            name="Duplicate Template Name",  # Same name
            type=NotificationType.EMAIL,
            subject="Second template",
            content="Second content"
        )
        
        # Mock first request to succeed, second to fail
        response1 = api_client.post(
            "/api/v1/notifications/templates",
            json=template_request1.dict(),
            headers=auth_headers
        )
        
        response2 = api_client.post(
            "/api/v1/notifications/templates",
            json=template_request2.dict(),
            headers=auth_headers
        )
        
        # Second request should fail due to duplicate name
        assert response2.status_code == 409  # Conflict
        error_data = response2.json()
        assert "already exists" in error_data["error"].lower()
        assert "name" in error_data["error"].lower()
    
    def test_get_template_success(self, api_client, auth_headers):
        """Test getting template by ID"""
        
        template_id = "tpl_test_123"
        response = api_client.get(
            f"/api/v1/notifications/templates/{template_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify template response structure
        assert "template" in response_data
        template = response_data["template"]
        assert template["template_id"] == template_id
        assert "name" in template
        assert "type" in template
        assert "content" in template
        assert "variables" in template
        assert "created_at" in template
    
    def test_get_template_not_found(self, api_client, auth_headers):
        """Test getting non-existent template"""
        
        template_id = "tpl_nonexistent_123"
        response = api_client.get(
            f"/api/v1/notifications/templates/{template_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"].lower()
    
    def test_list_templates_success(self, api_client, auth_headers):
        """Test listing templates with filters"""
        
        response = api_client.get(
            "/api/v1/notifications/templates?type=email&status=active&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        templates_list = response.json()
        
        # Verify list response structure
        assert isinstance(templates_list, list)
        
        # If there are templates, verify structure and filters
        if templates_list:
            for template in templates_list:
                assert template["type"] == NotificationType.EMAIL.value
                assert template["status"] == "active"
                assert "template_id" in template
                assert "name" in template
    
    def test_update_template_success(self, api_client, auth_headers):
        """Test successful template update"""
        
        template_id = "tpl_test_123"
        update_request = {
            "name": "Updated API Template",
            "subject": "Updated {{subject}}",
            "content": "Updated content for {{name}}",
            "variables": ["subject", "name"]
        }
        
        response = api_client.put(
            f"/api/v1/notifications/templates/{template_id}",
            json=update_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify update response
        updated_template = response_data["template"]
        assert updated_template["name"] == "Updated API Template"
        assert updated_template["subject"] == "Updated {{subject}}"
        assert updated_template["variables"] == ["subject", "name"]
        assert "version" in updated_template
        assert updated_template["version"] > 1
    
    def test_delete_template_success(self, api_client, auth_headers):
        """Test successful template deletion"""
        
        template_id = "tpl_test_123"
        response = api_client.delete(
            f"/api/v1/notifications/templates/{template_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
    
    def test_delete_template_not_found(self, api_client, auth_headers):
        """Test deleting non-existent template"""
        
        template_id = "tpl_nonexistent_123"
        response = api_client.delete(
            f"/api/v1/notifications/templates/{template_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"].lower()


class TestTemplateRenderAPI:
    """Test template rendering endpoint"""
    
    def test_render_template_success(self, api_client, auth_headers):
        """Test successful template rendering"""
        
        render_request = {
            "template_id": "tpl_test_123",
            "variables": {
                "name": "API Test User",
                "subject": "Rendering Test",
                "message": "template rendering is working"
            }
        }
        
        response = api_client.post(
            "/api/v1/notifications/templates/render",
            json=render_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify render response
        assert "success" in response_data
        assert response_data["success"] is True
        assert "rendered" in response_data
        
        rendered = response_data["rendered"]
        assert "subject" in rendered
        assert "content" in rendered
        assert "variables_used" in rendered
    
    def test_render_template_not_found(self, api_client, auth_headers):
        """Test rendering non-existent template"""
        
        render_request = {
            "template_id": "tpl_nonexistent_123",
            "variables": {"name": "Test User"}
        }
        
        response = api_client.post(
            "/api/v1/notifications/templates/render",
            json=render_request,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"].lower()
    
    def test_render_template_missing_variables(self, api_client, auth_headers):
        """Test rendering template with missing variables"""
        
        render_request = {
            "template_id": "tpl_test_123",
            "variables": {}  # Missing required variables
        }
        
        response = api_client.post(
            "/api/v1/notifications/templates/render",
            json=render_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "missing variables" in error_data["error"].lower()


class TestPushSubscriptionAPI:
    """Test push subscription management endpoints"""
    
    def test_register_push_subscription_success(self, api_client, auth_headers):
        """Test successful push subscription registration"""
        
        subscription_request = {
            "user_id": "api-test-user-123",
            "device_token": "api_test_token_abc123",
            "platform": "ios",
            "device_name": "API Test Device",
            "app_version": "1.0.0"
        }
        
        response = api_client.post(
            "/api/v1/notifications/subscriptions/push",
            json=subscription_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify subscription response structure
        assert "success" in response_data
        assert response_data["success"] is True
        assert "subscription" in response_data
        
        subscription = response_data["subscription"]
        assert subscription["user_id"] == "api-test-user-123"
        assert subscription["device_token"] == "api_test_token_abc123"
        assert subscription["platform"] == "ios"
        assert subscription["device_name"] == "API Test Device"
        assert "subscription_id" in subscription
        assert subscription["subscription_id"].startswith("sub_")
    
    def test_register_push_subscription_invalid_platform(self, api_client, auth_headers):
        """Test push subscription with invalid platform"""
        
        subscription_request = {
            "user_id": "api-test-user-123",
            "device_token": "test_token_123",
            "platform": "invalid_platform",  # Invalid platform
            "device_name": "Test Device"
        }
        
        response = api_client.post(
            "/api/v1/notifications/subscriptions/push",
            json=subscription_request,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "invalid platform" in error_data["error"].lower()
    
    def test_list_user_subscriptions_success(self, api_client, auth_headers):
        """Test listing user's push subscriptions"""
        
        user_id = "api-test-user-123"
        response = api_client.get(
            f"/api/v1/notifications/subscriptions/user/{user_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        subscriptions_list = response.json()
        
        # Verify list response structure
        assert isinstance(subscriptions_list, list)
        
        # If there are subscriptions, verify structure
        if subscriptions_list:
            subscription = subscriptions_list[0]
            assert "subscription_id" in subscription
            assert "user_id" in subscription
            assert "device_token" in subscription
            assert "platform" in subscription
            assert "is_active" in subscription
    
    def test_update_subscription_success(self, api_client, auth_headers):
        """Test successful subscription update"""
        
        subscription_id = "sub_test_123"
        update_request = {
            "device_name": "Updated API Device",
            "app_version": "2.0.0"
        }
        
        response = api_client.put(
            f"/api/v1/notifications/subscriptions/{subscription_id}",
            json=update_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify update response
        updated_subscription = response_data["subscription"]
        assert updated_subscription["device_name"] == "Updated API Device"
        assert updated_subscription["app_version"] == "2.0.0"
    
    def test_deactivate_subscription_success(self, api_client, auth_headers):
        """Test successful subscription deactivation"""
        
        subscription_id = "sub_test_123"
        response = api_client.delete(
            f"/api/v1/notifications/subscriptions/{subscription_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True


class TestNotificationStatisticsAPI:
    """Test notification statistics endpoints"""
    
    def test_get_notification_statistics_success(self, api_client, auth_headers):
        """Test getting notification statistics"""
        
        response = api_client.get(
            "/api/v1/notifications/stats?period=7d",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify statistics response structure
        assert "stats" in response_data
        stats = response_data["stats"]
        
        assert "total_sent" in stats
        assert "total_delivered" in stats
        assert "total_failed" in stats
        assert "by_type" in stats
        assert "by_status" in stats
        assert "period" in stats
        assert stats["period"] == "7d"
    
    def test_get_notification_statistics_invalid_period(self, api_client, auth_headers):
        """Test statistics with invalid period"""
        
        response = api_client.get(
            "/api/v1/notifications/stats?period=invalid_period",
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "invalid period" in error_data["error"].lower()
    
    def test_get_notification_details_success(self, api_client, auth_headers):
        """Test getting notification details"""
        
        notification_id = "ntf_test_123"
        response = api_client.get(
            f"/api/v1/notifications/{notification_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify notification response structure
        assert "notification" in response_data
        notification = response_data["notification"]
        assert notification["notification_id"] == notification_id
        assert "type" in notification
        assert "status" in notification
        assert "created_at" in notification
        assert "delivery_status" in notification
    
    def test_get_notification_details_not_found(self, api_client, auth_headers):
        """Test getting non-existent notification details"""
        
        notification_id = "ntf_nonexistent_123"
        response = api_client.get(
            f"/api/v1/notifications/{notification_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"].lower()


class TestNotificationHealthAPI:
    """Test health check endpoints"""
    
    def test_health_check_success(self, api_client):
        """Test service health check"""
        
        response = api_client.get("/health")
        
        assert response.status_code == 200
        health_data = response.json()
        
        # Verify health check structure
        assert "status" in health_data
        assert "service" in health_data
        assert "version" in health_data
        assert "timestamp" in health_data
        assert "checks" in health_data
        
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "notification_service"
    
    def test_readiness_check_success(self, api_client):
        """Test service readiness check"""
        
        response = api_client.get("/health/ready")
        
        assert response.status_code == 200
        readiness_data = response.json()
        
        # Verify readiness check structure
        assert "ready" in readiness_data
        assert "checks" in readiness_data
        assert readiness_data["ready"] is True
    
    def test_metrics_endpoint_success(self, api_client):
        """Test metrics endpoint"""
        
        response = api_client.get("/metrics")
        
        assert response.status_code == 200
        
        # Metrics should be in Prometheus format
        metrics_text = response.text
        assert "notification_" in metrics_text or "# HELP" in metrics_text


class TestAPIAuthentication:
    """Test API authentication and authorization"""
    
    def test_missing_authentication_header(self, api_client):
        """Test API access without authentication header"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="no-auth@example.com",
            content="No auth test"
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict()
        )
        
        assert response.status_code == 401
        error_data = response.json()
        assert "unauthorized" in error_data["error"].lower()
    
    def test_invalid_token(self, api_client):
        """Test API access with invalid token"""
        
        invalid_headers = {
            "Authorization": "Bearer invalid_token_123",
            "X-User-ID": "test-user"
        }
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="invalid-token@example.com",
            content="Invalid token test"
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=invalid_headers
        )
        
        assert response.status_code == 401
        error_data = response.json()
        assert "unauthorized" in error_data["error"].lower()
    
    def test_expired_token(self, api_client):
        """Test API access with expired token"""
        
        expired_headers = {
            "Authorization": "Bearer expired_token_123",
            "X-User-ID": "test-user"
        }
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="expired-token@example.com",
            content="Expired token test"
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=expired_headers
        )
        
        assert response.status_code == 401
        error_data = response.json()
        assert "unauthorized" in error_data["error"].lower()
    
    def test_forbidden_access(self, api_client, auth_headers):
        """Test API access to forbidden resource"""
        
        # Try to access another user's notifications
        forbidden_headers = {
            **auth_headers,
            "X-User-ID": "other-user-456"  # Different user
        }
        
        response = api_client.get(
            "/api/v1/notifications/in-app/other-user-456",
            headers=forbidden_headers
        )
        
        assert response.status_code == 403
        error_data = response.json()
        assert "forbidden" in error_data["error"].lower()


class TestAPIErrorHandling:
    """Test API error handling and edge cases"""
    
    def test_malformed_json_request(self, api_client, auth_headers):
        """Test handling of malformed JSON"""
        
        response = api_client.post(
            "/api/v1/notifications/send",
            content="invalid json {",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "json" in error_data["error"].lower()
        assert "malformed" in error_data["error"].lower()
    
    def test_empty_request_body(self, api_client, auth_headers):
        """Test handling of empty request body"""
        
        response = api_client.post(
            "/api/v1/notifications/send",
            content="",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "empty" in error_data["error"].lower()
        assert "request" in error_data["error"].lower()
    
    def test_unsupported_http_method(self, api_client, auth_headers):
        """Test handling of unsupported HTTP methods"""
        
        response = api_client.patch(
            "/api/v1/notifications/send",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 405
        assert "allow" in response.headers
    
    def test_nonexistent_endpoint(self, api_client, auth_headers):
        """Test access to non-existent endpoint"""
        
        response = api_client.get(
            "/api/v1/notifications/nonexistent",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"].lower()
    
    def test_large_request_body(self, api_client, auth_headers):
        """Test handling of excessively large request body"""
        
        # Create very large content
        large_content = "x" * 1000000  # 1MB of content
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="large@example.com",
            content=large_content
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=auth_headers
        )
        
        # Should either succeed or fail with appropriate error
        assert response.status_code in [200, 413, 422]
        
        if response.status_code == 413:
            error_data = response.json()
            assert "large" in error_data["error"].lower()


class TestAPIPagination:
    """Test API pagination functionality"""
    
    def test_list_notifications_with_pagination(self, api_client, auth_headers):
        """Test listing notifications with pagination parameters"""
        
        response = api_client.get(
            "/api/v1/notifications?limit=10&offset=5&status=pending",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        notifications_list = response.json()
        
        # Verify pagination response structure
        assert isinstance(notifications_list, list)
        # Should have at most 10 items due to limit
        assert len(notifications_list) <= 10
    
    def test_list_notifications_invalid_pagination(self, api_client, auth_headers):
        """Test listing notifications with invalid pagination"""
        
        response = api_client.get(
            "/api/v1/notifications?limit=1000",  # Exceeds max limit
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "limit" in error_data["error"].lower()
    
    def test_list_templates_with_pagination(self, api_client, auth_headers):
        """Test listing templates with pagination parameters"""
        
        response = api_client.get(
            "/api/v1/notifications/templates?limit=20&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        templates_list = response.json()
        
        # Verify pagination response structure
        assert isinstance(templates_list, list)
        # Should have at most 20 items due to limit
        assert len(templates_list) <= 20


class TestAPIResponseHeaders:
    """Test API response headers"""
    
    def test_cors_headers(self, api_client):
        """Test CORS headers in API responses"""
        
        response = api_client.get("/health")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_content_type_headers(self, api_client, auth_headers):
        """Test content-type headers in API responses"""
        
        response = api_client.get(
            "/api/v1/notifications/templates",
            headers=auth_headers
        )
        
        # Should have JSON content type
        assert "application/json" in response.headers["content-type"]
    
    def test_rate_limit_headers(self, api_client, auth_headers):
        """Test rate limiting headers in API responses"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="rate-limit-test@example.com",
            content="Rate limit test"
        )
        
        response = api_client.post(
            "/api/v1/notifications/send",
            json=notification_request.dict(),
            headers=auth_headers
        )
        
        # Check for rate limiting headers
        assert "x-rate-limit-remaining" in response.headers
        assert "x-rate-limit-reset" in response.headers


if __name__ == "__main__":
    # Run API tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
