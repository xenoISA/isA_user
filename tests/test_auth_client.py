#!/usr/bin/env python3
"""
Test script for auth_client.py functionality
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.auth_client import UnifiedAuthClient, quick_verify_token
from core.config_manager import ConfigManager

# Get gateway URL from config
config_manager = ConfigManager("gateway")
config = config_manager.get_service_config()
GATEWAY_URL = config.gateway_url or "http://localhost:8100"

async def test_auth_client():
    """Test the auth client functionality"""
    print("Testing UnifiedAuthClient...")
    
    # Test 1: Check service health
    print("\n1. Testing service health check...")
    async with UnifiedAuthClient(GATEWAY_URL) as client:
        try:
            health = await client.check_service_health()
            print(f"   Auth service health: {health}")
        except Exception as e:
            print(f"   Health check failed: {e}")
    
    # Test 2: Test invalid token
    print("\n2. Testing invalid token verification...")
    async with UnifiedAuthClient(GATEWAY_URL) as client:
        try:
            result = await client.verify_token("invalid_token_12345")
            print(f"   Result: {result.result}")
            print(f"   Error: {result.error}")
        except Exception as e:
            print(f"   Token verification failed: {e}")
    
    # Test 3: Test API key verification
    print("\n3. Testing API key verification...")
    async with UnifiedAuthClient(GATEWAY_URL) as client:
        try:
            result = await client.verify_api_key("test_api_key", user_id="test_user")
            print(f"   Result: {result.result}")
            print(f"   Error: {result.error}")
        except Exception as e:
            print(f"   API key verification failed: {e}")
    
    # Test 4: Test user context resolution
    print("\n4. Testing user context resolution...")
    async with UnifiedAuthClient(GATEWAY_URL) as client:
        try:
            context = await client.resolve_user_context("test_user_123")
            print(f"   User ID: {context.user_id}")
            print(f"   Authenticated: {context.authenticated}")
            print(f"   Auth source: {context.auth_source}")
        except Exception as e:
            print(f"   User context resolution failed: {e}")
    
    # Test 5: Test quick verify function
    print("\n5. Testing quick verify token function...")
    try:
        context = await quick_verify_token("test_token", GATEWAY_URL)
        if context:
            print(f"   Quick verify successful: {context.user_id}")
        else:
            print("   Quick verify returned None (expected for invalid token)")
    except Exception as e:
        print(f"   Quick verify failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth_client())