"""
Membership Service Event Handlers

NATS event subscription handlers.
"""

import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)


class MembershipEventHandlers:
    """Membership service event handlers"""

    def __init__(self, membership_service, event_bus):
        self.service = membership_service
        self.repository = membership_service.repository
        self.event_bus = event_bus

    def get_event_handler_map(self) -> Dict[str, Callable]:
        return {
            "order.completed": self.handle_order_completed,
            "user.deleted": self.handle_user_deleted,
            "subscription.renewed": self.handle_subscription_renewed,
        }

    async def handle_order_completed(self, event_data: dict):
        """Award points for completed order"""
        try:
            user_id = event_data.get("data", {}).get("user_id") or event_data.get("user_id")
            order_total = event_data.get("data", {}).get("total_amount", 0) or event_data.get("total_amount", 0)

            if user_id and order_total > 0:
                # Calculate base points: $1 = 100 points
                base_points = int(float(order_total) * 100)

                try:
                    result = await self.service.earn_points(
                        user_id=user_id,
                        points_amount=base_points,
                        source="order_completed",
                        reference_id=event_data.get("data", {}).get("order_id") or event_data.get("order_id"),
                        description=f"Order ${float(order_total):.2f}"
                    )

                    if result.success:
                        logger.info(f"Awarded {result.points_earned} points to {user_id} for order")
                    else:
                        logger.warning(f"Failed to award points: {result.message}")
                except Exception as e:
                    logger.error(f"Failed to award points: {e}")

        except Exception as e:
            logger.error(f"Error handling order.completed: {e}")

    async def handle_user_deleted(self, event_data: dict):
        """GDPR compliance - delete all user data"""
        try:
            user_id = event_data.get("data", {}).get("user_id") or event_data.get("user_id")

            if user_id:
                deleted_count = await self.repository.delete_user_data(user_id)
                logger.info(f"Deleted {deleted_count} membership records for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling user.deleted: {e}")

    async def handle_subscription_renewed(self, event_data: dict):
        """Sync tier benefits when subscription renews"""
        try:
            user_id = event_data.get("data", {}).get("user_id") or event_data.get("user_id")
            tier_code = event_data.get("data", {}).get("tier_code") or event_data.get("tier_code")

            if user_id and tier_code:
                membership = await self.repository.get_membership_by_user(user_id)
                if membership:
                    logger.info(f"Subscription renewed for user {user_id}, tier: {tier_code}")

        except Exception as e:
            logger.error(f"Error handling subscription.renewed: {e}")


def get_event_handlers(membership_service, event_bus) -> Dict[str, Callable]:
    """Get event handler map"""
    handlers = MembershipEventHandlers(membership_service, event_bus)
    return handlers.get_event_handler_map()


__all__ = ["MembershipEventHandlers", "get_event_handlers"]
