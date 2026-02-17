"""
Notification Service Integration Tests

This test suite validates integration between Notification Service components:
- HTTP API endpoints
- Database operations (PostgreSQL)
- Message passing (NATS)
- External service dependencies (Auth Service)
- Email provider integration
- Push notification services

These tests require running infrastructure components.
"""

import pytest
import asyncio
import json
import httpx
import asyncpg
import nats
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import os
import secrets

# Import contract components
from tests.contracts.notification.data_contract import (
    NotificationType, NotificationStatus, NotificationPriority,
    SendNotificationRequestContract, NotificationResponseContract, InAppNotificationResponseContract,
    CreateTemplateRequestContract, TemplateResponseContract, NotificationStatsResponseContract,
    NotificationTestDataFactory
)


class TestNotificationServiceIntegration:
    """Test Notification Service integration with external dependencies"""
    
    @pytest.fixture(scope="class")
    async def test_config(self):
        """Test configuration for integration tests"""
        return {
            "notification_service_url": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8215"),
            "database_url": os.getenv("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/notification_test"),
            "nats_url": os.getenv("NATS_URL", "nats://localhost:4222"),
            "auth_service_url": os.getenv("AUTH_SERVICE_URL", "http://localhost:8210"),
            "test_user_id": "integration-test-user",
            "test_email": "integration-test@example.com"
        }
    
    @pytest.fixture(scope="class")
    async def db_pool(self, test_config):
        """Create database connection pool"""
        return await asyncpg.create_pool(
            test_config["database_url"],
            min_size=2,
            max_size=10
        )
    
    @pytest.fixture(scope="class")
    async def nats_client(self, test_config):
        """Create NATS client"""
        nc = await nats.connect(test_config["nats_url"])
        yield nc
        await nc.close()
    
    @pytest.fixture(scope="class")
    async def http_client(self, test_config):
        """Create HTTP client"""
        async with httpx.AsyncClient(base_url=test_config["notification_service_url"]) as client:
            yield client
    
    @pytest.fixture(autouse=True)
    async def setup_test_data(self, db_pool, test_config):
        """Setup test data before each test"""
        # Clean up any existing test data
        await db_pool.execute("""
            DELETE FROM notification.notifications WHERE user_id = $1
        """, test_config["test_user_id"])
        
        await db_pool.execute("""
            DELETE FROM notification.templates WHERE created_by = $1
        """, test_config["test_user_id"])
        
        yield
        
        # Cleanup after each test
        await db_pool.execute("""
            DELETE FROM notification.notifications WHERE user_id = $1
        """, test_config["test_user_id"])
        
        await db_pool.execute("""
            DELETE FROM notification.templates WHERE created_by = $1
        """, test_config["test_user_id"])


