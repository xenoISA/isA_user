#!/usr/bin/env python3
"""
Simple Event-Driven Billing Test

Uses gRPC NATS client directly to publish usage events and verify billing.
This simulates what isA_Model does when publishing billing events.
"""

import asyncio
import sys
import os
import logging
from decimal import Decimal
from datetime import datetime
import json
import grpc

# Add parent directory to path for gRPC imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import gRPC NATS client
sys.path.insert(0, '/app')  # For Docker container
from core.grpc_clients import nats_pb2, nats_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def publish_usage_event_via_grpc(
    user_id: str,
    product_id: str,
    usage_amount: Decimal,
    unit_type: str,
    usage_details: dict,
    nats_host: str = 'localhost',
    nats_port: int = 50056
):
    """
    Publish usage event directly via gRPC NATS client
    """
    try:
        # Create gRPC channel
        channel = grpc.aio.insecure_channel(f'{nats_host}:{nats_port}')
        stub = nats_pb2_grpc.NATSServiceStub(channel)

        # Prepare event payload
        event_data = {
            "user_id": user_id,
            "product_id": product_id,
            "usage_amount": str(usage_amount),
            "unit_type": unit_type,
            "usage_details": usage_details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Subject follows the pattern: usage.recorded.{product_id}
        subject = f"usage.recorded.{product_id}"

        # Publish request
        request = nats_pb2.PublishRequest(
            subject=subject,
            data=json.dumps(event_data).encode('utf-8'),
            user_id=user_id
        )

        logger.info(f"Publishing to subject: {subject}")
        logger.info(f"Event data: {json.dumps(event_data, indent=2)}")

        # Send publish request
        response = await stub.Publish(request)

        if response.success:
            logger.info(f"✅ Successfully published event to NATS")
            logger.info(f"   Message ID: {response.message_id}")
            return True
        else:
            logger.error(f"❌ Failed to publish event: {response.error}")
            return False

    except Exception as e:
        logger.error(f"❌ Error publishing event via gRPC: {e}", exc_info=True)
        return False
    finally:
        await channel.close()


async def verify_billing_record(user_id: str, product_id: str):
    """
    Verify that billing record was created
    """
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            url = f"http://localhost:8216/api/v1/billing/records/user/{user_id}"
            params = {"limit": 5}

            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    records = data.get("records", [])
                    total_count = data.get("total_count", 0)

                    logger.info(f"\n📊 Billing Records: {total_count} total")

                    # Find matching record
                    for record in records:
                        if record.get("product_id") == product_id:
                            logger.info("\n✅ Found matching billing record:")
                            logger.info(f"   Billing ID: {record.get('billing_id')}")
                            logger.info(f"   Product: {record.get('product_id')}")
                            logger.info(f"   Usage: {record.get('usage_amount')}")
                            logger.info(f"   Cost: ${record.get('total_amount')}")
                            logger.info(f"   Status: {record.get('billing_status')}")
                            logger.info(f"   Method: {record.get('billing_method')}")

                            wallet_tx = record.get('wallet_transaction_id')
                            if wallet_tx:
                                logger.info(f"   Wallet TX: {wallet_tx}")

                            return True

                    logger.warning(f"⚠️  No billing record found for product: {product_id}")
                    return False
                else:
                    error = await resp.text()
                    logger.error(f"❌ API error: HTTP {resp.status} - {error}")
                    return False

    except Exception as e:
        logger.error(f"❌ Error verifying billing: {e}")
        return False


async def main():
    """
    Main test flow
    """
    logger.info("=" * 80)
    logger.info("🧪 Event-Driven Billing Test")
    logger.info("=" * 80)

    # Test parameters
    user_id = "test_billing_user_123"
    product_id = "gpt-5-nano"
    input_tokens = 50
    output_tokens = 150
    total_tokens = input_tokens + output_tokens

    usage_details = {
        "provider": "openai",
        "model": product_id,
        "operation": "chat_completion",
        "service_type": "text",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "organization_id": "org_billing_test_123"
    }

    logger.info(f"\nTest Parameters:")
    logger.info(f"  User: {user_id}")
    logger.info(f"  Product: {product_id}")
    logger.info(f"  Tokens: {total_tokens}")

    # Step 1: Publish event
    logger.info("\n" + "-" * 80)
    logger.info("📤 Step 1: Publishing usage event to NATS")
    logger.info("-" * 80)

    nats_host = os.getenv('NATS_HOST', 'localhost')
    nats_port = int(os.getenv('NATS_PORT', '50056'))

    success = await publish_usage_event_via_grpc(
        user_id=user_id,
        product_id=product_id,
        usage_amount=Decimal(total_tokens),
        unit_type="token",
        usage_details=usage_details,
        nats_host=nats_host,
        nats_port=nats_port
    )

    if not success:
        logger.error("\n❌ Failed to publish event")
        return False

    # Step 2: Wait for processing
    logger.info("\n" + "-" * 80)
    logger.info("⏳ Step 2: Waiting for billing_service to process...")
    logger.info("-" * 80)
    logger.info("  Expected: billing_service subscribes to usage.recorded.*")
    logger.info("  Process: calculate cost → create record → deduct wallet")
    await asyncio.sleep(3)

    # Step 3: Verify billing record
    logger.info("\n" + "-" * 80)
    logger.info("🔍 Step 3: Verifying billing record")
    logger.info("-" * 80)

    verified = await verify_billing_record(user_id, product_id)

    logger.info("\n" + "=" * 80)
    if verified:
        logger.info("✅ Test PASSED: Event-driven billing flow works!")
    else:
        logger.error("❌ Test FAILED: No billing record created")
    logger.info("=" * 80)

    return verified


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)
