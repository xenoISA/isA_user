#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Billing Service Event Handlers

Handles incoming events from NATS message bus.
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from isa_common.events import EventHandler, UsageEvent, EventType, BillingEventPublisher

if TYPE_CHECKING:
    from ..billing_service import BillingService

logger = logging.getLogger(__name__)


class UsageEventHandler(EventHandler):
    """
    Handles usage.recorded.* events.

    Flow:
    1. Receive UsageEvent from isA_Model, isA_Agent, or isA_MCP
    2. Calculate billing cost (including token equivalents)
    3. Create billing record in database
    4. Publish BillingCalculatedEvent for wallet_service
    """

    def __init__(self, billing_service: 'BillingService', event_publisher: BillingEventPublisher):
        """
        Initialize handler.

        Args:
            billing_service: Billing service instance
            event_publisher: Event publisher for downstream events
        """
        self.billing_service = billing_service
        self.event_publisher = event_publisher

    def event_type(self) -> str:
        """Return event type this handler processes"""
        return EventType.USAGE_RECORDED

    async def handle(self, event: UsageEvent) -> bool:
        """
        Handle usage.recorded event.

        Args:
            event: UsageEvent from NATS

        Returns:
            True if processed successfully
        """
        try:
            logger.info(
                f"Processing usage event: user={event.user_id}, "
                f"product={event.product_id}, amount={event.usage_amount}"
            )

            # 1. Get product pricing from product_service
            pricing_info = await self.billing_service._get_product_pricing(
                event.product_id,
                event.user_id,
                event.subscription_id
            )

            if not pricing_info:
                logger.error(f"Pricing not found for product {event.product_id}")
                # Publish billing error event
                await self.event_publisher.publish_billing_error(
                    user_id=event.user_id,
                    usage_event_id=event.event_id,
                    product_id=event.product_id,
                    error_code="PRICING_NOT_FOUND",
                    error_message=f"No pricing configured for {event.product_id}"
                )
                return False

            # 2. Parse pricing structure
            pricing_model = pricing_info.get("pricing_model", {})
            effective_pricing = pricing_info.get("effective_pricing", {})

            unit_price = Decimal(str(
                pricing_info.get("unit_price") or
                effective_pricing.get("base_unit_price") or
                pricing_model.get("base_unit_price") or
                0
            ))

            # 3. Calculate cost
            base_cost = event.usage_amount * unit_price

            # 4. Add model costs from metadata (for MCP tools)
            model_cost = Decimal(str(event.usage_details.get("model_cost_usd", 0)))
            api_cost = Decimal(str(event.usage_details.get("search_api_cost_usd", 0)))
            storage_cost = Decimal(str(event.usage_details.get("storage_cost_usd", 0)))

            total_cost = base_cost + model_cost + api_cost + storage_cost

            # 5. Convert to token equivalents (1 token = $0.00003 baseline)
            token_conversion_rate = Decimal("0.00003")  # GPT-4 input token cost
            token_equivalent = total_cost / token_conversion_rate

            logger.info(
                f"Cost calculated: base=${base_cost:.6f}, "
                f"model=${model_cost:.6f}, total=${total_cost:.6f}, "
                f"tokens={token_equivalent:.0f}"
            )

            # 6. Check if free tier or subscription included
            is_free_tier = await self._check_free_tier(
                event.user_id,
                event.product_id,
                event.usage_amount,
                pricing_model
            )

            is_subscription = await self._check_subscription_included(
                event.user_id,
                event.subscription_id,
                event.product_id,
                event.usage_amount
            )

            # 7. Create billing record
            billing_record = await self.billing_service.repository.create_billing_record({
                "user_id": event.user_id,
                "organization_id": event.organization_id,
                "subscription_id": event.subscription_id,
                "product_id": event.product_id,
                "usage_amount": float(event.usage_amount),
                "unit_price": float(unit_price),
                "total_amount": float(total_cost),
                "usage_record_id": event.event_id,  # Link to usage event
                "billing_metadata": {
                    "usage_event_id": event.event_id,
                    "unit_type": event.unit_type,
                    "token_equivalent": float(token_equivalent),
                    "token_conversion_rate": float(token_conversion_rate),
                    "is_free_tier": is_free_tier,
                    "is_subscription_included": is_subscription,
                    "usage_details": event.usage_details
                }
            })

            if not billing_record:
                logger.error("Failed to create billing record")
                return False

            # 8. Publish billing.calculated event
            success = await self.event_publisher.publish_billing_calculated(
                user_id=event.user_id,
                billing_record_id=billing_record.billing_id,
                usage_event_id=event.event_id,
                product_id=event.product_id,
                actual_usage=event.usage_amount,
                unit_type=event.unit_type,
                token_equivalent=token_equivalent,
                cost_usd=total_cost,
                unit_price=unit_price,
                token_conversion_rate=token_conversion_rate,
                is_free_tier=is_free_tier,
                is_included_in_subscription=is_subscription
            )

            if success:
                logger.info(
                    f"✅ Billing calculated and published: "
                    f"record={billing_record.billing_id}, "
                    f"cost=${total_cost:.6f}, tokens={token_equivalent:.0f}"
                )
                return True
            else:
                logger.error("Failed to publish billing.calculated event")
                return False

        except Exception as e:
            logger.error(f"Error handling usage event: {e}", exc_info=True)

            # Try to publish error event
            try:
                await self.event_publisher.publish_billing_error(
                    user_id=event.user_id,
                    usage_event_id=event.event_id,
                    product_id=event.product_id,
                    error_code="BILLING_CALCULATION_ERROR",
                    error_message=str(e)
                )
            except:
                pass

            return False

    async def _check_free_tier(
        self,
        user_id: str,
        product_id: str,
        usage_amount: Decimal,
        pricing_model: dict
    ) -> bool:
        """
        Check if usage is within free tier limits.

        Args:
            user_id: User ID
            product_id: Product ID
            usage_amount: Usage amount
            pricing_model: Pricing model data

        Returns:
            True if within free tier
        """
        try:
            free_tier_limit = Decimal(str(pricing_model.get("free_tier_limit", 0)))
            if free_tier_limit <= 0:
                return False

            # Check user's free tier usage for this product
            # TODO: Query billing_records for user's total free tier usage this period
            # For now, simplified check
            return usage_amount <= free_tier_limit

        except Exception as e:
            logger.error(f"Error checking free tier: {e}")
            return False

    async def _check_subscription_included(
        self,
        user_id: str,
        subscription_id: str,
        product_id: str,
        usage_amount: Decimal
    ) -> bool:
        """
        Check if usage is included in user's subscription.

        Args:
            user_id: User ID
            subscription_id: Subscription ID
            product_id: Product ID
            usage_amount: Usage amount

        Returns:
            True if included in subscription
        """
        try:
            if not subscription_id:
                return False

            # Get subscription info from product_service
            subscription_info = await self.billing_service._get_subscription_info(
                subscription_id
            )

            if not subscription_info:
                return False

            # Check if product is included
            included_products = subscription_info.get("included_products", [])
            for included in included_products:
                if included.get("product_id") == product_id:
                    included_amount = Decimal(str(included.get("included_amount", 0)))
                    if usage_amount <= included_amount:
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False
