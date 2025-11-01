"""
Example: GDPR Compliance Features

Shows how to use GDPR data control features.
"""

import asyncio
from microservices.compliance_service.client import ComplianceServiceClient


async def main():
    # Initialize client
    compliance = ComplianceServiceClient("http://localhost:8250")
    
    try:
        print("=" * 50)
        print("GDPR Compliance Example")
        print("=" * 50)
        print()
        
        user_id = "gdpr_test_user"
        
        # Example 1: Get data summary (Article 15)
        print("1. Get User Data Summary (GDPR Article 15)...")
        summary = await compliance.get_user_data_summary(user_id)
        
        print(f"   User ID: {summary.get('user_id')}")
        print(f"   Total Records: {summary.get('total_records', 0)}")
        print(f"   Data Categories: {summary.get('data_categories', [])}")
        print(f"   Can Export: {summary.get('can_export')}")
        print(f"   Can Delete: {summary.get('can_delete')}")
        print()
        
        # Example 2: Export user data (Article 20)
        print("2. Export User Data (GDPR Article 20)...")
        export_data = await compliance.export_user_data(
            user_id=user_id,
            format="json"
        )
        
        print(f"   Export Type: {export_data.get('export_type')}")
        print(f"   Total Checks: {export_data.get('total_checks', 0)}")
        print(f"   Export Date: {export_data.get('export_date')}")
        print("   ✓ Data exported successfully")
        print()
        
        # Example 3: Delete user data (Article 17)
        print("3. Delete User Data (GDPR Article 17)...")
        print("   Warning: This is permanent!")
        
        # Uncomment to actually delete:
        # result = await compliance.delete_user_data(
        #     user_id=user_id,
        #     confirmation="CONFIRM_DELETE"
        # )
        # print(f"   Status: {result.get('status')}")
        # print(f"   Deleted Records: {result.get('deleted_records')}")
        
        print("   (Skipped - uncomment to test)")
        print()
        
        # Example 4: Check what data we collect
        print("4. Data Transparency...")
        print("   Compliance service collects:")
        print("   - Compliance check results")
        print("   - Content hashes (not actual content)")
        print("   - Timestamps")
        print("   - Risk assessments")
        print("   - Violations detected")
        print()
        print("   Retention: 7 years (GDPR compliant)")
        print("   Purpose: Safety, security, compliance")
        
    finally:
        await compliance.close()


if __name__ == "__main__":
    asyncio.run(main())

