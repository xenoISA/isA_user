"""
Billing Service - Mock Dependencies

Mock implementations for component testing.
These mocks simulate repository and external service behavior.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decimal import Decimal
import uuid


class MockBillingRepository:
    """Mock billing repository for component testing"""

    def __init__(self):
        self._records: Dict[str, Dict] = {}
        self._events: Dict[str, Dict] = {}
        self._quotas: Dict[str, Dict] = {}
        self._aggregations: Dict[str, Dict] = {}
        
        self.create_billing_record = AsyncMock(side_effect=self._create_billing_record)
        self.get_billing_record = AsyncMock(side_effect=self._get_billing_record)
        self.update_billing_record = AsyncMock(side_effect=self._update_billing_record)
        self.get_user_billing_records = AsyncMock(side_effect=self._get_user_billing_records)
        self.create_billing_event = AsyncMock(side_effect=self._create_billing_event)
        self.get_billing_event = AsyncMock(side_effect=self._get_billing_event)
        self.get_user_quota = AsyncMock(side_effect=self._get_user_quota)
        self.update_user_quota = AsyncMock(side_effect=self._update_user_quota)
        self.create_or_update_quota = AsyncMock(side_effect=self._create_or_update_quota)
        self.get_billing_stats = AsyncMock(side_effect=self._get_billing_stats)
        self.get_billing_quota = AsyncMock(side_effect=self._get_billing_quota)

    async def _get_billing_quota(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        service_type: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Mock billing quota retrieval"""
        if not user_id or not service_type:
            return None

        key = f"{user_id}_{service_type}"
        data = self._quotas.get(key)
        if data is None:
            return None

        quota = MagicMock()
        for k, v in data.items():
            setattr(quota, k, v)
        return quota

    async def _create_billing_record(self, record_data: Dict[str, Any]) -> Any:
        """Mock billing record creation"""
        billing_id = record_data.get("billing_id", f"bill_{uuid.uuid4().hex[:24]}")
        now = datetime.now(timezone.utc)

        record = MagicMock()
        record.billing_id = billing_id
        record.user_id = record_data.get("user_id")
        record.organization_id = record_data.get("organization_id")
        record.subscription_id = record_data.get("subscription_id")
        record.usage_record_id = record_data.get("usage_record_id")
        record.product_id = record_data.get("product_id")
        record.service_type = record_data.get("service_type")
        record.usage_amount = Decimal(str(record_data.get("usage_amount", 0)))
        record.unit_price = Decimal(str(record_data.get("unit_price", 0)))
        record.total_amount = Decimal(str(record_data.get("total_amount", 0)))
        record.currency = record_data.get("currency", "USD")
        record.billing_method = record_data.get("billing_method")
        record.billing_status = record_data.get("billing_status", "pending")
        record.processed_at = record_data.get("processed_at")
        record.failure_reason = record_data.get("failure_reason")
        record.wallet_transaction_id = record_data.get("wallet_transaction_id")
        record.payment_transaction_id = record_data.get("payment_transaction_id")
        record.billing_metadata = record_data.get("billing_metadata", {})
        record.created_at = now
        record.updated_at = now

        self._records[billing_id] = {
            "billing_id": billing_id,
            "user_id": record.user_id,
            "organization_id": record.organization_id,
            "subscription_id": record.subscription_id,
            "usage_record_id": record.usage_record_id,
            "product_id": record.product_id,
            "service_type": record.service_type,
            "usage_amount": record.usage_amount,
            "unit_price": record.unit_price,
            "total_amount": record.total_amount,
            "currency": record.currency,
            "billing_method": record.billing_method,
            "billing_status": record.billing_status,
            "processed_at": record.processed_at,
            "failure_reason": record.failure_reason,
            "wallet_transaction_id": record.wallet_transaction_id,
            "payment_transaction_id": record.payment_transaction_id,
            "billing_metadata": record.billing_metadata,
            "created_at": now,
            "updated_at": now,
        }

        return record

    async def _get_billing_record(self, billing_id: str) -> Optional[Any]:
        """Mock billing record retrieval"""
        data = self._records.get(billing_id)
        if data is None:
            return None

        record = MagicMock()
        for key, value in data.items():
            setattr(record, key, value)
        return record

    async def _update_billing_record(self, billing_id: str, update_data: Dict[str, Any]) -> bool:
        """Mock billing record update"""
        if billing_id not in self._records:
            return False

        now = datetime.now(timezone.utc)
        for key, value in update_data.items():
            self._records[billing_id][key] = value
        self._records[billing_id]["updated_at"] = now
        return True

    async def _get_user_billing_records(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        service_type: Optional[str] = None,
    ) -> List[Any]:
        """Mock user billing records retrieval"""
        records = []
        for billing_id, data in self._records.items():
            if data["user_id"] == user_id:
                if status and data["billing_status"] != status:
                    continue
                if service_type and data["service_type"] != service_type:
                    continue
                record = MagicMock()
                for key, value in data.items():
                    setattr(record, key, value)
                records.append(record)

        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[offset:offset + limit]

    async def _create_billing_event(self, event_data: Dict[str, Any]) -> Any:
        """Mock billing event creation"""
        event_id = event_data.get("event_id", f"evt_{uuid.uuid4().hex[:24]}")
        now = datetime.now(timezone.utc)

        event = MagicMock()
        event.event_id = event_id
        event.event_type = event_data.get("event_type")
        event.event_source = event_data.get("event_source")
        event.user_id = event_data.get("user_id")
        event.organization_id = event_data.get("organization_id")
        event.subscription_id = event_data.get("subscription_id")
        event.billing_record_id = event_data.get("billing_record_id")
        event.service_type = event_data.get("service_type")
        event.event_data = event_data.get("event_data", {})
        event.amount = event_data.get("amount")
        event.currency = event_data.get("currency")
        event.is_processed = event_data.get("is_processed", False)
        event.processed_at = event_data.get("processed_at")
        event.event_timestamp = event_data.get("event_timestamp", now)
        event.created_at = now

        self._events[event_id] = {
            "event_id": event_id,
            "event_type": event.event_type,
            "event_source": event.event_source,
            "user_id": event.user_id,
            "organization_id": event.organization_id,
            "subscription_id": event.subscription_id,
            "billing_record_id": event.billing_record_id,
            "service_type": event.service_type,
            "event_data": event.event_data,
            "amount": event.amount,
            "currency": event.currency,
            "is_processed": event.is_processed,
            "processed_at": event.processed_at,
            "event_timestamp": event.event_timestamp,
            "created_at": now,
        }

        return event

    async def _get_billing_event(self, event_id: str) -> Optional[Any]:
        """Mock billing event retrieval"""
        data = self._events.get(event_id)
        if data is None:
            return None

        event = MagicMock()
        for key, value in data.items():
            setattr(event, key, value)
        return event

    async def _get_user_quota(self, user_id: str, service_type: str) -> Optional[Any]:
        """Mock user quota retrieval"""
        key = f"{user_id}_{service_type}"
        data = self._quotas.get(key)
        if data is None:
            return None

        quota = MagicMock()
        for k, v in data.items():
            setattr(quota, k, v)
        return quota

    async def _update_user_quota(self, user_id: str, service_type: str, used_amount: Decimal) -> bool:
        """Mock user quota update"""
        key = f"{user_id}_{service_type}"
        if key not in self._quotas:
            return False

        self._quotas[key]["quota_used"] = Decimal(str(self._quotas[key]["quota_used"])) + Decimal(str(used_amount))
        self._quotas[key]["quota_remaining"] = Decimal(str(self._quotas[key]["quota_limit"])) - self._quotas[key]["quota_used"]
        self._quotas[key]["updated_at"] = datetime.now(timezone.utc)
        return True

    async def _create_or_update_quota(self, quota_data: Dict[str, Any]) -> Any:
        """Mock quota creation or update"""
        user_id = quota_data.get("user_id")
        service_type = quota_data.get("service_type")
        key = f"{user_id}_{service_type}"
        now = datetime.now(timezone.utc)

        quota_id = quota_data.get("quota_id", f"quota_{uuid.uuid4().hex[:16]}")
        
        self._quotas[key] = {
            "quota_id": quota_id,
            "user_id": user_id,
            "organization_id": quota_data.get("organization_id"),
            "subscription_id": quota_data.get("subscription_id"),
            "service_type": service_type,
            "product_id": quota_data.get("product_id"),
            "quota_limit": Decimal(str(quota_data.get("quota_limit", 100000))),
            "quota_used": Decimal(str(quota_data.get("quota_used", 0))),
            "quota_remaining": Decimal(str(quota_data.get("quota_limit", 100000))) - Decimal(str(quota_data.get("quota_used", 0))),
            "quota_period": quota_data.get("quota_period", "monthly"),
            "reset_date": quota_data.get("reset_date", now + timedelta(days=30)),
            "last_reset_date": quota_data.get("last_reset_date"),
            "auto_reset": quota_data.get("auto_reset", True),
            "is_active": quota_data.get("is_active", True),
            "is_exceeded": False,
            "created_at": now,
            "updated_at": now,
        }

        quota = MagicMock()
        for k, v in self._quotas[key].items():
            setattr(quota, k, v)
        return quota

    async def _get_billing_stats(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Mock billing statistics"""
        total_records = len(self._records)
        completed = sum(1 for r in self._records.values() if r["billing_status"] == "completed")
        pending = sum(1 for r in self._records.values() if r["billing_status"] == "pending")
        failed = sum(1 for r in self._records.values() if r["billing_status"] == "failed")
        
        total_revenue = sum(
            Decimal(str(r["total_amount"])) 
            for r in self._records.values() 
            if r["billing_status"] == "completed"
        )

        return {
            "total_billing_records": total_records,
            "pending_billing_records": pending,
            "completed_billing_records": completed,
            "failed_billing_records": failed,
            "total_revenue": total_revenue,
        }

    def add_quota(self, user_id: str, service_type: str, quota_limit: Decimal, quota_used: Decimal = Decimal("0")):
        """Add quota to mock"""
        key = f"{user_id}_{service_type}"
        now = datetime.now(timezone.utc)
        self._quotas[key] = {
            "quota_id": f"quota_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "service_type": service_type,
            "quota_limit": quota_limit,
            "quota_used": quota_used,
            "quota_remaining": quota_limit - quota_used,
            "quota_period": "monthly",
            "reset_date": now + timedelta(days=30),
            "is_active": True,
            "is_exceeded": False,
            "created_at": now,
            "updated_at": now,
        }

    def reset(self):
        """Reset mock state"""
        self._records.clear()
        self._events.clear()
        self._quotas.clear()
        self._aggregations.clear()


class MockEventBus:
    """Mock NATS event bus for component testing"""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish_event = AsyncMock(side_effect=self._publish_event)

    async def _publish_event(self, event: Any) -> None:
        """Mock event publishing"""
        self.published_events.append(event)

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def get_events_by_type(self, event_type: str) -> List[Any]:
        """Get published events by type"""
        result = []
        for e in self.published_events:
            if hasattr(e, 'type'):
                if str(e.type) == event_type or (hasattr(e.type, 'value') and str(e.type.value) == event_type):
                    result.append(e)
            elif hasattr(e, 'event_type'):
                if str(e.event_type) == event_type:
                    result.append(e)
            elif isinstance(e, dict):
                if e.get('event_type') == event_type:
                    result.append(e)
        return result

    def reset(self):
        """Reset mock state"""
        self.published_events.clear()


class MockWalletClient:
    """Mock wallet service client for component testing"""

    def __init__(self):
        self._wallets: Dict[str, Dict] = {}
        self.get_wallet_balance = AsyncMock(side_effect=self._get_wallet_balance)
        self.deduct_balance = AsyncMock(side_effect=self._deduct_balance)
        self.deduct_credits = AsyncMock(side_effect=self._deduct_credits)

    async def _get_wallet_balance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mock wallet balance retrieval"""
        return self._wallets.get(user_id)

    async def _deduct_balance(self, user_id: str, amount: Decimal, reason: str = "") -> Dict[str, Any]:
        """Mock wallet balance deduction"""
        if user_id not in self._wallets:
            return {"success": False, "message": "Wallet not found"}
        
        wallet = self._wallets[user_id]
        if Decimal(str(wallet["balance"])) < amount:
            return {"success": False, "message": "Insufficient balance"}
        
        wallet["balance"] = Decimal(str(wallet["balance"])) - amount
        return {
            "success": True,
            "transaction_id": f"txn_{uuid.uuid4().hex[:24]}",
            "remaining_balance": wallet["balance"],
        }

    async def _deduct_credits(self, user_id: str, amount: Decimal, reason: str = "") -> Dict[str, Any]:
        """Mock credit deduction"""
        if user_id not in self._wallets:
            return {"success": False, "message": "Wallet not found"}
        
        wallet = self._wallets[user_id]
        if Decimal(str(wallet.get("credits", 0))) < amount:
            return {"success": False, "message": "Insufficient credits"}
        
        wallet["credits"] = Decimal(str(wallet.get("credits", 0))) - amount
        return {
            "success": True,
            "transaction_id": f"txn_{uuid.uuid4().hex[:24]}",
            "remaining_credits": wallet["credits"],
        }

    def add_wallet(self, user_id: str, balance: Decimal = Decimal("100"), credits: Decimal = Decimal("0")):
        """Add wallet to mock"""
        self._wallets[user_id] = {
            "user_id": user_id,
            "balance": balance,
            "credits": credits,
            "currency": "USD",
        }

    def reset(self):
        """Reset mock state"""
        self._wallets.clear()


class MockSubscriptionClient:
    """Mock subscription service client for component testing"""

    def __init__(self):
        self._subscriptions: Dict[str, Dict] = {}
        self._credit_balances: Dict[str, Dict] = {}
        self.get_user_subscription = AsyncMock(side_effect=self._get_user_subscription)
        self.check_service_coverage = AsyncMock(side_effect=self._check_service_coverage)
        self.get_credit_balance = AsyncMock(side_effect=self._get_credit_balance)

    async def _get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mock subscription retrieval"""
        return self._subscriptions.get(user_id)

    async def _check_service_coverage(self, user_id: str, service_type: str) -> bool:
        """Mock service coverage check"""
        sub = self._subscriptions.get(user_id)
        if not sub:
            return False
        if not sub.get("is_active"):
            return False
        covered_services = sub.get("covered_services", [])
        return service_type in covered_services

    async def _get_credit_balance(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Mock subscription credit balance retrieval"""
        balance = self._credit_balances.get(user_id)
        if balance:
            return {
                "success": True,
                "subscription_credits_remaining": balance.get("credits", 0),
                "total_credits": balance.get("total_credits", 0),
            }
        return {"success": False, "message": "No credit balance found"}

    def add_credit_balance(self, user_id: str, credits: Decimal, total_credits: Decimal = None):
        """Add credit balance to mock"""
        self._credit_balances[user_id] = {
            "credits": credits,
            "total_credits": total_credits or credits,
        }

    def add_subscription(
        self, 
        user_id: str, 
        plan_id: str = "premium",
        covered_services: List[str] = None,
        is_active: bool = True
    ):
        """Add subscription to mock"""
        self._subscriptions[user_id] = {
            "subscription_id": f"sub_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "plan_id": plan_id,
            "covered_services": covered_services or [],
            "is_active": is_active,
            "started_at": datetime.now(timezone.utc),
        }

    def reset(self):
        """Reset mock state"""
        self._subscriptions.clear()
        self._credit_balances.clear()


class MockProductClient:
    """Mock product service client for component testing"""

    def __init__(self):
        self._products: Dict[str, Dict] = {}
        self.get_product_pricing = AsyncMock(side_effect=self._get_product_pricing)

    async def _get_product_pricing(self, product_id: str, user_id: str = None, subscription_id: str = None) -> Optional[Dict[str, Any]]:
        """Mock product pricing retrieval"""
        return self._products.get(product_id)

    def add_product(
        self, 
        product_id: str, 
        unit_price: Decimal = Decimal("0.001"),
        free_tier_limit: Decimal = Decimal("1000"),
        currency: str = "USD"
    ):
        """Add product to mock"""
        self._products[product_id] = {
            "product_id": product_id,
            "unit_price": unit_price,
            "pricing_model": {
                "base_unit_price": unit_price,
            },
            "effective_pricing": {
                "base_unit_price": unit_price,
            },
            "free_tier": {
                "limit": free_tier_limit,
                "remaining": free_tier_limit,
            },
            "currency": currency,
        }

    def reset(self):
        """Reset mock state"""
        self._products.clear()


# Import timedelta for quota date calculations
from datetime import timedelta