class TestEmailNotificationIntegration:
    """Test email notification integration with database and events"""
    
    async def test_send_email_notification_success(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test successful email notification with database persistence and event publishing"""
        
        # Create email notification request
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email=test_config["test_email"],
            content="Integration test email notification"
        )
        
        # Send notification via API
        response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify response structure
        assert "notification" in response_data
        assert response_data["success"] is True
        notification = response_data["notification"]
        assert notification["type"] == NotificationType.EMAIL.value
        assert notification["recipient_email"] == test_config["test_email"]
        assert notification["status"] == NotificationStatus.PENDING.value
        assert notification["notification_id"].startswith("ntf_")
        
        notification_id = notification["notification_id"]
        
        # Verify database persistence
        db_record = await db_pool.fetchrow("""
            SELECT notification_id, type, recipient_email, content, status, user_id
            FROM notification.notifications WHERE notification_id = $1
        """, notification_id)
        
        assert db_record is not None
        assert db_record["notification_id"] == notification_id
        assert db_record["type"] == NotificationType.EMAIL.value
        assert db_record["recipient_email"] == test_config["test_email"]
        assert db_record["content"] == notification_request.content
        assert db_record["status"] == NotificationStatus.PENDING.value
        assert db_record["user_id"] == test_config["test_user_id"]
        
        # Verify event publishing to NATS
        events = []
        
        async def message_handler(msg):
            events.append(json.loads(msg.data.decode()))
        
        await nats_client.subscribe("notification.created", cb=message_handler)
        
        # Wait for event
        await asyncio.sleep(0.5)
        
        assert len(events) > 0
        notification_created_event = next((e for e in events if e.get("notification_id") == notification_id), None)
        assert notification_created_event is not None
        assert notification_created_event["event_type"] == "notification.created"
        assert notification_created_event["notification_id"] == notification_id
        assert notification_created_event["type"] == NotificationType.EMAIL.value
    
    async def test_send_email_with_template_success(
        self, http_client, db_pool, test_config
    ):
        """Test email notification using template"""
        
        # First create a template
        template_request = NotificationTestDataFactory.make_create_template_request(
            name="Integration Email Template",
            type=NotificationType.EMAIL,
            subject="Test {{subject}}",
            content="Hello {{name}}, this is a {{message}} notification",
            variables=["subject", "name", "message"]
        )
        
        template_response = await http_client.post("/api/v1/notifications/templates", json=template_request.dict())
        assert template_response.status_code == 200
        template_data = template_response.json()
        template_id = template_data["template"]["template_id"]
        
        # Send notification using template
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email=test_config["test_email"],
            template_id=template_id,
            variables={"subject": "Integration Test", "name": "Test User", "message": "template"}
        )
        
        response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify template was used
        notification = response_data["notification"]
        assert notification["template_id"] == template_id
        assert "rendered_content" in notification or "rendered_subject" in notification
        
        # Verify template usage tracked in database
        template_usage = await db_pool.fetchrow("""
            SELECT usage_count FROM notification.templates WHERE template_id = $1
        """, template_id)
        
        assert template_usage is not None
        assert template_usage["usage_count"] >= 1


class TestPushNotificationIntegration:
    """Test push notification integration with database and external services"""
    
    async def test_send_push_notification_success(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test successful push notification with database persistence"""
        
        # First register a push subscription
        subscription_data = {
            "user_id": test_config["test_user_id"],
            "device_token": "integration_test_token_123",
            "platform": "ios",
            "device_name": "Integration Test Device"
        }
        
        subscription_response = await http_client.post("/api/v1/notifications/subscriptions/push", json=subscription_data)
        assert subscription_response.status_code == 200
        
        # Send push notification
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.PUSH,
            recipient_id=test_config["test_user_id"],
            content="Integration test push notification",
            title="Test Push",
            data={"custom_key": "custom_value"}
        )
        
        response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify response structure
        notification = response_data["notification"]
        assert notification["type"] == NotificationType.PUSH.value
        assert notification["recipient_id"] == test_config["test_user_id"]
        assert notification["title"] == "Test Push"
        assert notification["status"] == NotificationStatus.PENDING.value
        
        notification_id = notification["notification_id"]
        
        # Verify database persistence
        db_record = await db_pool.fetchrow("""
            SELECT notification_id, type, recipient_id, title, data, status
            FROM notification.notifications WHERE notification_id = $1
        """, notification_id)
        
        assert db_record is not None
        assert db_record["type"] == NotificationType.PUSH.value
        assert db_record["recipient_id"] == test_config["test_user_id"]
        assert db_record["title"] == "Test Push"
        assert json.loads(db_record["data"])["custom_key"] == "custom_value"
        
        # Verify push delivery attempt logged
        delivery_attempts = await db_pool.fetch("""
            SELECT device_token, platform, status FROM notification.push_delivery_attempts
            WHERE notification_id = $1
        """, notification_id)
        
        assert len(delivery_attempts) >= 1
        assert delivery_attempts[0]["device_token"] == "integration_test_token_123"
        assert delivery_attempts[0]["platform"] == "ios"
    
    async def test_send_push_multiple_devices_success(
        self, http_client, db_pool, test_config
    ):
        """Test push notification to multiple devices for same user"""
        
        # Register multiple device subscriptions
        device_tokens = [
            ("ios_token_123", "ios"),
            ("android_token_456", "android"),
            ("ios_token_789", "ios")
        ]
        
        for token, platform in device_tokens:
            subscription_data = {
                "user_id": test_config["test_user_id"],
                "device_token": token,
                "platform": platform,
                "device_name": f"Test Device {platform}"
            }
            
            await http_client.post("/api/v1/notifications/subscriptions/push", json=subscription_data)
        
        # Send push notification
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.PUSH,
            recipient_id=test_config["test_user_id"],
            content="Multi-device push test"
        )
        
        response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        
        assert response.status_code == 200
        response_data = response.json()
        notification_id = response_data["notification"]["notification_id"]
        
        # Verify delivery attempts for all devices
        delivery_attempts = await db_pool.fetch("""
            SELECT device_token, platform, status FROM notification.push_delivery_attempts
            WHERE notification_id = $1
        """, notification_id)
        
        assert len(delivery_attempts) == len(device_tokens)
        
        device_tokens_found = {attempt["device_token"] for attempt in delivery_attempts}
        expected_tokens = {token for token, _ in device_tokens}
        assert device_tokens_found == expected_tokens


