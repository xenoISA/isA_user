"""
Audit Service Client

Client library for other microservices to interact with audit service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditServiceClient:
    """Audit Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Audit Service client

        Args:
            base_url: Audit service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("audit_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8204"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Audit Event Logging
    # =============================================================================

    async def log_event(
        self,
        event_type: str,
        category: str,
        action: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        severity: str = "low",
        status: str = "success",
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Log an audit event

        Args:
            event_type: Type of event (user_login, resource_create, etc.)
            category: Event category (authentication, authorization, etc.)
            action: Action description
            user_id: User ID (optional)
            session_id: Session ID (optional)
            organization_id: Organization ID (optional)
            resource_type: Resource type (optional)
            resource_id: Resource ID (optional)
            resource_name: Resource name (optional)
            severity: Event severity (low, medium, high, critical)
            status: Event status (success, failure, pending, error)
            description: Event description (optional)
            ip_address: Client IP address (optional)
            user_agent: User agent string (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created audit event

        Example:
            >>> client = AuditServiceClient()
            >>> event = await client.log_event(
            ...     event_type="user_login",
            ...     category="authentication",
            ...     action="User login successful",
            ...     user_id="user123",
            ...     severity="low",
            ...     status="success"
            ... )
        """
        try:
            event_data = {
                "event_type": event_type,
                "category": category,
                "action": action,
                "severity": severity,
                "status": status
            }

            if user_id:
                event_data["user_id"] = user_id
            if session_id:
                event_data["session_id"] = session_id
            if organization_id:
                event_data["organization_id"] = organization_id
            if resource_type:
                event_data["resource_type"] = resource_type
            if resource_id:
                event_data["resource_id"] = resource_id
            if resource_name:
                event_data["resource_name"] = resource_name
            if description:
                event_data["description"] = description
            if ip_address:
                event_data["ip_address"] = ip_address
            if user_agent:
                event_data["user_agent"] = user_agent
            if metadata:
                event_data["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/audit/events",
                json=event_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to log audit event: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
            return None

    async def log_batch_events(
        self,
        events: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Log multiple audit events in batch

        Args:
            events: List of event dictionaries

        Returns:
            Batch log result

        Example:
            >>> events = [
            ...     {
            ...         "event_type": "user_login",
            ...         "category": "authentication",
            ...         "action": "Login",
            ...         "user_id": "user1"
            ...     },
            ...     {
            ...         "event_type": "resource_create",
            ...         "category": "data_access",
            ...         "action": "Created file",
            ...         "user_id": "user1"
            ...     }
            ... ]
            >>> result = await client.log_batch_events(events)
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/audit/events/batch",
                json={"events": events}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to log batch events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error logging batch events: {e}")
            return None

    # =============================================================================
    # Audit Event Querying
    # =============================================================================

    async def query_events(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Query audit events with filters

        Args:
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            event_types: Filter by event types
            categories: Filter by categories
            severities: Filter by severities
            statuses: Filter by statuses
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            Query results with events and metadata

        Example:
            >>> result = await client.query_events(
            ...     user_id="user123",
            ...     event_types=["user_login", "user_logout"],
            ...     limit=50
            ... )
            >>> for event in result['events']:
            ...     print(f"{event['timestamp']}: {event['action']}")
        """
        try:
            query_data = {
                "limit": limit,
                "offset": offset
            }

            if user_id:
                query_data["user_id"] = user_id
            if organization_id:
                query_data["organization_id"] = organization_id
            if event_types:
                query_data["event_types"] = event_types
            if categories:
                query_data["categories"] = categories
            if severities:
                query_data["severities"] = severities
            if statuses:
                query_data["statuses"] = statuses
            if resource_type:
                query_data["resource_type"] = resource_type
            if resource_id:
                query_data["resource_id"] = resource_id
            if start_time:
                query_data["start_time"] = start_time.isoformat()
            if end_time:
                query_data["end_time"] = end_time.isoformat()

            response = await self.client.post(
                f"{self.base_url}/api/v1/audit/events/query",
                json=query_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to query events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error querying events: {e}")
            return None

    # =============================================================================
    # User Activity Tracking
    # =============================================================================

    async def get_user_activities(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get user activity history

        Args:
            user_id: User ID
            limit: Maximum results
            offset: Result offset

        Returns:
            User activities

        Example:
            >>> activities = await client.get_user_activities("user123", limit=50)
            >>> for activity in activities['events']:
            ...     print(f"{activity['action']} at {activity['timestamp']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/audit/users/{user_id}/activities",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user activities: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return None

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Get user activity summary

        Args:
            user_id: User ID
            days: Number of days to summarize

        Returns:
            Activity summary statistics

        Example:
            >>> summary = await client.get_user_activity_summary("user123", days=7)
            >>> print(f"Total events: {summary['total_events']}")
            >>> print(f"Login count: {summary['login_count']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/audit/users/{user_id}/summary",
                params={"days": days}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get activity summary: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return None

    # =============================================================================
    # Security & Compliance
    # =============================================================================

    async def create_security_alert(
        self,
        alert_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a security alert

        Args:
            alert_type: Type of security alert
            severity: Alert severity
            description: Alert description
            user_id: Related user ID (optional)
            resource_id: Related resource ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created alert

        Example:
            >>> alert = await client.create_security_alert(
            ...     alert_type="suspicious_login",
            ...     severity="high",
            ...     description="Multiple failed login attempts",
            ...     user_id="user123"
            ... )
        """
        try:
            alert_data = {
                "alert_type": alert_type,
                "severity": severity,
                "description": description
            }

            if user_id:
                alert_data["user_id"] = user_id
            if resource_id:
                alert_data["resource_id"] = resource_id
            if metadata:
                alert_data["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/audit/security/alerts",
                json=alert_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create security alert: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating security alert: {e}")
            return None

    async def get_security_events(
        self,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get security events

        Args:
            severity: Filter by severity
            limit: Maximum results

        Returns:
            List of security events

        Example:
            >>> events = await client.get_security_events(severity="high", limit=20)
        """
        try:
            params = {"limit": limit}
            if severity:
                params["severity"] = severity

            response = await self.client.get(
                f"{self.base_url}/api/v1/audit/security/events",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get security events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            return None

    async def generate_compliance_report(
        self,
        report_type: str,
        standard: str,
        start_date: datetime,
        end_date: datetime,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate compliance report

        Args:
            report_type: Type of compliance report
            standard: Compliance standard (GDPR, HIPAA, etc.)
            start_date: Report start date
            end_date: Report end date
            organization_id: Organization ID (optional)

        Returns:
            Generated compliance report

        Example:
            >>> report = await client.generate_compliance_report(
            ...     report_type="data_access",
            ...     standard="GDPR",
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 12, 31)
            ... )
        """
        try:
            report_data = {
                "report_type": report_type,
                "standard": standard,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }

            if organization_id:
                report_data["organization_id"] = organization_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/audit/compliance/reports",
                json=report_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to generate compliance report: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return None

    # =============================================================================
    # Service Information
    # =============================================================================

    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get audit service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_service_stats()
            >>> print(f"Total events: {stats['total_events']}")
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/audit/stats")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get service stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["AuditServiceClient"]
