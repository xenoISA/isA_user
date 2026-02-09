"""
MQTT Channel Implementation for Notification Service

This module provides MQTT notification delivery by calling the gateway's
MQTT publish endpoint. The gateway then publishes to the MQTT broker.

Flow:
    notification_service → HTTP → gateway → MQTT → user's app
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class MQTTChannel:
    """
    MQTT notification channel that publishes notifications via gateway.

    This is an HTTP client that forwards notifications to the gateway,
    which then publishes them to the MQTT broker.
    """

    def __init__(self, gateway_url: str):
        """
        Initialize MQTT channel

        Args:
            gateway_url: Base URL of the gateway service
        """
        self.gateway_url = gateway_url
        self.mqtt_endpoint = f"{gateway_url}/api/v1/mqtt/publish/notification"
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"MQTT Channel initialized with gateway: {gateway_url}")

    async def send_notification(
        self,
        notification_type: str,
        notification_data: Dict[str, Any],
        user_id: Optional[str] = None,
        system_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification via MQTT through gateway

        Args:
            notification_type: "user", "broadcast", or "system"
            notification_data: Notification payload with title, message, etc.
            user_id: Target user ID (required for type="user")
            system_id: Target system ID (required for type="system")
            auth_token: Optional JWT token for authentication

        Returns:
            Dict with success status and response data
        """
        payload = {
            "type": notification_type,
            "notification": notification_data
        }

        if notification_type == "user" and user_id:
            payload["user_id"] = user_id
        elif notification_type == "system" and system_id:
            payload["system_id"] = system_id

        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            logger.debug(f"Sending {notification_type} notification via gateway")
            response = await self.client.post(
                self.mqtt_endpoint,
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"MQTT notification sent successfully: {notification_type}")
            return {
                "success": True,
                "mqtt_response": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending MQTT notification: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "timestamp": datetime.utcnow().isoformat()
            }
        except httpx.RequestError as e:
            logger.error(f"Request error sending MQTT notification: {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def send_user_notification(
        self,
        user_id: str,
        notification: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to specific user via MQTT

        Args:
            user_id: Target user ID
            notification: Notification data (title, message, priority, etc.)
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        return await self.send_notification(
            notification_type="user",
            notification_data=notification,
            user_id=user_id,
            auth_token=auth_token
        )

    async def send_broadcast_notification(
        self,
        notification: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send broadcast notification to all users via MQTT

        Args:
            notification: Notification data
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        return await self.send_notification(
            notification_type="broadcast",
            notification_data=notification,
            auth_token=auth_token
        )

    async def send_system_notification(
        self,
        system_id: str,
        notification: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to specific system via MQTT

        Args:
            system_id: Target system ID
            notification: Notification data
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        return await self.send_notification(
            notification_type="system",
            notification_data=notification,
            system_id=system_id,
            auth_token=auth_token
        )

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()
        logger.info("MQTT Channel closed")


# Global MQTT channel instance (singleton pattern)
_mqtt_channel: Optional[MQTTChannel] = None


def get_mqtt_channel(gateway_url: Optional[str] = None) -> MQTTChannel:
    """
    Get or create global MQTT channel instance

    Args:
        gateway_url: Gateway service URL

    Returns:
        MQTTChannel instance
    """
    global _mqtt_channel
    if _mqtt_channel is None:
        _mqtt_channel = MQTTChannel(gateway_url=gateway_url)
    return _mqtt_channel


async def close_mqtt_channel():
    """Close and cleanup global MQTT channel instance"""
    global _mqtt_channel
    if _mqtt_channel is not None:
        await _mqtt_channel.close()
        _mqtt_channel = None
