"""
Blockchain Integration for Payment Service

Example of how a microservice integrates with blockchain functionality
through the API Gateway.
"""

from fastapi import HTTPException, Depends
from typing import Optional
import logging
from decimal import Decimal
import sys
import os

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.blockchain_client import BlockchainClient, InsufficientBalanceError, TransactionFailedError
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Note: Gateway URL should be obtained from config as it's an external service
# For blockchain integration, we still need the gateway URL from config
config_manager = ConfigManager("payment_service")
config = config_manager.get_service_config()
gateway_url = config.gateway_url  # Gateway is external, not discovered via Consul

if not gateway_url:
    logger.warning("Gateway URL not configured, blockchain features will be unavailable")
    blockchain_client = None
else:
    # Initialize blockchain client (singleton)
    blockchain_client = BlockchainClient(
        gateway_url=gateway_url,
        auth_token=None  # Will be set from auth service
    )


async def process_blockchain_payment(
    user_address: str,
    amount: str,
    order_id: str,
    service_id: str
) -> dict:
    """
    Process a payment using blockchain
    
    Args:
        user_address: User's blockchain address
        amount: Payment amount in wei
        order_id: Order ID for this payment
        service_id: Service being paid for
    
    Returns:
        Payment transaction details
    """
    try:
        # 1. Check user balance
        balance_info = await blockchain_client.get_balance(user_address)
        user_balance = Decimal(balance_info.get("balance", "0"))
        required_amount = Decimal(amount)
        
        if user_balance < required_amount:
            raise InsufficientBalanceError(
                f"Insufficient balance. Required: {amount}, Available: {user_balance}"
            )
        
        # 2. Process payment
        tx_result = await blockchain_client.charge_for_service(
            user_address=user_address,
            amount=amount,
            service_id=f"{service_id}:{order_id}"
        )
        
        # 3. Store transaction in database
        # This would normally save to your payment database
        payment_record = {
            "order_id": order_id,
            "user_address": user_address,
            "amount": amount,
            "service_id": service_id,
            "tx_hash": tx_result.get("transaction_hash"),
            "status": "pending"
        }
        
        # 4. Return transaction details
        return {
            "success": True,
            "order_id": order_id,
            "transaction_hash": tx_result.get("transaction_hash"),
            "status": tx_result.get("status"),
            "payment_record": payment_record
        }
        
    except InsufficientBalanceError as e:
        logger.error(f"Insufficient balance for payment: {e}")
        raise HTTPException(status_code=402, detail=str(e))
        
    except Exception as e:
        logger.error(f"Blockchain payment failed: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")


async def verify_blockchain_payment(tx_hash: str, expected_amount: str) -> bool:
    """
    Verify a blockchain payment transaction
    
    Args:
        tx_hash: Transaction hash to verify
        expected_amount: Expected payment amount
        
    Returns:
        True if payment is verified
    """
    try:
        return await blockchain_client.verify_payment(tx_hash, expected_amount)
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        return False


async def issue_refund(
    user_address: str,
    amount: str,
    order_id: str,
    reason: str
) -> dict:
    """
    Issue a refund to user via blockchain
    
    Args:
        user_address: User's blockchain address
        amount: Refund amount
        order_id: Original order ID
        reason: Reason for refund
        
    Returns:
        Refund transaction details
    """
    try:
        # Process refund as a reward transaction
        tx_result = await blockchain_client.reward_user(
            user_address=user_address,
            amount=amount,
            reason=f"refund:{order_id}:{reason}"
        )
        
        return {
            "success": True,
            "order_id": order_id,
            "refund_tx_hash": tx_result.get("transaction_hash"),
            "status": tx_result.get("status")
        }
        
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        raise HTTPException(status_code=500, detail="Refund processing failed")


async def check_subscription_status(user_address: str, service_id: str) -> dict:
    """
    Check if user has an active subscription (via blockchain NFT or balance)
    
    Args:
        user_address: User's blockchain address
        service_id: Service to check subscription for
        
    Returns:
        Subscription status details
    """
    try:
        # Check if user has access to the service
        has_access = await blockchain_client.check_service_access(
            user_address=user_address,
            service_id=service_id
        )
        
        # Get current balance
        balance_info = await blockchain_client.get_balance(user_address)
        
        return {
            "has_access": has_access,
            "service_id": service_id,
            "user_address": user_address,
            "current_balance": balance_info.get("balance"),
            "balance_eth": balance_info.get("eth")
        }
        
    except Exception as e:
        logger.error(f"Subscription check failed: {e}")
        return {
            "has_access": False,
            "service_id": service_id,
            "user_address": user_address,
            "error": str(e)
        }


# FastAPI route examples
from fastapi import APIRouter

blockchain_router = APIRouter(prefix="/blockchain", tags=["blockchain"])


@blockchain_router.post("/payment")
async def create_blockchain_payment(
    user_address: str,
    amount: str,
    order_id: str,
    service_id: str
):
    """Process a blockchain payment"""
    return await process_blockchain_payment(
        user_address=user_address,
        amount=amount,
        order_id=order_id,
        service_id=service_id
    )


@blockchain_router.get("/payment/{tx_hash}/verify")
async def verify_payment(tx_hash: str, amount: str):
    """Verify a payment transaction"""
    is_valid = await verify_blockchain_payment(tx_hash, amount)
    return {
        "transaction_hash": tx_hash,
        "verified": is_valid,
        "expected_amount": amount
    }


@blockchain_router.post("/refund")
async def create_refund(
    user_address: str,
    amount: str,
    order_id: str,
    reason: str = "Customer request"
):
    """Issue a blockchain refund"""
    return await issue_refund(
        user_address=user_address,
        amount=amount,
        order_id=order_id,
        reason=reason
    )


@blockchain_router.get("/subscription/{user_address}/{service_id}")
async def get_subscription_status(user_address: str, service_id: str):
    """Check subscription status via blockchain"""
    return await check_subscription_status(user_address, service_id)