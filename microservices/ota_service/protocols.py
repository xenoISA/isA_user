"""
OTA Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class OTAServiceError(Exception):
    """Base exception for OTA service errors"""
    pass


class FirmwareNotFoundError(Exception):
    """Firmware not found"""
    pass


class CampaignNotFoundError(Exception):
    """Campaign not found"""
    pass


@runtime_checkable
class OTARepositoryProtocol(Protocol):
    """Interface for OTA Repository"""

    async def check_connection(self) -> bool: ...

    async def create_firmware(self, firmware_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_firmware_by_model_version(
        self, device_model: str, version: str,
    ) -> Optional[Dict[str, Any]]: ...

    async def list_firmware(
        self, device_model: Optional[str] = None, manufacturer: Optional[str] = None,
        is_beta: Optional[bool] = None, is_security_update: Optional[bool] = None,
        limit: int = 50, offset: int = 0,
    ) -> List[Dict[str, Any]]: ...

    async def update_firmware_stats(
        self, firmware_id: str, download_count_delta: int = 0,
        success_rate: Optional[float] = None,
    ) -> bool: ...

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_campaigns(
        self, status: Optional[str] = None, priority: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> List[Dict[str, Any]]: ...

    async def update_campaign_status(self, campaign_id: str, status: str, **kwargs) -> bool: ...

    async def create_device_update(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def get_device_update_by_id(self, update_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_device_updates(
        self, device_id: Optional[str] = None, campaign_id: Optional[str] = None,
        status: Optional[str] = None, limit: int = 50,
    ) -> List[Dict[str, Any]]: ...

    async def update_device_update_status(
        self, update_id: str, status: str,
        progress_percentage: Optional[float] = None,
        error_message: Optional[str] = None, **kwargs,
    ) -> bool: ...

    async def get_update_stats(self) -> Optional[Dict[str, Any]]: ...

    async def cancel_device_updates(self, device_id: str) -> int: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
