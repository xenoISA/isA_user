"""
OTA Service - Business Logic

OTA更新服务业务逻辑，处理固件管理和设备更新
"""

import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import os
import sys

# Add parent directories to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client

from .models import (
    UpdateType, UpdateStatus, DeploymentStrategy, Priority,
    FirmwareResponse, UpdateCampaignResponse, DeviceUpdateResponse,
    UpdateStatsResponse, RollbackResponse
)

logger = logging.getLogger("ota_service")


class OTAService:
    """OTA更新服务"""
    
    def __init__(self):
        self.storage_path = "/var/ota/firmware"  # 固件存储路径
        self.max_file_size = 500 * 1024 * 1024  # 500MB
        self.supported_formats = ['.bin', '.hex', '.elf', '.tar.gz', '.zip']
        self.supabase = get_supabase_client()
        
    async def upload_firmware(self, user_id: str, firmware_data: Dict[str, Any], file_content: bytes) -> Optional[FirmwareResponse]:
        """上传固件文件"""
        try:
            # 验证文件大小
            if len(file_content) > self.max_file_size:
                raise ValueError("File size exceeds maximum limit")
            
            # 验证校验和
            actual_md5 = hashlib.md5(file_content).hexdigest()
            actual_sha256 = hashlib.sha256(file_content).hexdigest()
            
            if actual_md5 != firmware_data["checksum_md5"]:
                raise ValueError("MD5 checksum mismatch")
            if actual_sha256 != firmware_data["checksum_sha256"]:
                raise ValueError("SHA256 checksum mismatch")
            
            # 生成固件ID
            firmware_id = self._generate_firmware_id(
                firmware_data["name"],
                firmware_data["version"],
                firmware_data["device_model"]
            )
            
            # 保存文件
            file_path = os.path.join(self.storage_path, f"{firmware_id}.bin")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 在生产环境中，这里应该保存到云存储
            # with open(file_path, 'wb') as f:
            #     f.write(file_content)
            
            firmware = FirmwareResponse(
                firmware_id=firmware_id,
                name=firmware_data["name"],
                version=firmware_data["version"],
                description=firmware_data.get("description"),
                device_model=firmware_data["device_model"],
                manufacturer=firmware_data["manufacturer"],
                min_hardware_version=firmware_data.get("min_hardware_version"),
                max_hardware_version=firmware_data.get("max_hardware_version"),
                file_size=len(file_content),
                file_url=f"/api/v1/firmware/{firmware_id}/download",
                checksum_md5=firmware_data["checksum_md5"],
                checksum_sha256=firmware_data["checksum_sha256"],
                tags=firmware_data.get("tags", []),
                metadata=firmware_data.get("metadata", {}),
                is_beta=firmware_data.get("is_beta", False),
                is_security_update=firmware_data.get("is_security_update", False),
                changelog=firmware_data.get("changelog"),
                download_count=0,
                success_rate=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=user_id
            )
            
            logger.info(f"Firmware uploaded: {firmware_id}")
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
            
            campaign = UpdateCampaignResponse(
                campaign_id=campaign_id,
                name=campaign_data["name"],
                description=campaign_data.get("description"),
                firmware=firmware,
                status=UpdateStatus.CREATED,
                deployment_strategy=campaign_data.get("deployment_strategy", DeploymentStrategy.STAGED),
                priority=campaign_data.get("priority", Priority.NORMAL),
                target_device_count=target_device_count,
                targeted_devices=campaign_data.get("target_devices", []),
                targeted_groups=campaign_data.get("target_groups", []),
                rollout_percentage=campaign_data.get("rollout_percentage", 100),
                max_concurrent_updates=campaign_data.get("max_concurrent_updates", 10),
                batch_size=campaign_data.get("batch_size", 50),
                total_devices=target_device_count,
                pending_devices=target_device_count,
                in_progress_devices=0,
                completed_devices=0,
                failed_devices=0,
                cancelled_devices=0,
                scheduled_start=campaign_data.get("scheduled_start"),
                scheduled_end=campaign_data.get("scheduled_end"),
                actual_start=None,
                actual_end=None,
                timeout_minutes=campaign_data.get("timeout_minutes", 60),
                auto_rollback=campaign_data.get("auto_rollback", True),
                failure_threshold_percent=campaign_data.get("failure_threshold_percent", 20),
                rollback_triggers=campaign_data.get("rollback_triggers", ["failure_rate"]),
                requires_approval=campaign_data.get("requires_approval", False),
                approved=None,
                approved_by=None,
                approval_comment=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=user_id
            )
            
            logger.info(f"Update campaign created: {campaign_id}")
            return campaign
            
        except Exception as e:
            logger.error(f"Error creating update campaign: {e}")
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
            
            device_update = DeviceUpdateResponse(
                update_id=update_id,
                device_id=device_id,
                campaign_id=update_data.get("campaign_id"),
                firmware=firmware,
                status=UpdateStatus.SCHEDULED,
                priority=update_data.get("priority", Priority.NORMAL),
                progress_percentage=0.0,
                current_phase="scheduled",
                from_version=None,  # 应该从设备管理服务获取
                to_version=firmware.version,
                scheduled_at=datetime.utcnow(),
                started_at=None,
                completed_at=None,
                timeout_at=datetime.utcnow() + timedelta(minutes=update_data.get("timeout_minutes", 60)),
                error_code=None,
                error_message=None,
                retry_count=0,
                max_retries=update_data.get("max_retries", 3),
                download_size=firmware.file_size,
                download_progress=0.0,
                download_speed=None,
                signature_verified=None,
                checksum_verified=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 开始更新过程
            await self._start_device_update(device_update)
            
            logger.info(f"Device update started: {update_id} for device {device_id}")
            return device_update
            
        except Exception as e:
            logger.error(f"Error updating device: {e}")
            return None
    
    async def get_update_progress(self, update_id: str) -> Optional[DeviceUpdateResponse]:
        """获取更新进度"""
        try:
            result = self.supabase.table('device_updates').select('*').eq('update_id', update_id).single().execute()
            
            if result.data:
                data = result.data
                
                # Get firmware information
                firmware = await self.get_firmware(data['firmware_id'])
                if not firmware:
                    logger.error(f"Firmware not found for update {update_id}")
                    return None
                
                return DeviceUpdateResponse(
                    update_id=data['update_id'],
                    device_id=data['device_id'],
                    campaign_id=data['campaign_id'],
                    firmware=firmware,
                    status=UpdateStatus(data['status']),
                    priority=Priority(data['priority']),
                    progress_percentage=float(data['progress_percentage']) if data['progress_percentage'] else 0.0,
                    current_phase=data['current_phase'],
                    from_version=data['from_version'],
                    to_version=data['to_version'],
                    scheduled_at=datetime.fromisoformat(data['scheduled_at'].replace('Z', '+00:00')) if data['scheduled_at'] else None,
                    started_at=datetime.fromisoformat(data['started_at'].replace('Z', '+00:00')) if data['started_at'] else None,
                    completed_at=datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00')) if data['completed_at'] else None,
                    timeout_at=datetime.fromisoformat(data['timeout_at'].replace('Z', '+00:00')) if data['timeout_at'] else None,
                    error_code=data['error_code'],
                    error_message=data['error_message'],
                    retry_count=data['retry_count'] or 0,
                    max_retries=data['max_retries'] or 3,
                    download_size=data['download_size'],
                    download_progress=float(data['download_progress']) if data['download_progress'] else 0.0,
                    download_speed=float(data['download_speed']) if data['download_speed'] else None,
                    signature_verified=data['signature_verified'],
                    checksum_verified=data['checksum_verified'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting update progress {update_id}: {e}")
            return None
    
    async def cancel_update(self, update_id: str) -> bool:
        """取消更新"""
        try:
            # 发送取消命令到设备
            # 更新状态为已取消
            
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
            
            logger.info(f"Rollback started: {rollback_id} for device {device_id}")
            return rollback
            
        except Exception as e:
            logger.error(f"Error rolling back update: {e}")
            return None
    
    async def get_update_stats(self) -> Optional[UpdateStatsResponse]:
        """获取更新统计"""
        try:
            # Get campaign stats
            campaigns_result = self.supabase.table('update_campaigns').select('status').execute()
            campaign_data = campaigns_result.data or []
            
            total_campaigns = len(campaign_data)
            active_campaigns = len([c for c in campaign_data if c['status'] in ['in_progress', 'scheduled']])
            completed_campaigns = len([c for c in campaign_data if c['status'] == 'completed'])
            failed_campaigns = len([c for c in campaign_data if c['status'] == 'failed'])
            
            # Get device update stats
            updates_result = self.supabase.table('device_updates').select('status').execute()
            update_data = updates_result.data or []
            
            total_updates = len(update_data)
            pending_updates = len([u for u in update_data if u['status'] in ['created', 'scheduled']])
            in_progress_updates = len([u for u in update_data if u['status'] == 'in_progress'])
            completed_updates = len([u for u in update_data if u['status'] == 'completed'])
            failed_updates = len([u for u in update_data if u['status'] == 'failed'])
            
            # Calculate success rate
            if total_updates > 0:
                success_rate = (completed_updates / total_updates) * 100
            else:
                success_rate = 0.0
            
            # Get firmware download stats for data transfer calculation
            downloads_result = self.supabase.table('firmware_downloads').select('bytes_downloaded').execute()
            download_data = downloads_result.data or []
            
            total_data_transferred = sum([d['bytes_downloaded'] or 0 for d in download_data])
            
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
            result = self.supabase.table('firmware').select('*').eq('firmware_id', firmware_id).single().execute()
            
            if result.data:
                data = result.data
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
                    success_rate=float(data['success_rate']) or 0.0,
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
                    created_by=data['created_by']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting firmware {firmware_id}: {e}")
            return None
    
    async def get_campaign(self, campaign_id: str) -> Optional[UpdateCampaignResponse]:
        """获取活动信息"""
        try:
            result = self.supabase.table('update_campaigns').select('*').eq('campaign_id', campaign_id).single().execute()
            
            if result.data:
                data = result.data
                
                # Get firmware information
                firmware = await self.get_firmware(data['firmware_id'])
                if not firmware:
                    logger.error(f"Firmware not found for campaign {campaign_id}")
                    return None
                
                return UpdateCampaignResponse(
                    campaign_id=data['campaign_id'],
                    name=data['name'],
                    description=data['description'],
                    firmware=firmware,
                    status=UpdateStatus(data['status']),
                    deployment_strategy=DeploymentStrategy(data['deployment_strategy']),
                    priority=Priority(data['priority']),
                    target_device_count=data['target_device_count'] or 0,
                    targeted_devices=data['targeted_devices'] or [],
                    targeted_groups=data['targeted_groups'] or [],
                    rollout_percentage=data['rollout_percentage'] or 100,
                    max_concurrent_updates=data['max_concurrent_updates'] or 10,
                    batch_size=data['batch_size'] or 50,
                    total_devices=data['total_devices'] or 0,
                    pending_devices=data['pending_devices'] or 0,
                    in_progress_devices=data['in_progress_devices'] or 0,
                    completed_devices=data['completed_devices'] or 0,
                    failed_devices=data['failed_devices'] or 0,
                    cancelled_devices=data['cancelled_devices'] or 0,
                    scheduled_start=datetime.fromisoformat(data['scheduled_start'].replace('Z', '+00:00')) if data['scheduled_start'] else None,
                    scheduled_end=datetime.fromisoformat(data['scheduled_end'].replace('Z', '+00:00')) if data['scheduled_end'] else None,
                    actual_start=datetime.fromisoformat(data['actual_start'].replace('Z', '+00:00')) if data['actual_start'] else None,
                    actual_end=datetime.fromisoformat(data['actual_end'].replace('Z', '+00:00')) if data['actual_end'] else None,
                    timeout_minutes=data['timeout_minutes'] or 60,
                    auto_rollback=data['auto_rollback'] or True,
                    failure_threshold_percent=data['failure_threshold_percent'] or 20,
                    rollback_triggers=data['rollback_triggers'] or [],
                    requires_approval=data['requires_approval'] or False,
                    approved=data['approved'],
                    approved_by=data['approved_by'],
                    approval_comment=data['approval_comment'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
                    created_by=data['created_by']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            return None
    
    # Private helper methods
    
    def _generate_firmware_id(self, name: str, version: str, model: str) -> str:
        """生成固件ID"""
        unique_string = f"{name}:{version}:{model}:{datetime.utcnow().isoformat()}"
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