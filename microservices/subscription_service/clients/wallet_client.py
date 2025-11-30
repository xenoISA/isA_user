"""
Wallet Service Client

Client for wallet operations - checking balances, deducting purchased credits.
"""

import logging
import httpx
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class WalletClient:
    """Client for wallet service"""

    def __init__(self, base_url: str = "http://wallet:8208"):
        self.base_url = base_url
        self.timeout = 10.0

    async def get_wallet_balance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet balance for a user"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/wallets/user/{user_id}"
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    logger.warning(f"Failed to get wallet: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching wallet balance: {e}")
            return None

    async def deduct_credits(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Deduct credits from user's wallet"""
        try:
            payload = {
                "amount": float(amount),
                "description": description,
            }
            if reference_id:
                payload["reference_id"] = reference_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/wallets/user/{user_id}/consume",
                    json=payload
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to deduct credits: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error deducting credits: {e}")
            return None

    async def add_credits(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Add credits to user's wallet (for refunds, bonuses, etc.)"""
        try:
            payload = {
                "amount": float(amount),
                "description": description,
            }
            if reference_id:
                payload["reference_id"] = reference_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/wallets/user/{user_id}/deposit",
                    json=payload
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to add credits: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            return None


__all__ = ["WalletClient"]
