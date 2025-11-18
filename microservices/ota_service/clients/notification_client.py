"""
Notification Service Client for OTA Service

HTTP client for synchronous communication with notification_service
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class NotificationClient:
    """Client for notification_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Notification Service client

        Args:
            base_url: Notification service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("notification_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8209"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"NotificationClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def send_campaign_notification(
        self,
        user_ids: List[str],
        campaign_data: Dict[str, Any]
    ) -> bool:
        """
        Send campaign notification to users

        Args:
            user_ids: List of user IDs to notify
            campaign_data: Campaign information

        Returns:
            True if successful
        """
        try:
            payload = {
                "user_ids": user_ids,
                "notification_type": "ota_campaign",
                "title": f"OTA Campaign: {campaign_data.get('name', 'Update Available')}",
                "message": f"A new firmware update campaign has been created for {campaign_data.get('device_count', 0)} devices",
                "data": campaign_data,
                "channels": ["push", "email"],
                "priority": campaign_data.get('priority', 'normal')
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/send",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Campaign notification sent to {len(user_ids)} users")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send campaign notification: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error sending campaign notification: {e}")
            return False

    async def send_update_notification(
        self,
        device_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Send update notification for device

        Args:
            device_id: Device ID
            update_data: Update information

        Returns:
            True if successful
        """
        try:
            payload = {
                "device_id": device_id,
                "notification_type": "ota_update",
                "title": "Firmware Update Available",
                "message": f"Firmware version {update_data.get('version', 'unknown')} is ready to install",
                "data": update_data,
                "channels": ["push"],
                "priority": update_data.get('priority', 'normal')
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/device/{device_id}",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Update notification sent to device {device_id}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send update notification: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error sending update notification: {e}")
            return False

    async def send_alert(
        self,
        user_ids: List[str],
        alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send alert notification

        Args:
            user_ids: List of user IDs to notify
            alert_data: Alert information

        Returns:
            True if successful
        """
        try:
            payload = {
                "user_ids": user_ids,
                "notification_type": "ota_alert",
                "title": alert_data.get('title', 'OTA Alert'),
                "message": alert_data.get('message', 'An OTA alert has occurred'),
                "data": alert_data,
                "channels": ["push", "email", "sms"],
                "priority": "high"
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/alert",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Alert sent to {len(user_ids)} users")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send alert: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    async def send_rollback_notification(
        self,
        device_id: str,
        rollback_data: Dict[str, Any]
    ) -> bool:
        """
        Send rollback notification

        Args:
            device_id: Device ID
            rollback_data: Rollback information

        Returns:
            True if successful
        """
        try:
            payload = {
                "device_id": device_id,
                "notification_type": "ota_rollback",
                "title": "Firmware Rollback Initiated",
                "message": f"Firmware is being rolled back from {rollback_data.get('from_version')} to {rollback_data.get('to_version')}",
                "data": rollback_data,
                "channels": ["push"],
                "priority": "high"
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/device/{device_id}",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Rollback notification sent to device {device_id}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send rollback notification: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error sending rollback notification: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if notification service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
