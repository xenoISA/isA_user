"""
Tax Service Data Contract

Defines canonical data structures for tax service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for tax service test data.
"""

import uuid
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Enums (matching production event models)
# ============================================================================

class TaxEventType(str, Enum):
    """Tax event types for NATS publishing"""
    TAX_CALCULATED = "tax.calculated"
    TAX_FAILED = "tax.failed"


# ============================================================================
# Data Models (matching production Pydantic models)
# ============================================================================

class TaxLine(BaseModel):
    """Individual tax line item"""
    line_item_id: str
    tax_amount: Decimal = Field(..., ge=0)
    jurisdiction: Optional[str] = None
    rate: Optional[Decimal] = None


class TaxCalculation(BaseModel):
    """Tax calculation result"""
    calculation_id: str
    order_id: str
    currency: str = "USD"
    total_tax: Decimal = Field(default=Decimal("0"), ge=0)
    lines: List[TaxLine] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaxLineItem(BaseModel):
    """Tax line item in events"""
    line_item_id: str
    sku_id: Optional[str] = None
    tax_amount: float
    tax_rate: float
    jurisdiction: Optional[str] = None
    tax_type: Optional[str] = None


# ============================================================================
# Factory Functions
# ============================================================================

class TaxFactory:
    """Factory for generating test data"""

    @staticmethod
    def calculation_id() -> str:
        return f"calc_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def order_id() -> str:
        return f"ord_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def user_id() -> str:
        return f"user_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def shipping_address() -> Dict[str, Any]:
        return {
            "street": "123 Tax Street",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94102",
            "country": "US",
        }

    @staticmethod
    def items(count: int = 2) -> List[Dict[str, Any]]:
        return [
            {
                "sku_id": f"sku_{uuid.uuid4().hex[:8]}",
                "quantity": random.randint(1, 5),
                "unit_price": round(random.uniform(10.0, 200.0), 2),
                "name": f"Taxable Item {i + 1}",
            }
            for i in range(count)
        ]

    @staticmethod
    def calculate_request(
        items: Optional[List[Dict]] = None,
        address: Optional[Dict] = None,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        request = {
            "items": items or TaxFactory.items(),
            "address": address or TaxFactory.shipping_address(),
            "currency": currency,
        }
        if order_id:
            request["order_id"] = order_id
        if user_id:
            request["user_id"] = user_id
        return request

    @staticmethod
    def tax_line(**overrides) -> TaxLine:
        defaults = {
            "line_item_id": f"li_{uuid.uuid4().hex[:8]}",
            "tax_amount": Decimal(str(round(random.uniform(0.5, 20.0), 2))),
            "jurisdiction": "CA",
            "rate": Decimal("0.0875"),
        }
        defaults.update(overrides)
        return TaxLine(**defaults)

    @staticmethod
    def tax_calculation(**overrides) -> TaxCalculation:
        lines = overrides.pop("lines", [TaxFactory.tax_line(), TaxFactory.tax_line()])
        total_tax = sum(line.tax_amount for line in lines)
        defaults = {
            "calculation_id": TaxFactory.calculation_id(),
            "order_id": TaxFactory.order_id(),
            "currency": "USD",
            "total_tax": total_tax,
            "lines": lines,
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return TaxCalculation(**defaults)
