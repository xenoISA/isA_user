"""Mock tax provider (returns zero tax)."""

from typing import Dict, Any, List

from .base import TaxProvider


class MockTaxProvider(TaxProvider):
    async def calculate(self, items: List[Dict[str, Any]], address: Dict[str, Any], currency: str) -> Dict[str, Any]:
        return {
            "currency": currency,
            "total_tax": 0.0,
            "lines": [],
        }
