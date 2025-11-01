# Compliance Service Integration Examples

This directory contains examples of how to integrate `compliance_service` with other microservices.

## Examples

### 1. Account Service Integration
**File:** `account_service_example.py`

Shows how to:
- Check user profile content
- Detect PII in user data
- Get user data summary (GDPR)

**Run:**
```bash
python -m microservices.compliance_service.examples.account_service_example
```

### 2. Storage Service Integration
**File:** `storage_service_example.py`

Shows how to:
- Check file descriptions
- Check uploaded file content
- Detect credit card data (PCI-DSS)

**Run:**
```bash
python -m microservices.compliance_service.examples.storage_service_example
```

### 3. AI Agent Integration
**File:** `ai_agent_example.py`

Shows how to:
- Check prompts for injection attempts
- Detect jailbreak patterns
- Validate AI model outputs

**Run:**
```bash
python -m microservices.compliance_service.examples.ai_agent_example
```

### 4. GDPR Compliance Features
**File:** `gdpr_example.py`

Shows how to:
- Export user data (Article 20)
- Delete user data (Article 17)
- Get data summary (Article 15)
- Manage consent

**Run:**
```bash
python -m microservices.compliance_service.examples.gdpr_example
```

## Quick Start

1. **Start compliance service:**
   ```bash
   python -m microservices.compliance_service.main
   ```

2. **Run an example:**
   ```bash
   python -m microservices.compliance_service.examples.account_service_example
   ```

## Integration Pattern

All examples follow this pattern:

```python
from microservices.compliance_service.client import ComplianceServiceClient

# Initialize
compliance = ComplianceServiceClient("http://localhost:8250")

# Check content
result = await compliance.check_text(
    user_id="user123",
    content="Content to check",
    check_types=["content_moderation"]
)

# Handle result
if result.get("passed"):
    # Content is safe
    await save_content()
else:
    # Content blocked
    raise HTTPException(403, result.get("message"))

# Cleanup
await compliance.close()
```

## See Also

- [Client API Documentation](../client.py)
- [Test Scripts](../tests/)
- [Service Documentation](../docs/)

