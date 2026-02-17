"""
Tax Service Event Models

Pydantic models for events published by tax service
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class TaxEventType(str, Enum):
    """
    Events published by tax_service.

    Stream: tax-stream
    Subjects: tax.>
    """
    TAX_CALCULATED = "tax.calculated"
    TAX_FAILED = "tax.failed"


class TaxSubscribedEventType(str, Enum):
    """Events that tax_service subscribes to from other services."""
    INVENTORY_RESERVED = "inventory.reserved"


class TaxStreamConfig:
    """Stream configuration for tax_service"""
    STREAM_NAME = "tax-stream"
    SUBJECTS = ["tax.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "tax"


# =============================================================================
# Event Data Models
# =============================================================================

class TaxLineItem(BaseModel):
    """Tax line per order line item"""
    line_item_id: str
    sku_id: Optional[str] = None
    tax_amount: float
    tax_rate: float
    jurisdiction: Optional[str] = None
    tax_type: Optional[str] = None


class TaxCalculatedEvent(BaseModel):
    """Event published when tax is successfully calculated"""
    order_id: str
    calculation_id: str
    user_id: str
    subtotal: float
    total_tax: float
    currency: str = "USD"
    tax_lines: List[TaxLineItem] = Field(default_factory=list)
    shipping_address: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaxFailedEvent(BaseModel):
    """Event published when tax calculation fails"""
    order_id: str
    user_id: str
    error_code: Optional[str] = None
    error_message: str
    items: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
