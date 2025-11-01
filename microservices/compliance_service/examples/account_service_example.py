"""
Example: Integrating Compliance Service with Account Service

Shows how account_service can check user profile content before saving.
"""

import asyncio
from microservices.compliance_service.client import ComplianceServiceClient


async def main():
    # Initialize client
    compliance = ComplianceServiceClient("http://localhost:8250")
    
    try:
        print("=" * 50)
        print("Account Service Integration Example")
        print("=" * 50)
        print()
        
        # Example 1: Check user profile update
        print("1. Checking user profile content...")
        result = await compliance.check_text(
            user_id="user123",
            content="John Doe - Software Engineer at Tech Corp",
            check_types=["content_moderation", "pii_detection"]
        )
        
        print(f"   Status: {result.get('status')}")
        print(f"   Passed: {result.get('passed')}")
        print(f"   Risk Level: {result.get('risk_level')}")
        print(f"   Check ID: {result.get('check_id')}")
        
        if result.get("passed"):
            print("   ✓ Profile update allowed")
        else:
            print("   ✗ Profile update blocked")
            print(f"   Violations: {result.get('violations')}")
        
        print()
        
        # Example 2: Check profile with PII
        print("2. Checking profile with email...")
        result2 = await compliance.check_text(
            user_id="user456",
            content="Contact me at john@example.com",
            check_types=["pii_detection"]
        )
        
        print(f"   Status: {result2.get('status')}")
        print(f"   Passed: {result2.get('passed')}")
        
        if result2.get("pii_result"):
            pii = result2["pii_result"]
            print(f"   PII Detected: {len(pii.get('detected_pii', []))} items")
            for item in pii.get('detected_pii', []):
                print(f"     - {item.get('type')}: {item.get('value')}")
        
        print()
        
        # Example 3: Get user data summary (GDPR)
        print("3. Getting user data summary...")
        summary = await compliance.get_user_data_summary("user123")
        
        print(f"   Total Records: {summary.get('total_records', 0)}")
        print(f"   Can Export: {summary.get('can_export')}")
        print(f"   Can Delete: {summary.get('can_delete')}")
        
    finally:
        await compliance.close()


if __name__ == "__main__":
    asyncio.run(main())

