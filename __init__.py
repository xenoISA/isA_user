"""
User Service Package

提供用户认证、订阅管理和支付处理的综合服务
包含 Auth0 集成、Stripe 支付和用户生命周期管理
"""

# 移除有问题的导入，避免连锁依赖
# 如需使用具体服务，请直接导入对应模块
# from .services.auth_service import Auth0Service  # 注释掉避免连锁依赖
from .models import User, Subscription, ApiUsage, SubscriptionStatus

__all__ = [
    "Auth0Service",  
    "PaymentService",  
    "User",
    "Subscription", 
    "ApiUsage",
    "SubscriptionStatus"
] 