class TestBatchNotificationIntegration:
    """Test batch notification processing integration"""
    
    async def test_send_batch_notifications_success(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test successful batch notification processing"""
        
        # Create template for batch
        template_request = NotificationTestDataFactory.make_create_template_request(
            name="Batch Test Template",
            type=NotificationType.EMAIL,
            subject="Batch Test {{index}}",
            content="Hello user {{index}}, this is batch notification {{index}}",
            variables=["index"]
        )
        
        template_response = await http_client.post("/api/v1/notifications/templates", json=template_request.dict())
        template_id = template_response.json()["template"]["template_id"]
        
        # Create batch notification request
        batch_request = {
            "name": "Integration Test Batch",
            "template_id": template_id,
            "type": NotificationType.EMAIL.value,
            "recipients": [
                {"recipient_email": f"batch{i}@example.com", "variables": {"index": str(i)}}
                for i in range(5)
            ],
            "priority": NotificationPriority.NORMAL.value
        }
        
        response = await http_client.post("/api/v1/notifications/batch", json=batch_request)
        
        assert response.status_code == 200
        batch_data = response.json()
        
        # Verify batch response structure
        assert "batch" in batch_data
        assert batch_data["success"] is True
        batch = batch_data["batch"]
        assert batch["total_recipients"] == 5
        assert batch["status"] in ["pending", "processing"]
        assert batch["batch_id"].startswith("batch_")
        
        batch_id = batch["batch_id"]
        
        # Verify batch record in database
        batch_record = await db_pool.fetchrow("""
            SELECT batch_id, total_recipients, status, template_id
            FROM notification.batches WHERE batch_id = $1
        """, batch_id)
        
        assert batch_record is not None
        assert batch_record["batch_id"] == batch_id
        assert batch_record["total_recipients"] == 5
        assert batch_record["template_id"] == template_id
        
        # Verify individual notifications created
        notification_count = await db_pool.fetchval("""
            SELECT COUNT(*) FROM notification.notifications WHERE batch_id = $1
        """, batch_id)
        
        assert notification_count == 5
        
        # Verify batch processing event published
        events = []
        
        async def message_handler(msg):
            events.append(json.loads(msg.data.decode()))
        
        await nats_client.subscribe("notification.batch.created", cb=message_handler)
        await asyncio.sleep(0.5)
        
        batch_event = next((e for e in events if e.get("batch_id") == batch_id), None)
        assert batch_event is not None
        assert batch_event["event_type"] == "notification.batch.created"
        assert batch_event["batch_id"] == batch_id
        assert batch_event["total_recipients"] == 5
    
    async def test_batch_processing_with_failures(
        self, http_client, db_pool, test_config
    ):
        """Test batch processing with some failures"""
        
        # Create batch with mix of valid and invalid recipients
        batch_request = {
            "name": "Mixed Success Batch",
            "recipients": [
                {"recipient_email": "valid1@example.com", "content": "Valid content 1"},
                {"recipient_email": "invalid-email", "content": "Invalid email"},
                {"recipient_email": "valid2@example.com", "content": "Valid content 2"},
                {"recipient_email": "", "content": "Missing email"},
                {"recipient_email": "valid3@example.com", "content": "Valid content 3"}
            ]
        }
        
        response = await http_client.post("/api/v1/notifications/batch", json=batch_request)
        
        assert response.status_code == 200
        batch_data = response.json()
        batch_id = batch_data["batch"]["batch_id"]
        
        # Wait for batch processing
        await asyncio.sleep(2)
        
        # Check batch results
        batch_status = await db_pool.fetchrow("""
            SELECT sent_count, failed_count, total_recipients FROM notification.batches
            WHERE batch_id = $1
        """, batch_id)
        
        assert batch_status is not None
        assert batch_status["total_recipients"] == 5
        # Some should fail due to invalid emails
        assert batch_status["failed_count"] >= 2
        assert batch_status["sent_count"] >= 2
        assert batch_status["sent_count"] + batch_status["failed_count"] == 5


class TestInAppNotificationIntegration:
    """Test in-app notification integration"""
    
    async def test_send_in_app_notification_success(
        self, http_client, db_pool, test_config
    ):
        """Test successful in-app notification"""
        
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.IN_APP,
            recipient_id=test_config["test_user_id"],
            title="In-App Test",
            content="This is an in-app notification",
            action_url="/notifications/123"
        )
        
        response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        
        assert response.status_code == 200
        response_data = response.json()
        notification = response_data["notification"]
        
        # Verify response structure
        assert notification["type"] == NotificationType.IN_APP.value
        assert notification["recipient_id"] == test_config["test_user_id"]
        assert notification["title"] == "In-App Test"
        assert notification["action_url"] == "/notifications/123"
        assert notification["is_read"] is False
        
        notification_id = notification["notification_id"]
        
        # Verify database persistence
        db_record = await db_pool.fetchrow("""
            SELECT notification_id, type, recipient_id, title, action_url, is_read
            FROM notification.notifications WHERE notification_id = $1
        """, notification_id)
        
        assert db_record is not None
        assert db_record["type"] == NotificationType.IN_APP.value
        assert db_record["recipient_id"] == test_config["test_user_id"]
        assert db_record["title"] == "In-App Test"
        assert db_record["action_url"] == "/notifications/123"
        assert db_record["is_read"] is False
    
    async def test_list_in_app_notifications_success(
        self, http_client, db_pool, test_config
    ):
        """Test listing in-app notifications for user"""
        
        # Create multiple in-app notifications
        notifications = [
            NotificationTestDataFactory.make_send_request(
                type=NotificationType.IN_APP,
                recipient_id=test_config["test_user_id"],
                title=f"Notification {i}",
                content=f"Content {i}"
            )
            for i in range(3)
        ]
        
        for notification in notifications:
            await http_client.post("/api/v1/notifications/send", json=notification.dict())
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # List in-app notifications
        response = await http_client.get(f"/api/v1/notifications/in-app/{test_config['test_user_id']}")
        
        assert response.status_code == 200
        notifications_list = response.json()
        
        # Verify list response structure
        assert isinstance(notifications_list, list)
        assert len(notifications_list) >= 3
        
        # Verify notification properties
        for notification in notifications_list[:3]:
            assert notification["type"] == NotificationType.IN_APP.value
            assert notification["recipient_id"] == test_config["test_user_id"]
            assert "title" in notification
            assert "content" in notification
            assert "created_at" in notification
            assert "is_read" in notification
    
    async def test_mark_in_app_notification_read_success(
        self, http_client, db_pool, test_config
    ):
        """Test marking in-app notification as read"""
        
        # Create in-app notification
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.IN_APP,
            recipient_id=test_config["test_user_id"],
            title="To Be Read"
        )
        
        create_response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        notification_id = create_response.json()["notification"]["notification_id"]
        
        # Mark as read
        mark_read_request = {"is_read": True}
        response = await http_client.patch(
            f"/api/v1/notifications/{notification_id}/read",
            json=mark_read_request
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        
        # Verify database update
        db_record = await db_pool.fetchrow("""
            SELECT is_read, read_at FROM notification.notifications WHERE notification_id = $1
        """, notification_id)
        
        assert db_record is not None
        assert db_record["is_read"] is True
        assert db_record["read_at"] is not None


class TestTemplateManagementIntegration:
    """Test template management integration"""
    
    async def test_create_template_success(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test successful template creation with database persistence"""
        
        template_request = NotificationTestDataFactory.make_create_template_request(
            name="Integration Test Template",
            type=NotificationType.EMAIL,
            subject="Test {{subject}}",
            content="Hello {{name}}, {{content}}",
            variables=["subject", "name", "content"]
        )
        
        response = await http_client.post("/api/v1/notifications/templates", json=template_request.dict())
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify response structure
        assert "template" in response_data
        assert response_data["success"] is True
        template = response_data["template"]
        assert template["name"] == "Integration Test Template"
        assert template["type"] == NotificationType.EMAIL.value
        assert template["variables"] == ["subject", "name", "content"]
        assert template["template_id"].startswith("tpl_")
        
        template_id = template["template_id"]
        
        # Verify database persistence
        db_record = await db_pool.fetchrow("""
            SELECT template_id, name, type, subject, content, variables, created_by
            FROM notification.templates WHERE template_id = $1
        """, template_id)
        
        assert db_record is not None
        assert db_record["template_id"] == template_id
        assert db_record["name"] == "Integration Test Template"
        assert db_record["type"] == NotificationType.EMAIL.value
        assert db_record["subject"] == "Test {{subject}}"
        assert db_record["content"] == "Hello {{name}}, {{content}}"
        assert db_record["created_by"] == test_config["test_user_id"]
        
        # Verify template creation event published
        events = []
        
        async def message_handler(msg):
            events.append(json.loads(msg.data.decode()))
        
        await nats_client.subscribe("notification.template.created", cb=message_handler)
        await asyncio.sleep(0.5)
        
        template_event = next((e for e in events if e.get("template_id") == template_id), None)
        assert template_event is not None
        assert template_event["event_type"] == "notification.template.created"
        assert template_event["template_id"] == template_id
        assert template_event["name"] == "Integration Test Template"
    
    async def test_update_template_success(
        self, http_client, db_pool, test_config
    ):
        """Test successful template update"""
        
        # Create template first
        template_request = NotificationTestDataFactory.make_create_template_request(
            name="Template to Update",
            type=NotificationType.EMAIL,
            subject="Original {{subject}}",
            content="Original content"
        )
        
        create_response = await http_client.post("/api/v1/notifications/templates", json=template_request.dict())
        template_id = create_response.json()["template"]["template_id"]
        
        # Update template
        update_request = {
            "name": "Updated Template Name",
            "subject": "Updated {{subject}}",
            "content": "Updated {{content}} with {{name}}",
            "variables": ["subject", "content", "name"]
        }
        
        response = await http_client.put(
            f"/api/v1/notifications/templates/{template_id}",
            json=update_request
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify update response
        updated_template = response_data["template"]
        assert updated_template["name"] == "Updated Template Name"
        assert updated_template["subject"] == "Updated {{subject}}"
        assert updated_template["content"] == "Updated {{content}} with {{name}}"
        assert updated_template["variables"] == ["subject", "content", "name"]
        assert updated_template["version"] > 1
        
        # Verify database update
        db_record = await db_pool.fetchrow("""
            SELECT name, subject, content, variables, version FROM notification.templates 
            WHERE template_id = $1
        """, template_id)
        
        assert db_record is not None
        assert db_record["name"] == "Updated Template Name"
        assert db_record["subject"] == "Updated {{subject}}"
        assert db_record["content"] == "Updated {{content}} with {{name}}"
        assert db_record["version"] > 1
    
    async def test_template_rendering_integration(
        self, http_client, db_pool, test_config
    ):
        """Test template rendering with variables"""
        
        # Create template with variables
        template_request = NotificationTestDataFactory.make_create_template_request(
            name="Rendering Test Template",
            type=NotificationType.EMAIL,
            subject="Order {{order_id}} Update",
            content="Hello {{customer_name}}, your order #{{order_id}} is {{status}}.",
            variables=["order_id", "customer_name", "status"]
        )
        
        create_response = await http_client.post("/api/v1/notifications/templates", json=template_request.dict())
        template_id = create_response.json()["template"]["template_id"]
        
        # Render template with variables
        render_request = {
            "template_id": template_id,
            "variables": {
                "order_id": "12345",
                "customer_name": "John Doe",
                "status": "shipped"
            }
        }
        
        response = await http_client.post("/api/v1/notifications/templates/render", json=render_request)
        
        assert response.status_code == 200
        render_data = response.json()
        
        # Verify rendered content
        assert render_data["success"] is True
        assert "rendered" in render_data
        rendered = render_data["rendered"]
        assert rendered["subject"] == "Order 12345 Update"
        assert rendered["content"] == "Hello John Doe, your order #12345 is shipped."
        assert rendered["variables_used"] == ["order_id", "customer_name", "status"]


class TestNotificationStatisticsIntegration:
    """Test notification statistics and analytics integration"""
    
    async def test_get_notification_statistics_success(
        self, http_client, db_pool, test_config
    ):
        """Test retrieving notification statistics"""
        
        # Create notifications of different types
        notification_types = [
            NotificationType.EMAIL,
            NotificationType.PUSH,
            NotificationType.IN_APP,
            NotificationType.EMAIL,
            NotificationType.PUSH
        ]
        
        for i, notif_type in enumerate(notification_types):
            notification_request = NotificationTestDataFactory.make_send_request(
                type=notif_type,
                recipient_email=f"stats{i}@example.com" if notif_type == NotificationType.EMAIL else None,
                recipient_id=test_config["test_user_id"] if notif_type != NotificationType.EMAIL else None,
                content=f"Stats notification {i}"
            )
            
            await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Get statistics
        response = await http_client.get("/api/v1/notifications/stats")
        
        assert response.status_code == 200
        stats_data = response.json()
        
        # Verify statistics structure
        assert "stats" in stats_data
        stats = stats_data["stats"]
        assert "total_sent" in stats
        assert "total_delivered" in stats
        assert "total_failed" in stats
        assert "by_type" in stats
        assert "by_status" in stats
        assert "period" in stats
        
        # Verify statistics accuracy
        assert stats["total_sent"] >= len(notification_types)
        assert stats["by_type"].get("email", 0) >= 2
        assert stats["by_type"].get("push", 0) >= 2
        assert stats["by_type"].get("in_app", 0) >= 1
    
    async def test_notification_delivery_tracking(
        self, http_client, db_pool, test_config
    ):
        """Test notification delivery status tracking"""
        
        # Send notification
        notification_request = NotificationTestDataFactory.make_send_request(
            type=NotificationType.EMAIL,
            recipient_email="tracking@example.com",
            content="Delivery tracking test"
        )
        
        send_response = await http_client.post("/api/v1/notifications/send", json=notification_request.dict())
        notification_id = send_response.json()["notification"]["notification_id"]
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Get notification details with delivery status
        response = await http_client.get(f"/api/v1/notifications/{notification_id}")
        
        assert response.status_code == 200
        notification_data = response.json()
        notification = notification_data["notification"]
        
        # Verify delivery tracking
        assert "delivery_status" in notification
        assert "delivered_at" in notification or "failed_at" in notification
        assert "delivery_attempts" in notification
        
        # Verify delivery attempts tracked
        if "delivery_attempts" in notification and notification["delivery_attempts"]:
            delivery_attempt = notification["delivery_attempts"][0]
            assert "attempted_at" in delivery_attempt
            assert "status" in delivery_attempt
            assert "provider" in delivery_attempt


class TestNotificationServiceHealthIntegration:
    """Test notification service health monitoring"""
    
    async def test_service_health_check_success(
        self, http_client, test_config
    ):
        """Test service health check endpoint"""
        
        response = await http_client.get("/health")
        
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
        
        # Verify component health checks
        checks = health_data["checks"]
        assert "database" in checks
        assert "nats" in checks
        assert "email_provider" in checks
        assert "push_provider" in checks
    
    async def test_service_readiness_check_success(
        self, http_client, test_config
    ):
        """Test service readiness check endpoint"""
        
        response = await http_client.get("/health/ready")
        
        assert response.status_code == 200
        readiness_data = response.json()
        
        # Verify readiness check structure
        assert "ready" in readiness_data
        assert "checks" in readiness_data
        assert readiness_data["ready"] is True
        
        # Verify all critical components ready
        checks = readiness_data["checks"]
        assert checks.get("database", {}).get("ready", False) is True
        assert checks.get("nats", {}).get("ready", False) is True


class TestErrorHandlingIntegration:
    """Test error handling and edge cases in integration scenarios"""
    
    async def test_invalid_notification_request_handling(
        self, http_client, test_config
    ):
        """Test handling of invalid notification requests"""
        
        # Test missing required fields
        invalid_request = {
            "type": "email"
            # Missing recipient_email or recipient_id
        }
        
        response = await http_client.post("/api/v1/notifications/send", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "error" in error_data
        assert "validation" in error_data["error"].lower()
    
    async def test_unauthorized_access_handling(
        self, http_client, test_config
    ):
        """Test handling of unauthorized access attempts"""
        
        # Try to access notifications without proper authentication
        response = await http_client.get("/api/v1/notifications")
        
        assert response.status_code == 401
        error_data = response.json()
        assert "error" in error_data
        assert "unauthorized" in error_data["error"].lower()
    
    async def test_rate_limiting_integration(
        self, http_client, test_config
    ):
        """Test rate limiting integration"""
        
        # Send multiple rapid requests
        requests = []
        for i in range(10):
            notification_request = NotificationTestDataFactory.make_send_request(
                type=NotificationType.EMAIL,
                recipient_email=f"ratelimit{i}@example.com",
                content=f"Rate limit test {i}"
            )
            
            request = http_client.post("/api/v1/notifications/send", json=notification_request.dict())
            requests.append(request)
        
        responses = await asyncio.gather(*requests, return_exceptions=True)
        
        # Should hit rate limit eventually
        rate_limited_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 429]
        assert len(rate_limited_responses) > 0
        
        rate_limited_response = rate_limited_responses[0]
        error_data = rate_limited_response.json()
        assert "error" in error_data
        assert "rate limit" in error_data["error"].lower()


# Integration test utilities
class NotificationIntegrationTestUtils:
    """Utilities for notification integration testing"""
    
    @staticmethod
    async def create_test_user(db_pool, user_id: str, email: str):
        """Create test user in database"""
        await db_pool.execute("""
            INSERT INTO users (user_id, email, created_at) 
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, email)
    
    @staticmethod
    async def wait_for_notification_event(nats_client, subject: str, timeout: float = 5.0):
        """Wait for specific notification event on NATS"""
        event_received = asyncio.Event()
        event_data = None
        
        async def handler(msg):
            nonlocal event_data
            event_data = json.loads(msg.data.decode())
            event_received.set()
        
        await nats_client.subscribe(subject, cb=handler)
        
        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            return event_data
        except asyncio.TimeoutError:
            return None
    
    @staticmethod
    async def verify_notification_delivery(db_pool, notification_id: str, expected_status: str):
        """Verify notification delivery status in database"""
        record = await db_pool.fetchrow("""
            SELECT status, delivered_at, failed_at, delivery_attempts
            FROM notification.notifications WHERE notification_id = $1
        """, notification_id)
        
        if record:
            return {
                "status": record["status"],
                "delivered_at": record["delivered_at"],
                "failed_at": record["failed_at"],
                "delivery_attempts": record["delivery_attempts"]
            }
        return None


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
