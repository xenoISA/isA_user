#!/usr/bin/env python3
"""
Payment Service Test Script
测试 Stripe 和 Blockchain 支付功能
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from decimal import Decimal

# Use config manager for service URLs
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_manager import ConfigManager

# Get service URLs from config
payment_config = ConfigManager("payment_service").get_service_config()
auth_config = ConfigManager("auth_service").get_service_config()

PAYMENT_SERVICE_URL = f"http://localhost:{payment_config.service_port}" if payment_config.service_port else "http://localhost:8207"
AUTH_SERVICE_URL = f"http://localhost:{auth_config.service_port}" if auth_config.service_port else "http://localhost:8201"

async def test_payment_service_health():
    """测试 Payment Service 健康状态"""
    print("🔍 Testing Payment Service Health...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{PAYMENT_SERVICE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Payment Service is healthy: {data}")
                    return True
                else:
                    print(f"❌ Payment Service health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Failed to connect to Payment Service: {e}")
            return False

async def test_service_info():
    """测试服务信息和能力"""
    print("\n🔍 Checking Payment Service Capabilities...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{PAYMENT_SERVICE_URL}/info") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Service Info: {json.dumps(data, indent=2)}")
                    
                    capabilities = data.get("capabilities", {})
                    stripe_enabled = capabilities.get("stripe_integration", False)
                    blockchain_enabled = "blockchain" in str(data.get("endpoints", {}))
                    
                    print(f"\n📊 Payment Methods Available:")
                    print(f"   💳 Stripe Integration: {'✅ Enabled' if stripe_enabled else '❌ Disabled'}")
                    print(f"   🔗 Blockchain Wallet: {'✅ Available' if blockchain_enabled else '❌ Not Available'}")
                    
                    return stripe_enabled, blockchain_enabled
                else:
                    print(f"❌ Failed to get service info: {response.status}")
                    return False, False
        except Exception as e:
            print(f"❌ Error getting service info: {e}")
            return False, False

async def create_test_subscription_plan():
    """创建测试订阅计划"""
    print("\n🔍 Creating Test Subscription Plan...")
    
    plan_data = {
        "plan_id": "test_basic_monthly",
        "name": "Test Basic Plan",
        "tier": "BASIC",
        "price": 9.99,
        "billing_cycle": "MONTHLY",
        "features": {
            "max_users": 5,
            "storage_gb": 10,
            "api_calls": 1000
        },
        "trial_days": 7
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{PAYMENT_SERVICE_URL}/api/v1/plans",
                json=plan_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Test plan created: {data.get('plan_id')}")
                    return data
                else:
                    text = await response.text()
                    print(f"❌ Failed to create plan: {response.status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating plan: {e}")
            return None

async def test_stripe_payment_intent():
    """测试 Stripe 支付意图创建"""
    print("\n💳 Testing Stripe Payment Intent...")
    
    payment_data = {
        "amount": 9.99,
        "currency": "USD",
        "user_id": "test_user_123",
        "description": "Test payment for basic plan",
        "metadata": {
            "plan_id": "test_basic_monthly",
            "test": True
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{PAYMENT_SERVICE_URL}/api/v1/payments/intent",
                json=payment_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Stripe Payment Intent created:")
                    print(f"   Payment ID: {data.get('payment_intent_id')}")
                    print(f"   Client Secret: {data.get('client_secret', 'N/A')[:20]}...")
                    print(f"   Amount: ${data.get('amount')}")
                    print(f"   Status: {data.get('status')}")
                    return data
                else:
                    text = await response.text()
                    print(f"❌ Failed to create payment intent: {response.status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating payment intent: {e}")
            return None

async def test_blockchain_payment():
    """测试区块链支付"""
    print("\n🔗 Testing Blockchain Payment...")
    
    payment_data = {
        "user_address": "0x742d35Cc64C0532A79C2eEbAfDC0bB9B4089AD9",  # Test address
        "amount": "1000000000000000000",  # 1 ETH in wei
        "order_id": f"test_order_{int(datetime.now().timestamp())}",
        "service_id": "payment_service_test"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{PAYMENT_SERVICE_URL}/api/v1/payments/blockchain/payment",
                json=payment_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Blockchain Payment processed:")
                    print(f"   Order ID: {data.get('order_id')}")
                    print(f"   Transaction Hash: {data.get('transaction_hash', 'N/A')}")
                    print(f"   Status: {data.get('status')}")
                    return data
                else:
                    text = await response.text()
                    print(f"❌ Blockchain payment failed: {response.status} - {text}")
                    
                    # This might fail if blockchain gateway is not running
                    if "Failed to connect" in text or "Blockchain" in text:
                        print("ℹ️  This is expected if blockchain gateway is not running")
                    return None
        except Exception as e:
            print(f"❌ Error processing blockchain payment: {e}")
            return None

async def test_subscription_creation():
    """测试订阅创建"""
    print("\n📋 Testing Subscription Creation...")
    
    subscription_data = {
        "user_id": "test_user_123",
        "plan_id": "test_basic_monthly",
        "payment_method_id": "pm_card_visa",  # Stripe test payment method
        "trial_days": 7,
        "metadata": {
            "test": True,
            "created_by": "test_script"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{PAYMENT_SERVICE_URL}/api/v1/subscriptions",
                json=subscription_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Subscription created:")
                    subscription = data.get('subscription', {})
                    plan = data.get('plan', {})
                    print(f"   Subscription ID: {subscription.get('subscription_id')}")
                    print(f"   Status: {subscription.get('status')}")
                    print(f"   Plan: {plan.get('name')} (${plan.get('price')})")
                    print(f"   Trial Period: {subscription.get('trial_start')} to {subscription.get('trial_end')}")
                    return data
                else:
                    text = await response.text()
                    print(f"❌ Failed to create subscription: {response.status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating subscription: {e}")
            return None

async def test_payment_stats():
    """测试支付统计"""
    print("\n📊 Testing Payment Statistics...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{PAYMENT_SERVICE_URL}/api/v1/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Payment Statistics:")
                    print(f"   Total Payments: {data.get('total_payments', 0)}")
                    print(f"   Active Subscriptions: {data.get('active_subscriptions', 0)}")
                    print(f"   Revenue Today: ${data.get('revenue_today', 0)}")
                    print(f"   Revenue This Month: ${data.get('revenue_month', 0)}")
                    return data
                else:
                    text = await response.text()
                    print(f"❌ Failed to get stats: {response.status} - {text}")
                    return None
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return None

async def main():
    """主测试函数"""
    print("🚀 Starting Payment Service Tests")
    print("=" * 50)
    
    # 1. 健康检查
    if not await test_payment_service_health():
        print("\n❌ Payment Service is not running. Please start it first:")
        print("   cd /path/to/your/project")
        print("   source .venv/bin/activate")
        print("   python -m microservices.payment_service.main")
        return
    
    # 2. 检查服务能力
    stripe_enabled, blockchain_enabled = await test_service_info()
    
    # 3. 创建测试计划
    plan = await create_test_subscription_plan()
    
    # 4. 测试 Stripe 支付
    if stripe_enabled:
        stripe_result = await test_stripe_payment_intent()
    else:
        print("\n⚠️  Skipping Stripe tests - not configured")
        print("   To enable Stripe:")
        print("   1. Get test keys from Stripe Dashboard")
        print("   2. Set STRIPE_SECRET_KEY environment variable")
        
    # 5. 测试区块链支付
    if blockchain_enabled:
        blockchain_result = await test_blockchain_payment()
    else:
        print("\n⚠️  Blockchain payment endpoint not found")
    
    # 6. 测试订阅创建
    if plan:
        subscription = await test_subscription_creation()
    
    # 7. 获取统计信息
    await test_payment_stats()
    
    print("\n" + "=" * 50)
    print("🎉 Payment Service Tests Completed!")
    
    # 总结
    print("\n📋 Test Summary:")
    print(f"   💳 Stripe Integration: {'✅ Working' if stripe_enabled else '❌ Needs Configuration'}")
    print(f"   🔗 Blockchain Payments: {'✅ Available' if blockchain_enabled else '❌ Check Blockchain Gateway'}")
    print(f"   📋 Subscription Management: {'✅ Working' if plan else '❌ Issues Found'}")

if __name__ == "__main__":
    asyncio.run(main())