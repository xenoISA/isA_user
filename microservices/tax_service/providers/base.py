"""Tax provider interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class TaxProvider(ABC):
    """Abstract tax provider."""

    @abstractmethod
    async def calculate(self, items: List[Dict[str, Any]], address: Dict[str, Any], currency: str) -> Dict[str, Any]:
        """Calculate tax for items and address."""
        raise NotImplementedError
