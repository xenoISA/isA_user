"""
Calendar Service Event Handlers

事件处理器 - 订阅其他服务的事件
"""

from .handlers import CalendarEventHandlers
from .publishers import CalendarEventPublisher

__all__ = ["CalendarEventHandlers"]
