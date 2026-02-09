"""
Tax Service Data Models

Calculates tax for US/EU based on addresses and line items.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class TaxLine(BaseModel):
    """Tax line per order line item"""
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
