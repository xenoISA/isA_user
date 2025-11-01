"""
OTA Service - Business Logic

OTA更新服务业务逻辑，处理固件管理和设备更新
"""

import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import logging
import os
import sys

# Add parent directories to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .models import (
    UpdateType, UpdateStatus, DeploymentStrategy, Priority,
    FirmwareResponse, UpdateCampaignResponse, DeviceUpdateResponse,
    UpdateStatsResponse, RollbackResponse
)
from .ota_repository import OTARepository
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger("ota_service")


class OTAService:
    """OTA更新服务"""

    def __init__(self, event_bus=None):
        self.storage_path = "/var/ota/firmware"  # 固件存储路径 (legacy)
        self.max_file_size = 500 * 1024 * 1024  # 500MB
        self.supported_formats = ['.bin', '.hex', '.elf', '.tar.gz', '.zip']

        # Initialize repository and clients
        self.repository = OTARepository()
        self.device_client = None  # Will be initialized with async context
        self.storage_client = None
        self.notification_client = None
        self.event_bus = event_bus
        
    async def upload_firmware(self, user_id: str, firmware_data: Dict[str, Any], file_content: bytes) -> Optional[FirmwareResponse]:
        """上传固件文件"""
        try:
            # 验证文件大小
            if len(file_content) > self.max_file_size:
                raise ValueError("File size exceeds maximum limit")

            # 计算校验和
            actual_md5 = hashlib.md5(file_content).hexdigest()
            actual_sha256 = hashlib.sha256(file_content).hexdigest()

            # 如果提供了校验和，进行验证
            if "checksum_md5" in firmware_data and firmware_data["checksum_md5"]:
                if actual_md5 != firmware_data["checksum_md5"]:
                    raise ValueError("MD5 checksum mismatch")
            else:
                firmware_data["checksum_md5"] = actual_md5

            if "checksum_sha256" in firmware_data and firmware_data["checksum_sha256"]:
                if actual_sha256 != firmware_data["checksum_sha256"]:
                    raise ValueError("SHA256 checksum mismatch")
            else:
                firmware_data["checksum_sha256"] = actual_sha256

            # 生成固件ID
            firmware_id = self._generate_firmware_id(
                firmware_data.get("name", "firmware"),
                firmware_data.get("version", "1.0.0"),
                firmware_data.get("device_model", "unknown")
            )

            # Upload firmware binary to Storage Service (MinIO/S3)
            file_url = f"/api/v1/firmware/{firmware_id}/download"  # Default
            try:
                async with StorageServiceClient() as storage_client:
                    filename = f"{firmware_data.get('name', 'firmware')}_v{firmware_data.get('version', '1.0.0')}.bin"
                    storage_result = await storage_client.upload_firmware(
                        firmware_id=firmware_id,
                        file_content=file_content,
                        filename=filename,
                        user_id=user_id,
                        metadata={
                            "version": firmware_data.get("version"),
                            "device_model": firmware_data.get("device_model"),
                            "checksum_md5": actual_md5,
                            "checksum_sha256": actual_sha256
                        }
                    )

                    if storage_result and storage_result.get("download_url"):
                        file_url = storage_result["download_url"]
                        logger.info(f"Firmware binary uploaded to storage: {file_url}")
                    else:
                        logger.warning(f"Failed to upload to storage service, using local URL")
            except Exception as storage_error:
                logger.warning(f"Storage service error: {storage_error}, continuing with local storage")

            # Save firmware metadata to database using repository
            firmware_db_data = {
                "firmware_id": firmware_id,
                "name": firmware_data.get("name", "firmware"),
                "version": firmware_data.get("version", "1.0.0"),
                "description": firmware_data.get("description"),
                "device_model": firmware_data.get("device_model", "unknown"),
                "manufacturer": firmware_data.get("manufacturer", "unknown"),
                "min_hardware_version": firmware_data.get("min_hardware_version"),
                "max_hardware_version": firmware_data.get("max_hardware_version"),
                "file_size": len(file_content),
                "file_url": file_url,
                "checksum_md5": firmware_data["checksum_md5"],
                "checksum_sha256": firmware_data["checksum_sha256"],
                "tags": firmware_data.get("tags", []),
                "metadata": firmware_data.get("metadata", {}),
                "is_beta": firmware_data.get("is_beta", False),
                "is_security_update": firmware_data.get("is_security_update", False),
                "changelog": firmware_data.get("changelog"),
                "download_count": 0,
                "success_rate": 0.0,
                "created_by": user_id
            }

            db_result = await self.repository.create_firmware(firmware_db_data)
            if not db_result:
                logger.warning("Failed to save firmware to database")
                return None

            # Return FirmwareResponse
            firmware = FirmwareResponse(
                firmware_id=db_result["firmware_id"],
                name=db_result["name"],
                version=db_result["version"],
                description=db_result["description"],
                device_model=db_result["device_model"],
                manufacturer=db_result["manufacturer"],
                min_hardware_version=db_result["min_hardware_version"],
                max_hardware_version=db_result["max_hardware_version"],
                file_size=db_result["file_size"],
                file_url=db_result["file_url"],
                checksum_md5=db_result["checksum_md5"],
                checksum_sha256=db_result["checksum_sha256"],
                tags=db_result["tags"] or [],
                metadata=db_result["metadata"] or {},
                is_beta=db_result["is_beta"] or False,
                is_security_update=db_result["is_security_update"] or False,
                changelog=db_result["changelog"],
                download_count=db_result["download_count"] or 0,
                success_rate=float(db_result["success_rate"]) if db_result.get("success_rate") else 0.0,
                created_at=datetime.fromisoformat(db_result["created_at"].replace('Z', '+00:00')) if isinstance(db_result["created_at"], str) else db_result["created_at"],
                updated_at=datetime.fromisoformat(db_result["updated_at"].replace('Z', '+00:00')) if isinstance(db_result["updated_at"], str) else db_result["updated_at"],
                created_by=db_result["created_by"]
            )

            # Publish firmware.uploaded event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.FIRMWARE_UPLOADED,
                        source=ServiceSource.OTA_SERVICE,
                        data={
                            "firmware_id": firmware_id,
                            "name": firmware.name,
                            "version": firmware.version,
                            "device_model": firmware.device_model,
                            "file_size": firmware.file_size,
                            "is_security_update": firmware.is_security_update,
                            "uploaded_by": user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published firmware.uploaded event for firmware {firmware_id}")
                except Exception as e:
                    logger.error(f"Failed to publish firmware.uploaded event: {e}")

            logger.info(f"Firmware uploaded successfully: {firmware_id}")
            return firmware

        except Exception as e:
            logger.error(f"Error uploading firmware: {e}")
            return None
    
    async def create_update_campaign(self, user_id: str, campaign_data: Dict[str, Any]) -> Optional[UpdateCampaignResponse]:
        """创建更新活动"""
        try:
            campaign_id = secrets.token_hex(16)

            # 获取固件信息
            firmware = await self.get_firmware(campaign_data["firmware_id"])
            if not firmware:
                raise ValueError("Firmware not found")

            # 计算目标设备数量
            target_device_count = await self._calculate_target_devices(
                campaign_data.get("target_devices", []),
                campaign_data.get("target_groups", []),
                campaign_data.get("target_filters", {})
            )

            # Prepare campaign data for database
            campaign_db_data = {
                "campaign_id": campaign_id,
                "name": campaign_data["name"],
                "description": campaign_data.get("description"),
                "firmware_id": campaign_data["firmware_id"],
                "status": UpdateStatus.CREATED.value,
                "deployment_strategy": campaign_data.get("deployment_strategy", DeploymentStrategy.STAGED).value if hasattr(campaign_data.get("deployment_strategy", DeploymentStrategy.STAGED), 'value') else str(campaign_data.get("deployment_strategy", DeploymentStrategy.STAGED)),
                "priority": campaign_data.get("priority", Priority.NORMAL).value if hasattr(campaign_data.get("priority", Priority.NORMAL), 'value') else str(campaign_data.get("priority", Priority.NORMAL)),
                "target_device_count": target_device_count,
                "targeted_devices": campaign_data.get("target_devices", []),
                "targeted_groups": campaign_data.get("target_groups", []),
                "target_filters": campaign_data.get("target_filters", {}),
                "rollout_percentage": campaign_data.get("rollout_percentage", 100),
                "max_concurrent_updates": campaign_data.get("max_concurrent_updates", 10),
                "batch_size": campaign_data.get("batch_size", 50),
                "total_devices": target_device_count,
                "pending_devices": target_device_count,
                "in_progress_devices": 0,
                "completed_devices": 0,
                "failed_devices": 0,
                "cancelled_devices": 0,
                "scheduled_start": campaign_data.get("scheduled_start"),
                "scheduled_end": campaign_data.get("scheduled_end"),
                "timeout_minutes": campaign_data.get("timeout_minutes", 60),
                "auto_rollback": campaign_data.get("auto_rollback", True),
                "failure_threshold_percent": campaign_data.get("failure_threshold_percent", 20),
                "rollback_triggers": campaign_data.get("rollback_triggers", ["failure_rate"]),
                "requires_approval": campaign_data.get("requires_approval", False),
                "notify_on_start": campaign_data.get("notify_on_start", True),
                "notify_on_complete": campaign_data.get("notify_on_complete", True),
                "notify_on_failure": campaign_data.get("notify_on_failure", True),
                "notification_channels": campaign_data.get("notification_channels", []),
                "created_by": user_id
            }

            # Save campaign to database
            db_result = await self.repository.create_campaign(campaign_db_data)
            if not db_result:
                logger.error("Failed to save campaign to database")
                return None

            # Return UpdateCampaignResponse
            campaign = UpdateCampaignResponse(
                campaign_id=db_result["campaign_id"],
                name=db_result["name"],
                description=db_result["description"],
                firmware=firmware,
                status=UpdateStatus(db_result["status"]),
                deployment_strategy=DeploymentStrategy(db_result["deployment_strategy"]),
                priority=Priority(db_result["priority"]),
                target_device_count=db_result["target_device_count"],
                targeted_devices=db_result["targeted_devices"] or [],
                targeted_groups=db_result["targeted_groups"] or [],
                rollout_percentage=db_result["rollout_percentage"],
                max_concurrent_updates=db_result["max_concurrent_updates"],
                batch_size=db_result["batch_size"],
                total_devices=db_result["total_devices"],
                pending_devices=db_result["pending_devices"],
                in_progress_devices=db_result["in_progress_devices"],
                completed_devices=db_result["completed_devices"],
                failed_devices=db_result["failed_devices"],
                cancelled_devices=db_result["cancelled_devices"],
                scheduled_start=datetime.fromisoformat(db_result["scheduled_start"].replace('Z', '+00:00')) if db_result.get("scheduled_start") and isinstance(db_result["scheduled_start"], str) else db_result.get("scheduled_start"),
                scheduled_end=datetime.fromisoformat(db_result["scheduled_end"].replace('Z', '+00:00')) if db_result.get("scheduled_end") and isinstance(db_result["scheduled_end"], str) else db_result.get("scheduled_end"),
                actual_start=None,
                actual_end=None,
                timeout_minutes=db_result["timeout_minutes"],
                auto_rollback=db_result["auto_rollback"],
                failure_threshold_percent=db_result["failure_threshold_percent"],
                rollback_triggers=db_result["rollback_triggers"] or [],
                requires_approval=db_result.get("requires_approval", False),
                approved=db_result.get("approved"),
                approved_by=db_result.get("approved_by"),
                approval_comment=db_result.get("approval_comment"),
                created_at=datetime.fromisoformat(db_result["created_at"].replace('Z', '+00:00')) if isinstance(db_result["created_at"], str) else db_result["created_at"],
                updated_at=datetime.fromisoformat(db_result["updated_at"].replace('Z', '+00:00')) if isinstance(db_result["updated_at"], str) else db_result["updated_at"],
                created_by=db_result["created_by"]
            )

            # Publish campaign.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.CAMPAIGN_CREATED,
                        source=ServiceSource.OTA_SERVICE,
                        data={
                            "campaign_id": campaign_id,
                            "name": campaign.name,
                            "firmware_id": campaign.firmware.firmware_id,
                            "firmware_version": campaign.firmware.version,
                            "target_device_count": campaign.target_device_count,
                            "deployment_strategy": campaign.deployment_strategy.value,
                            "priority": campaign.priority.value,
                            "created_by": user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published campaign.created event for campaign {campaign_id}")
                except Exception as e:
                    logger.error(f"Failed to publish campaign.created event: {e}")

            logger.info(f"Update campaign created and saved to database: {campaign_id}")
            return campaign

        except Exception as e:
            logger.error(f"Error creating update campaign: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def start_campaign(self, campaign_id: str) -> bool:
        """启动更新活动"""
        try:
            # 获取活动信息
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                return False
            
            # 更新活动状态
            campaign.status = UpdateStatus.IN_PROGRESS
            campaign.actual_start = datetime.utcnow()
            
            # 开始分批更新设备
            await self._start_batch_updates(campaign)

            # Publish campaign.started event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.CAMPAIGN_STARTED,
                        source=ServiceSource.OTA_SERVICE,
                        data={
                            "campaign_id": campaign_id,
                            "name": campaign.name,
                            "firmware_id": campaign.firmware.firmware_id,
                            "firmware_version": campaign.firmware.version,
                            "target_device_count": campaign.target_device_count,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published campaign.started event for campaign {campaign_id}")
                except Exception as e:
                    logger.error(f"Failed to publish campaign.started event: {e}")

            logger.info(f"Update campaign started: {campaign_id}")
            return True

        except Exception as e:
            logger.error(f"Error starting campaign: {e}")
            return False
    
    async def update_single_device(self, device_id: str, update_data: Dict[str, Any]) -> Optional[DeviceUpdateResponse]:
        """更新单个设备"""
        try:
            update_id = secrets.token_hex(16)

            # 获取固件信息
            firmware = await self.get_firmware(update_data["firmware_id"])
            if not firmware:
                raise ValueError("Firmware not found")

            # Validate device exists via Device Service (microservices pattern)
            from_version = None
            try:
                async with DeviceServiceClient() as device_client:
                    device = await device_client.get_device(device_id)
                    if not device:
                        raise ValueError(f"Device '{device_id}' not found. Device must be registered in Device Service first.")

                    # Get current firmware version
                    from_version = await device_client.get_device_firmware_version(device_id)

                    # Optional: Check firmware compatibility
                    is_compatible = await device_client.check_firmware_compatibility(
                        device_id,
                        firmware.device_model,
                        firmware.min_hardware_version
                    )
                    if not is_compatible:
                        logger.warning(f"Firmware may not be compatible with device {device_id}")

            except Exception as e:
                logger.error(f"Device Service validation failed: {e}")
                # If Device Service is unavailable, proceed but log warning
                logger.warning(f"Proceeding with update without device validation (Device Service unavailable)")

            # Prepare data for database
            timeout_at = datetime.utcnow() + timedelta(minutes=update_data.get("timeout_minutes", 60))
            priority = update_data.get("priority", Priority.NORMAL)
            if isinstance(priority, str):
                priority = Priority(priority)

            # Only include fields that exist in device_updates table schema
            device_update_db_data = {
                "update_id": update_id,
                "device_id": device_id,
                "campaign_id": update_data.get("campaign_id"),
                "firmware_id": firmware.firmware_id,
                "status": UpdateStatus.SCHEDULED.value,
                "progress": 0.0,  # Changed from progress_percentage
                "scheduled_at": datetime.utcnow(),
                "started_at": None,
                "completed_at": None,
                "error_code": None,
                "error_message": None,
                "retry_count": 0,
                "metadata": {}  # Store extra info like priority, max_retries in metadata
            }

            # Save to database using repository
            db_result = await self.repository.create_device_update(device_update_db_data)
            if not db_result:
                logger.error("Failed to save device update to database")
                return None

            # Create response from database result, using defaults for fields not in schema
            device_update = DeviceUpdateResponse(
                update_id=db_result["update_id"],
                device_id=db_result["device_id"],
                campaign_id=db_result.get("campaign_id"),
                firmware=firmware,
                status=UpdateStatus(db_result["status"]),
                priority=priority,  # Use the priority variable from earlier in the method
                progress_percentage=float(db_result.get("progress", 0.0)),
                current_phase="scheduled",
                from_version=from_version,
                to_version=firmware.version,
                scheduled_at=db_result.get("scheduled_at"),
                started_at=db_result.get("started_at"),
                completed_at=db_result.get("completed_at"),
                timeout_at=timeout_at,
                error_code=db_result.get("error_code"),
                error_message=db_result.get("error_message"),
                retry_count=db_result.get("retry_count", 0),
                max_retries=update_data.get("max_retries", 3),
                download_size=firmware.file_size,
                download_progress=0.0,
                download_speed=None,
                signature_verified=None,
                checksum_verified=None,
                created_at=db_result["created_at"],
                updated_at=db_result["updated_at"]
            )

            # Start update process (can be async background task)
            # await self._start_device_update(device_update)

            logger.info(f"Device update created and saved: {update_id} for device {device_id}")
            return device_update

        except Exception as e:
            logger.error(f"Error updating device: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_update_progress(self, update_id: str) -> Optional[DeviceUpdateResponse]:
        """获取更新进度"""
        try:
            # Use repository to get device update
            data = await self.repository.get_device_update_by_id(update_id)

            if not data:
                return None

            # Get firmware information
            firmware = await self.get_firmware(data['firmware_id'])
            if not firmware:
                logger.error(f"Firmware not found for update {update_id}")
                return None

            # Note: device_updates table doesn't have all these fields in current schema
            # Using available fields only
            return DeviceUpdateResponse(
                update_id=data['update_id'],
                device_id=data['device_id'],
                campaign_id=data.get('campaign_id'),
                firmware=firmware,
                status=UpdateStatus(data['status']),
                priority=Priority.NORMAL,  # Default priority (not in current schema)
                progress_percentage=float(data.get('progress', 0.0)),
                current_phase=None,  # Not in current schema
                from_version=None,  # Not in current schema
                to_version=firmware.version,
                scheduled_at=data.get('scheduled_at'),
                started_at=data.get('started_at'),
                completed_at=data.get('completed_at'),
                timeout_at=None,  # Not in current schema
                error_code=data.get('error_code'),
                error_message=data.get('error_message'),
                retry_count=data.get('retry_count', 0),
                max_retries=3,  # Default
                download_size=None,  # Not in current schema
                download_progress=None,  # Not in current schema
                download_speed=None,  # Not in current schema
                signature_verified=None,  # Not in current schema
                checksum_verified=None,  # Not in current schema
                created_at=data['created_at'],
                updated_at=data['updated_at']
            )

        except Exception as e:
            logger.error(f"Error getting update progress {update_id}: {e}")
            return None
    
    async def cancel_update(self, update_id: str) -> bool:
        """取消更新"""
        try:
            # Get update info for event
            update = await self.get_update_progress(update_id)

            # 发送取消命令到设备
            # 更新状态为已取消

            # Publish update.cancelled event
            if self.event_bus and update:
                try:
                    event = Event(
                        event_type=EventType.UPDATE_CANCELLED,
                        source=ServiceSource.OTA_SERVICE,
                        data={
                            "update_id": update_id,
                            "device_id": update.device_id,
                            "firmware_id": update.firmware.firmware_id,
                            "firmware_version": update.firmware.version,
                            "campaign_id": update.campaign_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published update.cancelled event for update {update_id}")
                except Exception as e:
                    logger.error(f"Failed to publish update.cancelled event: {e}")

            logger.info(f"Update cancelled: {update_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling update: {e}")
            return False
    
    async def rollback_update(self, device_id: str, to_version: str) -> Optional[RollbackResponse]:
        """回滚更新"""
        try:
            rollback_id = secrets.token_hex(16)
            
            rollback = RollbackResponse(
                rollback_id=rollback_id,
                campaign_id="",  # 如果是活动回滚
                device_id=device_id,
                trigger="manual",
                reason="User requested rollback",
                from_version="1.1.0",  # 当前版本
                to_version=to_version,
                status=UpdateStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                completed_at=None,
                success=False,
                error_message=None
            )
            
            # 开始回滚过程
            await self._start_rollback_process(rollback)

            # Publish rollback.initiated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.ROLLBACK_INITIATED,
                        source=ServiceSource.OTA_SERVICE,
                        data={
                            "rollback_id": rollback_id,
                            "device_id": device_id,
                            "from_version": rollback.from_version,
                            "to_version": to_version,
                            "trigger": "manual",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published rollback.initiated event for rollback {rollback_id}")
                except Exception as e:
                    logger.error(f"Failed to publish rollback.initiated event: {e}")

            logger.info(f"Rollback started: {rollback_id} for device {device_id}")
            return rollback

        except Exception as e:
            logger.error(f"Error rolling back update: {e}")
            return None
    
    async def get_update_stats(self) -> Optional[UpdateStatsResponse]:
        """获取更新统计"""
        try:
            # Use repository to get stats
            repo_stats = await self.repository.get_update_stats()

            if not repo_stats:
                return None

            # Extract values from repository stats
            total_campaigns = repo_stats.get('total_campaigns', 0)
            active_campaigns = repo_stats.get('active_campaigns', 0)
            completed_campaigns = repo_stats.get('completed_campaigns', 0)
            failed_campaigns = repo_stats.get('failed_campaigns', 0)

            total_updates = repo_stats.get('total_device_updates', 0)
            pending_updates = repo_stats.get('pending_updates', 0)
            in_progress_updates = repo_stats.get('in_progress_updates', 0)
            completed_updates = repo_stats.get('completed_updates', 0)
            failed_updates = repo_stats.get('failed_updates', 0)

            # Calculate success rate
            if total_updates > 0:
                success_rate = (completed_updates / total_updates) * 100
            else:
                success_rate = 0.0

            total_data_transferred = repo_stats.get('total_bytes_downloaded', 0)

            # Get 24h stats (simplified - could be enhanced with time filters)
            last_24h_updates = min(total_updates, 89)  # Simplified for now
            last_24h_failures = min(failed_updates, 2)  # Simplified for now
            last_24h_data_transferred = min(total_data_transferred, 5 * 1024 * 1024 * 1024)  # Simplified for now

            stats = UpdateStatsResponse(
                total_campaigns=total_campaigns,
                active_campaigns=active_campaigns,
                completed_campaigns=completed_campaigns,
                failed_campaigns=failed_campaigns,
                total_updates=total_updates,
                pending_updates=pending_updates,
                in_progress_updates=in_progress_updates,
                completed_updates=completed_updates,
                failed_updates=failed_updates,
                success_rate=round(success_rate, 1),
                avg_update_time=12.5,  # Could calculate from update_history table
                total_data_transferred=total_data_transferred,
                last_24h_updates=last_24h_updates,
                last_24h_failures=last_24h_failures,
                last_24h_data_transferred=last_24h_data_transferred,
                updates_by_device_type={},  # Could be calculated with device service integration
                updates_by_firmware_version={}  # Could be calculated from firmware table
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting update stats: {e}")
            return None
    
    async def get_firmware(self, firmware_id: str) -> Optional[FirmwareResponse]:
        """获取固件信息"""
        try:
            data = await self.repository.get_firmware_by_id(firmware_id)
            if not data:
                return None

            return FirmwareResponse(
                firmware_id=data['firmware_id'],
                name=data['name'],
                version=data['version'],
                description=data['description'],
                device_model=data['device_model'],
                manufacturer=data['manufacturer'],
                min_hardware_version=data['min_hardware_version'],
                max_hardware_version=data['max_hardware_version'],
                file_size=data['file_size'],
                file_url=data['file_url'],
                checksum_md5=data['checksum_md5'],
                checksum_sha256=data['checksum_sha256'],
                tags=data['tags'] or [],
                metadata=data['metadata'] or {},
                is_beta=data['is_beta'] or False,
                is_security_update=data['is_security_update'] or False,
                changelog=data['changelog'],
                download_count=data['download_count'] or 0,
                success_rate=float(data['success_rate']) if data.get('success_rate') else 0.0,
                created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if isinstance(data['created_at'], str) else data['created_at'],
                updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if isinstance(data['updated_at'], str) else data['updated_at'],
                created_by=data['created_by']
            )

        except Exception as e:
            logger.error(f"Error getting firmware {firmware_id}: {e}")
            return None

    async def get_campaign(self, campaign_id: str) -> Optional[UpdateCampaignResponse]:
        """获取活动信息"""
        try:
            data = await self.repository.get_campaign_by_id(campaign_id)
            if not data:
                logger.info(f"Campaign not found: {campaign_id}")
                return None

            # Get firmware information
            firmware = await self.get_firmware(data['firmware_id'])
            if not firmware:
                logger.error(f"Firmware not found for campaign {campaign_id}")
                return None

            # Map available fields from database, use defaults for missing fields
            return UpdateCampaignResponse(
                campaign_id=data['campaign_id'],
                name=data['name'],
                description=data.get('description'),
                firmware=firmware,
                status=UpdateStatus(data['status']),
                deployment_strategy=DeploymentStrategy(data.get('deployment_strategy', 'staged')),
                priority=Priority(data.get('priority', 'normal')),
                target_device_count=len(data.get('target_devices', [])),
                targeted_devices=data.get('target_devices', []),
                targeted_groups=data.get('targeted_groups', []),
                rollout_percentage=data.get('rollout_percentage', 100),
                max_concurrent_updates=data.get('max_concurrent_updates', 10),
                batch_size=data.get('batch_size', 50),
                total_devices=len(data.get('target_devices', [])),
                pending_devices=len(data.get('target_devices', [])),
                in_progress_devices=0,
                completed_devices=0,
                failed_devices=0,
                cancelled_devices=0,
                scheduled_start=data.get('start_time'),
                scheduled_end=data.get('end_time'),
                actual_start=None,
                actual_end=None,
                timeout_minutes=60,
                auto_rollback=data.get('auto_rollback', True),
                failure_threshold_percent=int(data.get('rollback_threshold', 10)),
                rollback_triggers=[],
                requires_approval=False,
                approved=None,
                approved_by=None,
                approval_comment=None,
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                created_by=data['created_by']
            )

        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # Private helper methods
    
    def _generate_firmware_id(self, name: str, version: str, model: str) -> str:
        """生成固件ID - 基于 name:version:model 的确定性哈希"""
        # Use deterministic hash without timestamp so same firmware gets same ID
        unique_string = f"{name}:{version}:{model}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]
    
    async def _calculate_target_devices(self, device_ids: List[str], group_ids: List[str], filters: Dict[str, Any]) -> int:
        """计算目标设备数量"""
        # 实际应该查询设备管理服务
        return len(device_ids) + len(group_ids) * 20  # 模拟计算
    
    async def _start_batch_updates(self, campaign: UpdateCampaignResponse):
        """开始分批更新"""
        try:
            # 实现分批更新逻辑
            batch_size = campaign.batch_size
            # 分批处理设备更新
            logger.info(f"Starting batch updates for campaign {campaign.campaign_id}")
        except Exception as e:
            logger.error(f"Error in batch updates: {e}")
    
    async def _start_device_update(self, device_update: DeviceUpdateResponse):
        """开始设备更新过程"""
        try:
            # 实现设备更新流程
            # 1. 下载固件
            # 2. 验证签名和校验和
            # 3. 安装固件
            # 4. 重启设备
            # 5. 验证更新结果
            
            device_update.status = UpdateStatus.IN_PROGRESS
            device_update.started_at = datetime.utcnow()
            device_update.current_phase = "downloading"
            
            logger.info(f"Device update process started: {device_update.update_id}")
        except Exception as e:
            logger.error(f"Error in device update process: {e}")
    
    async def _start_rollback_process(self, rollback: RollbackResponse):
        """开始回滚过程"""
        try:
            # 实现回滚逻辑
            logger.info(f"Rollback process started: {rollback.rollback_id}")
        except Exception as e:
            logger.error(f"Error in rollback process: {e}")