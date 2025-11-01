"""
Example: Integrating Compliance Service with Storage Service

Shows how storage_service can check uploaded files and descriptions.
"""

import asyncio
from microservices.compliance_service.client import ComplianceServiceClient


async def main():
    # Initialize client
    compliance = ComplianceServiceClient("http://localhost:8250")
    
    try:
        print("=" * 50)
        print("Storage Service Integration Example")
        print("=" * 50)
        print()
        
        # Example 1: Check file description
        print("1. Checking file description...")
        result = await compliance.check_text(
            user_id="user123",
            content="My vacation photos from 2024",
            check_types=["content_moderation", "pii_detection"]
        )
        
        print(f"   Status: {result.get('status')}")
        print(f"   Passed: {result.get('passed')}")
        
        if result.get("passed"):
            print("   ✓ File description OK")
        else:
            print("   ✗ File description blocked")
        
        print()
        
        # Example 2: Check file content
        print("2. Checking image file...")
        result2 = await compliance.check_file(
            user_id="user123",
            file_id="file_abc123",
            content_type="image"
        )
        
        print(f"   Status: {result2.get('status')}")
        print(f"   Passed: {result2.get('passed')}")
        print(f"   Check ID: {result2.get('check_id')}")
        
        if result2.get("passed"):
            print("   ✓ File content OK - upload can proceed")
        else:
            print("   ✗ File content blocked - delete temp file")
        
        print()
        
        # Example 3: Check PCI compliance (no card data)
        print("3. Checking for card data in file description...")
        result3 = await compliance.check_pci_card_data(
            content="Invoice for services rendered",
            user_id="user123"
        )
        
        print(f"   PCI Compliant: {result3.get('pci_compliant')}")
        
        if result3.get("pci_compliant"):
            print("   ✓ No card data detected")
        else:
            print("   ✗ Card data detected - block upload!")
            print(f"   Detected: {result3.get('detected_cards')}")
        
    finally:
        await compliance.close()


if __name__ == "__main__":
    asyncio.run(main())

