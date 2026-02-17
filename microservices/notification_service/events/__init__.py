"""
Event handlers for Notification Service
"""

# Only export what's needed, handlers are imported lazily in main.py
from . import models
from .publishers import NotificationEventPublishers

__all__ = [
    "NotificationEventPublishers",
    "models",
]
