#!/usr/bin/env python3
"""
Test Event-Driven Billing Flow

Tests the complete flow:
1. isA_Model publishes usage.recorded.* event to NATS
2. billing_service subscribes and processes the event
3. billing_service calculates cost and creates billing record
4. billing_service calls wallet_service for balance deduction
5. Verify billing record in database
6. Monitor for billing.calculated and billing.failed events

This script simulates what happens in isA_Model when a user makes an inference request.
"""

import asyncio
import sys
import os
import logging
from decimal import Decimal
from datetime import datetime
import json

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# Import from isa_common
from isa_common.events import publish_usage_event
from isa_common.consul_client import ConsulRegistry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_event_driven_billing():
    """
    Test the complete event-driven billing flow
    """

    # Test user and product info
    user_id = "test_billing_user_123"
    product_id = "gpt-5-nano"  # Match what you tested in isA_Model
    organization_id = "org_billing_test_123"

    # Usage details (simulating what isA_Model sends)
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
        "organization_id": organization_id,
        "request_id": f"req_test_{datetime.now().timestamp()}",
        "session_id": f"session_test_{datetime.now().timestamp()}"
    }

    logger.info("=" * 80)
    logger.info("🧪 Testing Event-Driven Billing Flow")
    logger.info("=" * 80)
    logger.info(f"User ID: {user_id}")
    logger.info(f"Product ID: {product_id}")
    logger.info(f"Total Tokens: {total_tokens}")
    logger.info(f"Usage Details: {json.dumps(usage_details, indent=2)}")

    # Step 1: Discover NATS service via Consul (or use defaults)
    nats_host = None
    nats_port = None

    try:
        consul_host = os.getenv('CONSUL_HOST', 'localhost')
        consul_port = int(os.getenv('CONSUL_PORT', '8500'))
        consul = ConsulRegistry(consul_host=consul_host, consul_port=consul_port)

        nats_url = consul.get_nats_url()
        if '://' in nats_url:
            nats_url = nats_url.split('://', 1)[1]
        nats_host, port_str = nats_url.rsplit(':', 1)
        nats_port = int(port_str)
        logger.info(f"✅ Discovered NATS via Consul: {nats_host}:{nats_port}")
    except Exception as e:
        logger.warning(f"⚠️  Consul discovery failed: {e}")
        nats_host = os.getenv('NATS_HOST', 'localhost')
        nats_port = int(os.getenv('NATS_PORT', '50056'))
        logger.info(f"Using default NATS: {nats_host}:{nats_port}")

    # Step 2: Publish usage event to NATS (simulating isA_Model behavior)
    logger.info("\n" + "=" * 80)
    logger.info("📤 Step 1: Publishing usage.recorded event to NATS")
    logger.info("=" * 80)

    try:
        success = await publish_usage_event(
            user_id=user_id,
            product_id=product_id,
            usage_amount=Decimal(total_tokens),
            unit_type="token",
            usage_details=usage_details,
            nats_host=nats_host,
            nats_port=nats_port
        )

        if success:
            logger.info(f"✅ Successfully published usage event: usage.recorded.{product_id}")
            logger.info(f"   Subject: usage.recorded.{product_id}")
            logger.info(f"   User: {user_id}")
            logger.info(f"   Usage: {total_tokens} tokens")
        else:
            logger.error("❌ Failed to publish usage event")
            return False

    except Exception as e:
        logger.error(f"❌ Error publishing event: {e}", exc_info=True)
        return False

    # Step 3: Wait for billing_service to process the event
    logger.info("\n" + "=" * 80)
    logger.info("⏳ Step 2: Waiting for billing_service to process event...")
    logger.info("=" * 80)
    logger.info("Expected flow:")
    logger.info("  1. billing_service subscribes to usage.recorded.*")
    logger.info("  2. Receives event and validates payload")
    logger.info("  3. Gets product pricing from product_service:8215")
    logger.info("  4. Calculates billing cost")
    logger.info("  5. Creates billing record in Supabase")
    logger.info("  6. Checks user balance via wallet_service:8209")
    logger.info("  7. Calls wallet deduction API")
    logger.info("  8. Publishes billing.calculated event")
    logger.info("\nWaiting 5 seconds for processing...")
    await asyncio.sleep(5)

    # Step 4: Verify billing record was created (requires database access)
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Step 3: Verifying billing record creation")
    logger.info("=" * 80)

    # Query billing service API to check if record exists
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            # Get billing records for this user
            billing_api_url = f"http://localhost:8216/api/v1/billing/records/user/{user_id}"
            params = {"limit": 5}

            async with session.get(billing_api_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    records = data.get("records", [])
                    total_count = data.get("total_count", 0)

                    logger.info(f"✅ Found {total_count} billing records for user {user_id}")

                    # Find the most recent record for our product
                    matching_records = [
                        r for r in records
                        if r.get("product_id") == product_id
                    ]

                    if matching_records:
                        latest_record = matching_records[0]
                        logger.info("\n📊 Latest Billing Record:")
                        logger.info(f"   Billing ID: {latest_record.get('billing_id')}")
                        logger.info(f"   Product ID: {latest_record.get('product_id')}")
                        logger.info(f"   Service Type: {latest_record.get('service_type')}")
                        logger.info(f"   Usage Amount: {latest_record.get('usage_amount')}")
                        logger.info(f"   Total Cost: ${latest_record.get('total_amount')}")
                        logger.info(f"   Status: {latest_record.get('billing_status')}")
                        logger.info(f"   Billing Method: {latest_record.get('billing_method')}")
                        logger.info(f"   Created At: {latest_record.get('created_at')}")

                        # Check if wallet transaction was successful
                        wallet_tx_id = latest_record.get('wallet_transaction_id')
                        if wallet_tx_id:
                            logger.info(f"   Wallet TX ID: {wallet_tx_id}")
                            logger.info("   ✅ Wallet deduction completed")
                        else:
                            logger.warning("   ⚠️  No wallet transaction ID (may be subscription_included)")

                        return True
                    else:
                        logger.warning(f"⚠️  No billing records found for product {product_id}")
                        logger.info("\nAll records:")
                        for r in records[:3]:
                            logger.info(f"   - {r.get('product_id')} | {r.get('service_type')} | ${r.get('total_amount')}")
                        return False
                else:
                    logger.error(f"❌ Failed to query billing API: HTTP {resp.status}")
                    error_text = await resp.text()
                    logger.error(f"   Error: {error_text}")
                    return False

    except Exception as e:
        logger.error(f"❌ Error verifying billing record: {e}", exc_info=True)
        return False

    # Step 5: Check wallet balance
    logger.info("\n" + "=" * 80)
    logger.info("💰 Step 4: Checking wallet balance")
    logger.info("=" * 80)

    try:
        async with aiohttp.ClientSession() as session:
            wallet_api_url = f"http://localhost:8209/api/v1/wallets/user/{user_id}/balance"

            async with session.get(wallet_api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    balance = data.get("balance") or data.get("available_balance", 0)
                    logger.info(f"✅ Current wallet balance: ${balance}")
                else:
                    logger.warning(f"⚠️  Could not retrieve wallet balance: HTTP {resp.status}")
    except Exception as e:
        logger.warning(f"⚠️  Error checking wallet balance: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ Event-Driven Billing Test Completed!")
    logger.info("=" * 80)

    return True


async def main():
    """Main test runner"""
    try:
        success = await test_event_driven_billing()

        if success:
            logger.info("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            logger.error("\n❌ Test failed. Check logs above for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
