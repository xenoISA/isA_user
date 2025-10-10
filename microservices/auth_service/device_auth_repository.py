"""
Device Authentication Repository

设备认证数据访问层
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
import json
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class DeviceAuthRepository:
    """设备认证数据访问层"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def create_device_credential(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建设备凭证"""
        try:
            result = self.supabase.table('device_credentials').insert({
                'device_id': device_data['device_id'],
                'device_secret': device_data['device_secret'],
                'organization_id': device_data['organization_id'],
                'device_name': device_data.get('device_name'),
                'device_type': device_data.get('device_type'),
                'status': device_data.get('status', 'active'),
                'metadata': device_data.get('metadata', {}),
                'expires_at': device_data.get('expires_at'),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating device credential: {e}")
            return None
    
    async def get_device_credential(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备凭证"""
        try:
            result = self.supabase.table('device_credentials').select('*').eq(
                'device_id', device_id
            ).eq('status', 'active').execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting device credential: {e}")
            return None
    
    async def verify_device_credential(self, device_id: str, device_secret: str) -> Optional[Dict[str, Any]]:
        """验证设备凭证"""
        try:
            # 获取设备凭证
            result = self.supabase.table('device_credentials').select('*').eq(
                'device_id', device_id
            ).eq('device_secret', device_secret).eq('status', 'active').execute()
            
            if result.data:
                device = result.data[0]
                
                # 检查是否过期
                if device.get('expires_at'):
                    expires_at = device['expires_at']
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expires_at < datetime.now(timezone.utc):
                        await self._log_auth_attempt(device_id, 'failed', 
                                              error='Device credential expired')
                        return None
                
                # 更新认证信息
                auth_count = device.get('authentication_count', 0) + 1
                self.supabase.table('device_credentials').update({
                    'last_authenticated_at': datetime.now(timezone.utc).isoformat(),
                    'authentication_count': auth_count,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('device_id', device_id).execute()
                
                # 记录成功的认证
                await self._log_auth_attempt(device_id, 'success')
                
                return device
            else:
                # 记录失败的认证
                await self._log_auth_attempt(device_id, 'failed', 
                                     error='Invalid credentials')
                return None
                        
        except Exception as e:
            logger.error(f"Error verifying device credential: {e}")
            return None
    
    async def _log_auth_attempt(self, device_id: str, status: str, 
                         ip_address: str = None, user_agent: str = None, 
                         error: str = None):
        """记录认证尝试"""
        try:
            self.supabase.table('device_auth_logs').insert({
                'device_id': device_id,
                'auth_status': status,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'error_message': error,
                'created_at': datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error logging auth attempt: {e}")
    
    async def update_device_credential(self, device_id: str, 
                                      updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新设备凭证"""
        try:
            # 过滤掉不应更新的字段
            filtered_updates = {k: v for k, v in updates.items() 
                              if k not in ['device_id', 'created_at']}
            
            if not filtered_updates:
                return None
            
            filtered_updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            result = self.supabase.table('device_credentials').update(
                filtered_updates
            ).eq('device_id', device_id).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating device credential: {e}")
            return None
    
    async def revoke_device_credential(self, device_id: str) -> bool:
        """撤销设备凭证"""
        try:
            result = self.supabase.table('device_credentials').update({
                'status': 'revoked',
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('device_id', device_id).execute()
            
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            logger.error(f"Error revoking device credential: {e}")
            return False
    
    async def list_organization_devices(self, organization_id: str) -> List[Dict[str, Any]]:
        """列出组织的所有设备"""
        try:
            result = self.supabase.table('device_credentials').select(
                'device_id, device_name, device_type, status, '
                'last_authenticated_at, authentication_count, created_at, expires_at'
            ).eq('organization_id', organization_id).order(
                'created_at', desc=True
            ).execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error listing organization devices: {e}")
            return []
    
    async def get_device_auth_logs(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取设备认证日志"""
        try:
            result = self.supabase.table('device_auth_logs').select('*').eq(
                'device_id', device_id
            ).order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting device auth logs: {e}")
            return []