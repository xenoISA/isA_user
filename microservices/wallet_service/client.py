"""
Wallet Service Client

Client library for other microservices to interact with wallet service
"""

import httpx
from core.config_manager import ConfigManager
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class WalletServiceClient:
    """Wallet Service HTTP client"""

    def __init__(self, base_url: str = None, config: Optional[ConfigManager] = None):
        """
        Initialize Wallet Service client

        Args:
            base_url: Wallet service base URL, defaults to service discovery
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via ConfigManager
            if config is None:
                config = ConfigManager("wallet_service_client")

            try:
                host, port = config.discover_service(
                    service_name='wallet_service',
                    default_host='localhost',
                    default_port=8208,
                    env_host_key='WALLET_SERVICE_HOST',
                    env_port_key='WALLET_SERVICE_PORT'
                )
                self.base_url = f"http://{host}:{port}"
                logger.info(f"Wallet service discovered at {self.base_url}")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8208"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Wallet Management
    # =============================================================================

    async def create_wallet(
        self,
        user_id: str,
        currency: str = "USD",
        wallet_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new wallet

        Args:
            user_id: User ID
            currency: Currency code (USD, EUR, CREDIT, etc.)
            wallet_type: Wallet type (user, organization, system)
            metadata: Additional metadata (optional)

        Returns:
            Created wallet

        Example:
            >>> client = WalletServiceClient()
            >>> wallet = await client.create_wallet(
            ...     user_id="user123",
            ...     currency="USD",
            ...     wallet_type="user"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "currency": currency,
                "wallet_type": wallet_type
            }

            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallets",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create wallet: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return None

    async def get_wallet(
        self,
        wallet_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get wallet by ID

        Args:
            wallet_id: Wallet ID

        Returns:
            Wallet details

        Example:
            >>> wallet = await client.get_wallet("wallet123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallets/{wallet_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get wallet: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet: {e}")
            return None

    async def get_user_wallets(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get all wallets for user

        Args:
            user_id: User ID

        Returns:
            List of wallets

        Example:
            >>> wallets = await client.get_user_wallets("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/wallets"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user wallets: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user wallets: {e}")
            return None

    async def get_wallet_balance(
        self,
        wallet_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get wallet balance

        Args:
            wallet_id: Wallet ID

        Returns:
            Wallet balance info

        Example:
            >>> balance = await client.get_wallet_balance("wallet123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/balance"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get wallet balance: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return None

    # =============================================================================
    # Wallet Operations
    # =============================================================================

    async def deposit(
        self,
        wallet_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Deposit funds to wallet

        Args:
            wallet_id: Wallet ID
            amount: Amount to deposit
            description: Transaction description
            reference_id: External reference ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Updated wallet

        Example:
            >>> result = await client.deposit(
            ...     wallet_id="wallet123",
            ...     amount=100.00,
            ...     description="Payment received",
            ...     reference_id="payment_456"
            ... )
        """
        try:
            payload = {
                "amount": amount,
                "description": description
            }

            if reference_id:
                payload["reference_id"] = reference_id
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/deposit",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to deposit: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error depositing: {e}")
            return None

    async def withdraw(
        self,
        wallet_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Withdraw funds from wallet

        Args:
            wallet_id: Wallet ID
            amount: Amount to withdraw
            description: Transaction description
            reference_id: External reference ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Updated wallet

        Example:
            >>> result = await client.withdraw(
            ...     wallet_id="wallet123",
            ...     amount=50.00,
            ...     description="Payout to bank"
            ... )
        """
        try:
            payload = {
                "amount": amount,
                "description": description
            }

            if reference_id:
                payload["reference_id"] = reference_id
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/withdraw",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to withdraw: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error withdrawing: {e}")
            return None

    async def consume_credits(
        self,
        wallet_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Consume credits from wallet

        Args:
            wallet_id: Wallet ID
            amount: Amount of credits to consume
            description: Transaction description
            reference_id: External reference ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Updated wallet

        Example:
            >>> result = await client.consume_credits(
            ...     wallet_id="wallet123",
            ...     amount=10.0,
            ...     description="API usage"
            ... )
        """
        try:
            payload = {
                "amount": amount,
                "description": description
            }

            if reference_id:
                payload["reference_id"] = reference_id
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/consume",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to consume credits: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            return None

    async def consume_user_credits(
        self,
        user_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Consume credits from user's default credit wallet

        Args:
            user_id: User ID
            amount: Amount of credits to consume
            description: Transaction description
            reference_id: External reference ID (optional)

        Returns:
            Updated wallet

        Example:
            >>> result = await client.consume_user_credits(
            ...     user_id="user123",
            ...     amount=5.0,
            ...     description="Storage usage"
            ... )
        """
        try:
            payload = {
                "amount": amount,
                "description": description
            }

            if reference_id:
                payload["reference_id"] = reference_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/users/{user_id}/credits/consume",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to consume user credits: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error consuming user credits: {e}")
            return None

    async def transfer(
        self,
        wallet_id: str,
        to_wallet_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Transfer funds between wallets

        Args:
            wallet_id: Source wallet ID
            to_wallet_id: Destination wallet ID
            amount: Amount to transfer
            description: Transaction description
            reference_id: External reference ID (optional)

        Returns:
            Transfer result

        Example:
            >>> result = await client.transfer(
            ...     wallet_id="wallet123",
            ...     to_wallet_id="wallet456",
            ...     amount=25.00,
            ...     description="Transfer to friend"
            ... )
        """
        try:
            payload = {
                "to_wallet_id": to_wallet_id,
                "amount": amount,
                "description": description
            }

            if reference_id:
                payload["reference_id"] = reference_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/transfer",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to transfer: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error transferring: {e}")
            return None

    async def refund_transaction(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Refund a transaction

        Args:
            transaction_id: Transaction ID to refund
            reason: Refund reason (optional)

        Returns:
            Refund result

        Example:
            >>> result = await client.refund_transaction(
            ...     transaction_id="txn123",
            ...     reason="Customer request"
            ... )
        """
        try:
            payload = {}
            if reason:
                payload["reason"] = reason

            response = await self.client.post(
                f"{self.base_url}/api/v1/transactions/{transaction_id}/refund",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refund transaction: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error refunding transaction: {e}")
            return None

    # =============================================================================
    # Transactions & History
    # =============================================================================

    async def get_wallet_transactions(
        self,
        wallet_id: str,
        transaction_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Get wallet transactions

        Args:
            wallet_id: Wallet ID
            transaction_type: Filter by transaction type (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            page: Page number (default: 1)
            page_size: Items per page (default: 50)

        Returns:
            List of transactions with pagination

        Example:
            >>> transactions = await client.get_wallet_transactions("wallet123")
        """
        try:
            params = {
                "page": page,
                "page_size": page_size
            }

            if transaction_type:
                params["transaction_type"] = transaction_type
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            response = await self.client.get(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/transactions",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get wallet transactions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet transactions: {e}")
            return None

    async def get_user_transactions(
        self,
        user_id: str,
        transaction_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Get all user transactions across all wallets

        Args:
            user_id: User ID
            transaction_type: Filter by transaction type (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            page: Page number (default: 1)
            page_size: Items per page (default: 50)

        Returns:
            List of transactions with pagination

        Example:
            >>> transactions = await client.get_user_transactions("user123")
        """
        try:
            params = {
                "page": page,
                "page_size": page_size
            }

            if transaction_type:
                params["transaction_type"] = transaction_type
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/transactions",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user transactions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return None

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_wallet_statistics(
        self,
        wallet_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get wallet statistics

        Args:
            wallet_id: Wallet ID

        Returns:
            Wallet statistics

        Example:
            >>> stats = await client.get_wallet_statistics("wallet123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallets/{wallet_id}/statistics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get wallet statistics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet statistics: {e}")
            return None

    async def get_user_statistics(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user statistics across all wallets

        Args:
            user_id: User ID

        Returns:
            User wallet statistics

        Example:
            >>> stats = await client.get_user_statistics("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/statistics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user statistics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return None

    async def get_user_credit_balance(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's credit balance

        Args:
            user_id: User ID

        Returns:
            Credit balance info

        Example:
            >>> balance = await client.get_user_credit_balance("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/credits/balance"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get credit balance: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting credit balance: {e}")
            return None

    async def get_wallet_stats(
        self
    ) -> Optional[Dict[str, Any]]:
        """
        Get wallet service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_wallet_stats()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallet/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get wallet stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["WalletServiceClient"]
