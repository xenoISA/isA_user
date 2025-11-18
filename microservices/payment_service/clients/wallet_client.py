"""
Wallet Service Client for Payment Service

HTTP client for synchronous communication with wallet_service
"""

import httpx
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class WalletClient:
    """Client for wallet_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Wallet Service client

        Args:
            base_url: Wallet service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("wallet_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8207"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"WalletClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_wallet(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's wallet

        Args:
            user_id: User ID

        Returns:
            Wallet data if found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallet/user/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Wallet for user {user_id} not found")
                return None
            logger.error(f"Failed to get wallet: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet: {e}")
            return None

    async def get_balance(self, user_id: str) -> Optional[Decimal]:
        """
        Get wallet balance

        Args:
            user_id: User ID

        Returns:
            Balance as Decimal
        """
        wallet = await self.get_wallet(user_id)
        if wallet and 'balance' in wallet:
            return Decimal(str(wallet['balance']))
        return None

    async def add_credits(
        self,
        user_id: str,
        amount: Decimal,
        reason: str = "payment_completed",
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Add credits to wallet

        Args:
            user_id: User ID
            amount: Amount to add
            reason: Reason for adding credits
            transaction_id: Related transaction ID

        Returns:
            True if successful
        """
        try:
            payload = {
                "user_id": user_id,
                "amount": float(amount),
                "reason": reason,
                "transaction_id": transaction_id
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallet/credits/add",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add credits: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            return False

    async def deduct_credits(
        self,
        user_id: str,
        amount: Decimal,
        reason: str = "payment_charge",
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Deduct credits from wallet

        Args:
            user_id: User ID
            amount: Amount to deduct
            reason: Reason for deduction
            transaction_id: Related transaction ID

        Returns:
            True if successful
        """
        try:
            payload = {
                "user_id": user_id,
                "amount": float(amount),
                "reason": reason,
                "transaction_id": transaction_id
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallet/credits/deduct",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to deduct credits: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deducting credits: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if wallet service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
