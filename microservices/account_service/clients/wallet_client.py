"""
Wallet Service Client

HTTP client for synchronous communication with wallet_service
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class WalletServiceClient:
    """Client for wallet_service HTTP API"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize wallet service client

        Args:
            base_url: Base URL of wallet service (e.g., "http://localhost:8010")
                     If None, will use service discovery via Consul
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "http://wallet_service:8010"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def get_wallet_balance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's wallet balance

        Args:
            user_id: User ID

        Returns:
            Wallet balance data if found, None otherwise
            Example: {"user_id": "user_123", "balance": 100.50, "currency": "USD"}
        """
        try:
            url = f"{self.base_url}/api/v1/wallet/{user_id}/balance"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"No wallet found for user: {user_id}")
                return None
            else:
                logger.error(
                    f"Failed to get wallet balance for {user_id}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calling wallet_service.get_wallet_balance: {e}")
            return None

    async def get_wallet_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed wallet information

        Args:
            user_id: User ID

        Returns:
            Wallet info including balance, transactions, etc.
        """
        try:
            url = f"{self.base_url}/api/v1/wallet/{user_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"No wallet found for user: {user_id}")
                return None
            else:
                logger.error(
                    f"Failed to get wallet info for {user_id}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calling wallet_service.get_wallet_info: {e}")
            return None

    async def check_wallet_exists(self, user_id: str) -> bool:
        """
        Check if a wallet exists for a user

        Args:
            user_id: User ID

        Returns:
            True if wallet exists, False otherwise
        """
        wallet = await self.get_wallet_info(user_id)
        return wallet is not None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
