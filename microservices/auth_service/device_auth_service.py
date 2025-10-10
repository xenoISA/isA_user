"""
Device Authentication Service

设备认证服务层
"""

import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging
import jwt
import os

from .device_auth_repository import DeviceAuthRepository

logger = logging.getLogger(__name__)

class DeviceAuthService:
    """设备认证服务"""
    
    def __init__(self, repository: DeviceAuthRepository):
        self.repository = repository
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
        self.jwt_algorithm = 'HS256'
    
    def _generate_device_secret(self) -> str:
        """生成设备密钥"""
        return secrets.token_urlsafe(32)
    
    def _hash_secret(self, secret: str) -> str:
        """哈希设备密钥"""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    async def register_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册新设备"""
        try:
            # 生成设备密钥
            device_secret = self._generate_device_secret()
            device_secret_hash = self._hash_secret(device_secret)
            
            # 准备设备数据
            credential_data = {
                'device_id': device_data['device_id'],
                'device_secret': device_secret_hash,
                'organization_id': device_data['organization_id'],
                'device_name': device_data.get('device_name'),
                'device_type': device_data.get('device_type'),
                'status': 'active',
                'metadata': device_data.get('metadata', {}),
                'expires_at': device_data.get('expires_at')
            }
            
            # 创建设备凭证
            result = await self.repository.create_device_credential(credential_data)
            
            if result:
                # 返回包含明文密钥的结果（仅在注册时返回）
                return {
                    'success': True,
                    'device_id': result['device_id'],
                    'device_secret': device_secret,  # 明文密钥，仅此一次
                    'organization_id': result['organization_id'],
                    'device_name': result.get('device_name'),
                    'device_type': result.get('device_type'),
                    'status': result['status'],
                    'created_at': result['created_at']
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to register device'
                }
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def authenticate_device(self, device_id: str, device_secret: str,
                                 ip_address: str = None, 
                                 user_agent: str = None) -> Dict[str, Any]:
        """认证设备"""
        try:
            # 哈希提供的密钥
            device_secret_hash = self._hash_secret(device_secret)
            
            # 验证凭证
            device = await self.repository.verify_device_credential(
                device_id, device_secret_hash
            )
            
            if device:
                # 生成设备 JWT token
                token_payload = {
                    'device_id': device['device_id'],
                    'organization_id': device['organization_id'],
                    'device_type': device.get('device_type'),
                    'type': 'device',
                    'iat': datetime.now(timezone.utc),
                    'exp': datetime.now(timezone.utc) + timedelta(hours=24)
                }
                
                token = jwt.encode(token_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
                
                return {
                    'success': True,
                    'authenticated': True,
                    'device_id': device['device_id'],
                    'organization_id': device['organization_id'],
                    'device_name': device.get('device_name'),
                    'device_type': device.get('device_type'),
                    'token': token,
                    'expires_in': 86400  # 24 hours
                }
            else:
                return {
                    'success': False,
                    'authenticated': False,
                    'error': 'Invalid device credentials'
                }
        except Exception as e:
            logger.error(f"Error authenticating device: {e}")
            return {
                'success': False,
                'authenticated': False,
                'error': str(e)
            }
    
    async def verify_device_token(self, token: str) -> Dict[str, Any]:
        """验证设备 JWT token"""
        try:
            # 解码 token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # 检查 token 类型
            if payload.get('type') != 'device':
                return {
                    'valid': False,
                    'error': 'Invalid token type'
                }
            
            # 检查设备是否仍然有效
            device = await self.repository.get_device_credential(payload['device_id'])
            if not device:
                return {
                    'valid': False,
                    'error': 'Device not found or inactive'
                }
            
            return {
                'valid': True,
                'device_id': payload['device_id'],
                'organization_id': payload['organization_id'],
                'device_type': payload.get('device_type'),
                'expires_at': datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Token has expired'
            }
        except jwt.InvalidTokenError as e:
            return {
                'valid': False,
                'error': f'Invalid token: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error verifying device token: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    async def refresh_device_secret(self, device_id: str, 
                                   organization_id: str) -> Dict[str, Any]:
        """刷新设备密钥"""
        try:
            # 验证设备归属
            device = await self.repository.get_device_credential(device_id)
            if not device or device['organization_id'] != organization_id:
                return {
                    'success': False,
                    'error': 'Device not found or unauthorized'
                }
            
            # 生成新密钥
            new_secret = self._generate_device_secret()
            new_secret_hash = self._hash_secret(new_secret)
            
            # 更新密钥
            result = await self.repository.update_device_credential(
                device_id, 
                {'device_secret': new_secret_hash}
            )
            
            if result:
                return {
                    'success': True,
                    'device_id': device_id,
                    'device_secret': new_secret,  # 明文密钥
                    'message': 'Device secret refreshed successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to refresh device secret'
                }
                
        except Exception as e:
            logger.error(f"Error refreshing device secret: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def revoke_device(self, device_id: str, 
                           organization_id: str) -> Dict[str, Any]:
        """撤销设备"""
        try:
            # 验证设备归属
            device = await self.repository.get_device_credential(device_id)
            if not device or device['organization_id'] != organization_id:
                return {
                    'success': False,
                    'error': 'Device not found or unauthorized'
                }
            
            # 撤销设备
            result = await self.repository.revoke_device_credential(device_id)
            
            if result:
                return {
                    'success': True,
                    'message': f'Device {device_id} has been revoked'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to revoke device'
                }
                
        except Exception as e:
            logger.error(f"Error revoking device: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def list_devices(self, organization_id: str) -> Dict[str, Any]:
        """列出组织的所有设备"""
        try:
            devices = await self.repository.list_organization_devices(organization_id)
            return {
                'success': True,
                'devices': devices,
                'count': len(devices)
            }
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': []
            }
    
    async def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """获取设备信息"""
        try:
            device = await self.repository.get_device_credential(device_id)
            if device:
                # 不返回密钥哈希
                device.pop('device_secret', None)
                return {
                    'success': True,
                    'device': device
                }
            else:
                return {
                    'success': False,
                    'error': 'Device not found'
                }
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_device_auth_logs(self, device_id: str, 
                                  organization_id: str,
                                  limit: int = 100) -> Dict[str, Any]:
        """获取设备认证日志"""
        try:
            # 验证设备归属
            device = await self.repository.get_device_credential(device_id)
            if not device or device['organization_id'] != organization_id:
                return {
                    'success': False,
                    'error': 'Device not found or unauthorized'
                }
            
            logs = await self.repository.get_device_auth_logs(device_id, limit)
            return {
                'success': True,
                'logs': logs,
                'count': len(logs)
            }
        except Exception as e:
            logger.error(f"Error getting device auth logs: {e}")
            return {
                'success': False,
                'error': str(e),
                'logs': []
            }