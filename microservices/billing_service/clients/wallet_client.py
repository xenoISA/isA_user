"""
Wallet Service Client for Billing Service

Handles wallet-related operations: balance checks, credit consumption, deposits
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WalletClient:
    """Client for communicating with Wallet Service"""

    def __init__(self):
        """Initialize Wallet Service client"""
        try:
            import os
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

            from microservices.wallet_service.client import WalletServiceClient

            self.client = WalletServiceClient()
            logger.info("✅ WalletClient initialized with WalletServiceClient")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize WalletServiceClient: {e}")
            self.client = None

    async def get_balance(self, user_id: str) -> Optional[Decimal]:
        """
        Get user's wallet balance

        Args:
            user_id: User ID

        Returns:
            Balance as Decimal, or None if failed
        """
        try:
            if self.client:
                result = await self.client.get_user_credit_balance(user_id)
                if result and result.get("success"):
                    return Decimal(str(result.get("balance", 0)))

            logger.warning("WalletServiceClient not available")
            return None

        except Exception as e:
            logger.error(f"Failed to get balance for user {user_id}: {e}")
            return None

    async def consume_credits(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Consume credits from user's wallet

        Args:
            user_id: User ID
            amount: Amount to consume
            description: Transaction description
            metadata: Additional metadata

        Returns:
            Transaction result dict or None if failed
        """
        try:
            if self.client:
                result = await self.client.consume_user_credits(
                    user_id=user_id,
                    amount=float(amount),
                    description=description,
                    metadata=metadata or {},
                )

                if result and result.get("success"):
                    return result

            logger.warning("WalletServiceClient not available")
            return None

        except Exception as e:
            logger.error(f"Failed to consume credits for user {user_id}: {e}")
            return None

    async def deposit_credits(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Deposit credits to user's wallet

        Args:
            user_id: User ID
            amount: Amount to deposit
            description: Transaction description
            reference_id: Reference ID (e.g., payment_id)
            metadata: Additional metadata

        Returns:
            Transaction result dict or None if failed
        """
        try:
            if not self.client:
                logger.warning("WalletServiceClient not available")
                return None

            # Get user's wallets first
            wallets = await self.client.get_user_wallets(user_id)
            if not wallets or wallets.get("count", 0) == 0:
                logger.error(f"No wallet found for user {user_id}")
                return None

            wallet_id = wallets["wallets"][0]["wallet_id"]

            # Deposit to wallet
            result = await self.client.deposit_to_wallet(
                wallet_id=wallet_id,
                amount=float(amount),
                description=description,
                reference_id=reference_id,
                metadata=metadata or {},
            )

            if result and result.get("success"):
                return result

            return None

        except Exception as e:
            logger.error(f"Failed to deposit credits for user {user_id}: {e}")
            return None
