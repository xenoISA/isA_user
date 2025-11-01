#!/usr/bin/env python3
"""
Registration and Verification Flow Test

This script tests the complete registration and verification flow:
1. Start registration (get pending_registration_id)
2. Verify registration code (complete registration)
3. Verify the returned tokens

Usage:
    python test_registration_flow.py <email> <password> [name]

Example:
    python test_registration_flow.py test@example.com Test123! TestUser
"""

import asyncio
import sys
import os
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8201")

async def test_registration_flow(email: str, password: str, name: Optional[str] = None):
    """Test the complete registration and verification flow"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("Testing Auth Service Registration & Verification Flow")
        print("=" * 60)
        print(f"Email: {email}")
        print(f"Name: {name or email.split('@')[0]}")
        print(f"Auth Service URL: {AUTH_BASE_URL}")
        print()
        
        # Step 1: Start Registration
        print("[1/4] Starting registration...")
        try:
            register_response = await client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "name": name
                }
            )
            register_response.raise_for_status()
            register_data = register_response.json()
            
            print(f"✓ Registration started successfully")
            print(f"  Pending Registration ID: {register_data.get('pending_registration_id')}")
            print(f"  Expires At: {register_data.get('expires_at')}")
            
            pending_id = register_data.get('pending_registration_id')
            if not pending_id:
                print("❌ ERROR: No pending_registration_id returned")
                return False
                
        except httpx.HTTPStatusError as e:
            print(f"❌ Registration failed: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
        
        print()
        
        # Step 2: Get verification code (in development, we can use dev endpoint)
        print("[2/4] Getting verification code...")
        verification_code = None
        
        # Try to get code from dev endpoint (if available in debug mode)
        try:
            dev_response = await client.get(
                f"{AUTH_BASE_URL}/api/v1/auth/dev/pending-registration/{pending_id}"
            )
            if dev_response.status_code == 200:
                dev_data = dev_response.json()
                if not dev_data.get('expired') and dev_data.get('found'):
                    verification_code = dev_data.get('verification_code')
                    print(f"✓ Retrieved verification code from dev endpoint")
                    print(f"  Code: {verification_code}")
                elif dev_data.get('expired'):
                    print(f"⚠ Pending registration has expired")
                    return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                print("  Note: Dev endpoint not available (debug mode disabled)")
            elif e.response.status_code == 404:
                print("  Note: Dev endpoint returned 404")
            else:
                print(f"  Note: Dev endpoint error: {e.response.status_code}")
        
        # Fallback: Check environment variable or prompt user
        if not verification_code:
            verification_code = os.getenv("VERIFICATION_CODE")
            if not verification_code:
                import getpass
                print("  NOTE: Verification code should be sent via email.")
                print("  In development mode, check auth_service logs for the code.")
                verification_code = getpass.getpass("  Enter verification code (or set VERIFICATION_CODE env var): ").strip()
        
        if not verification_code:
            print("❌ ERROR: Verification code is required")
            return False
        
        if len(verification_code) != 6 or not verification_code.isdigit():
            print(f"⚠ Warning: Verification code should be 6 digits, got: {len(verification_code)} chars")
        
        print(f"  Using verification code: {verification_code[:2]}**{verification_code[-2:]}")
        print()
        
        # Step 3: Verify Registration
        print("[3/4] Verifying registration...")
        try:
            verify_response = await client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/verify",
                json={
                    "pending_registration_id": pending_id,
                    "code": verification_code
                }
            )
            
            if verify_response.status_code != 200:
                print(f"❌ Verification failed: {verify_response.status_code}")
                error_data = verify_response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                return False
            
            verify_data = verify_response.json()
            
            if not verify_data.get('success'):
                print(f"❌ Verification failed: {verify_data.get('error', 'Unknown error')}")
                return False
            
            print(f"✓ Verification successful!")
            print(f"  User ID: {verify_data.get('user_id')}")
            print(f"  Email: {verify_data.get('email')}")
            print(f"  Token Type: {verify_data.get('token_type')}")
            print(f"  Expires In: {verify_data.get('expires_in')} seconds")
            
            access_token = verify_data.get('access_token')
            refresh_token = verify_data.get('refresh_token')
            
            if not access_token:
                print("❌ ERROR: No access_token returned")
                return False
            
            print(f"  Access Token (first 32 chars): {access_token[:32]}...")
            if refresh_token:
                print(f"  Refresh Token (first 32 chars): {refresh_token[:32]}...")
            
        except httpx.HTTPStatusError as e:
            print(f"❌ Verification failed: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False
        
        print()
        
        # Step 4: Verify Token
        print("[4/4] Verifying access token...")
        try:
            token_verify_response = await client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/verify-token",
                json={
                    "token": access_token,
                    "provider": "isa_user"
                }
            )
            token_verify_response.raise_for_status()
            token_data = token_verify_response.json()
            
            if token_data.get('valid'):
                print(f"✓ Token verification successful!")
                print(f"  User ID: {token_data.get('user_id')}")
                print(f"  Email: {token_data.get('email')}")
                print(f"  Provider: {token_data.get('provider')}")
                if token_data.get('expires_at'):
                    print(f"  Expires At: {token_data.get('expires_at')}")
            else:
                print(f"❌ Token verification failed: {token_data.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Token verification error: {e}")
            return False
        
        print()
        print("=" * 60)
        print("✅ All tests passed! Registration flow is working correctly.")
        print("=" * 60)
        
        return True

async def test_error_cases(email: str):
    """Test error cases"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "=" * 60)
        print("Testing Error Cases")
        print("=" * 60)
        
        # Test 1: Invalid verification code
        print("\n[Error Test 1] Invalid verification code...")
        try:
            register_response = await client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/register",
                json={
                    "email": f"error_test_{datetime.now().timestamp()}@example.com",
                    "password": "Test123!",
                    "name": "ErrorTest"
                }
            )
            register_data = register_response.json()
            pending_id = register_data.get('pending_registration_id')
            
            # Try with wrong code
            verify_response = await client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/verify",
                json={
                    "pending_registration_id": pending_id,
                    "code": "000000"  # Wrong code
                }
            )
            
            verify_data = verify_response.json()
            if not verify_data.get('success') and verify_data.get('error'):
                print(f"✓ Correctly rejected invalid code: {verify_data.get('error')}")
            else:
                print(f"❌ Should have rejected invalid code")
                
        except Exception as e:
            print(f"⚠ Error test failed: {e}")
        
        # Test 2: Invalid pending_registration_id
        print("\n[Error Test 2] Invalid pending_registration_id...")
        try:
            verify_response = await client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/verify",
                json={
                    "pending_registration_id": "invalid_id_12345",
                    "code": "123456"
                }
            )
            
            verify_data = verify_response.json()
            if not verify_data.get('success') and verify_data.get('error'):
                print(f"✓ Correctly rejected invalid pending_id: {verify_data.get('error')}")
            else:
                print(f"❌ Should have rejected invalid pending_id")
                
        except Exception as e:
            print(f"⚠ Error test failed: {e}")

async def main():
    """Main test function"""
    if len(sys.argv) < 3:
        print("Usage: python test_registration_flow.py <email> <password> [name]")
        print("\nExample:")
        print("  python test_registration_flow.py test@example.com Test123! TestUser")
        print("\nOr with environment variables:")
        print("  VERIFICATION_CODE=123456 python test_registration_flow.py test@example.com Test123!")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Check if auth service is available
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_check = await client.get(f"{AUTH_BASE_URL}/health")
            if health_check.status_code != 200:
                print(f"⚠ Warning: Auth service health check returned {health_check.status_code}")
    except Exception as e:
        print(f"⚠ Warning: Cannot reach auth service at {AUTH_BASE_URL}: {e}")
        print("  Make sure auth_service is running before testing.")
    
    # Run main test
    success = await test_registration_flow(email, password, name)
    
    # Run error case tests (optional)
    if os.getenv("RUN_ERROR_TESTS", "false").lower() == "true":
        await test_error_cases(email)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())

