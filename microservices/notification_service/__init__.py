"""
Notification Service Package

通知服务包，提供通知发送和管理功能
"""

from .models import *
from .notification_service import NotificationService
from .notification_repository import NotificationRepository

__version__ = "1.0.0"
__all__ = [
    "NotificationService",
    "NotificationRepository"
]