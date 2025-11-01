# Compliance Service Client Integration Guide

## Overview

This guide shows how to integrate with `compliance_service` from other microservices using the **client pattern**.

---

## Installation & Setup

### 1. Import the Client

**File:** Your service's `main.py` or module

```python
from microservices.compliance_service.client import (
    ComplianceServiceClient,
    get_compliance_client
)
```

### 2. Initialize the Client

```python
# Method 1: Direct initialization
compliance_client = ComplianceServiceClient("http://localhost:8250")

# Method 2: Singleton pattern (recommended)
compliance_client = await get_compliance_client("http://localhost:8250")

# Method 3: With service discovery
from core.service_discovery import ServiceDiscovery

service_discovery = ServiceDiscovery(consul_registry)
compliance_url = service_discovery.get_service_url("compliance_service")
compliance_client = ComplianceServiceClient(compliance_url)
```

### 3. Close the Client (in shutdown)

```python
await compliance_client.close()
```

---

## Integration Examples

### Example 1: Account Service Integration

**File:** `microservices/account_service/main.py`

```python
from fastapi import FastAPI, HTTPException
from microservices.compliance_service.client import get_compliance_client

app = FastAPI()

# Initialize client on startup
@app.on_event("startup")
async def startup():
    global compliance_client
    compliance_client = await get_compliance_client()

@app.on_event("shutdown")
async def shutdown():
    await compliance_client.close()

# Use in endpoints
@app.put("/api/accounts/{user_id}")
async def update_account_profile(
    user_id: str,
    name: str,
    bio: Optional[str] = None
):
    """Update user profile with compliance check"""
    
    # Check profile content before saving
    result = await compliance_client.check_text(
        user_id=user_id,
        content=f"{name} {bio or ''}",
        check_types=["content_moderation", "pii_detection"]
    )
    
    if not result.get("passed"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "profile_content_blocked",
                "message": result.get("message"),
                "violations": result.get("violations"),
                "check_id": result.get("check_id")
            }
        )
    
    # Content passed - update profile
    await account_repository.update_profile(user_id, name, bio)
    
    return {
        "status": "success",
        "user_id": user_id,
        "compliance_check_id": result.get("check_id")
    }
```

---

### Example 2: Storage Service Integration

**File:** `microservices/storage_service/main.py`

```python
from fastapi import FastAPI, UploadFile, File
from microservices.compliance_service.client import ComplianceServiceClient

app = FastAPI()
compliance_client = ComplianceServiceClient("http://localhost:8250")

@app.post("/api/storage/upload")
async def upload_file(
    user_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = None
):
    """Upload file with compliance check"""
    
    # 1. Save file temporarily
    temp_file_id = await storage_repo.save_temp(file)
    
    try:
        # 2. Check file description if provided
        if description:
            desc_result = await compliance_client.check_text(
                user_id=user_id,
                content=description,
                check_types=["content_moderation", "pii_detection"]
            )
            
            if not desc_result.get("passed"):
                await storage_repo.delete_temp(temp_file_id)
                raise HTTPException(
                    status_code=403,
                    detail="File description contains inappropriate content"
                )
        
        # 3. Check file content
        content_type = "image" if file.content_type.startswith("image/") else "file"
        
        file_result = await compliance_client.check_file(
            user_id=user_id,
            file_id=temp_file_id,
            content_type=content_type
        )
        
        if not file_result.get("passed"):
            await storage_repo.delete_temp(temp_file_id)
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "file_content_blocked",
                    "message": file_result.get("message"),
                    "check_id": file_result.get("check_id")
                }
            )
        
        # 4. Move to permanent storage
        final_file_id = await storage_repo.finalize_upload(temp_file_id)
        
        return {
            "status": "success",
            "file_id": final_file_id,
            "compliance_check_id": file_result.get("check_id")
        }
    
    except Exception as e:
        await storage_repo.delete_temp(temp_file_id)
        raise
```

---

### Example 3: AI Agent Service Integration

**File:** `isa_agent/main.py` (your AI agent project)

```python
from fastapi import FastAPI, HTTPException
from microservices.compliance_service.client import ComplianceServiceClient

app = FastAPI()
compliance_client = ComplianceServiceClient("http://localhost:8250")

@app.post("/api/agent/chat")
async def agent_chat(
    user_id: str,
    prompt: str,
    context: Optional[dict] = None
):
    """AI agent chat with prompt injection protection"""
    
    # 1. Check user prompt for injection attempts
    prompt_check = await compliance_client.check_prompt(
        user_id=user_id,
        prompt=prompt,
        metadata={"has_context": bool(context)}
    )
    
    if not prompt_check.get("passed"):
        # Check if it's a prompt injection
        injection_result = prompt_check.get("injection_result", {})
        if injection_result.get("is_injection_detected"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "prompt_injection_detected",
                    "message": "Your prompt contains potentially harmful instructions",
                    "detected_patterns": injection_result.get("detected_patterns"),
                    "suggestion": "Please rephrase your question without system instructions"
                }
            )
        else:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "content_blocked",
                    "message": prompt_check.get("message")
                }
            )
    
    # 2. Call AI model (safe to proceed)
    ai_response = await call_ai_model(prompt, context)
    
    # 3. (Optional) Check AI output for harmful content
    output_check = await compliance_client.check_text(
        user_id="system",  # System check
        content=ai_response,
        check_types=["content_moderation"],
        metadata={"type": "ai_output", "original_user": user_id}
    )
    
    if not output_check.get("passed"):
        # AI generated harmful content - return safe response
        return {
            "response": "I apologize, but I cannot provide that information.",
            "compliance_note": "Response blocked by content moderation",
            "check_id": output_check.get("check_id")
        }
    
    return {
        "response": ai_response,
        "compliance_check_id": prompt_check.get("check_id")
    }
```

---

### Example 4: Chat/Messaging Service

**File:** `microservices/messaging_service/main.py`

```python
from fastapi import FastAPI
from microservices.compliance_service.client import ComplianceServiceClient

app = FastAPI()
compliance = ComplianceServiceClient()

@app.post("/api/messages/send")
async def send_message(
    user_id: str,
    room_id: str,
    message: str
):
    """Send message with content moderation"""
    
    # Check message content
    result = await compliance.check_text(
        user_id=user_id,
        content=message,
        check_types=["content_moderation", "pii_detection"],
        metadata={"room_id": room_id}
    )
    
    if not result.get("passed"):
        # Log violation
        logger.warning(f"Message blocked for user {user_id}: {result.get('violations')}")
        
        # Return user-friendly error
        return {
            "status": "blocked",
            "message": "Your message violates our community guidelines",
            "suggestions": [
                "Remove offensive language",
                "Avoid sharing personal information"
            ],
            "check_id": result.get("check_id")
        }
    
    # Save and broadcast message
    msg_id = await save_message(user_id, room_id, message)
    await broadcast_message(room_id, msg_id, message)
    
    return {
        "status": "sent",
        "message_id": msg_id,
        "compliance_check_id": result.get("check_id")
    }
```

---

## Client API Reference

### Core Methods

#### `check_text()`

```python
result = await client.check_text(
    user_id="user123",
    content="Text to check",
    check_types=["content_moderation", "pii_detection", "prompt_injection"],
    organization_id="org456",  # Optional
    session_id="session789",   # Optional
    metadata={"key": "value"}  # Optional
)

# Returns:
{
    "check_id": "550e8400-...",
    "status": "pass",  # or "fail", "warning", "flagged"
    "risk_level": "none",  # or "low", "medium", "high", "critical"
    "passed": true,
    "violations": [],
    "warnings": [],
    "message": "Content passed all compliance checks",
    "checked_at": "2025-10-22T10:00:00Z",
    "processing_time_ms": 145.3
}
```

#### `check_prompt()`

```python
result = await client.check_prompt(
    user_id="user123",
    prompt="AI prompt text",
    organization_id="org456",
    metadata={"context": "chat"}
)

# Specifically checks for prompt injection attempts
```

#### `check_file()`

```python
result = await client.check_file(
    user_id="user123",
    file_id="file_abc123",
    content_type="image",  # or "audio", "video", "file"
    organization_id="org456"
)
```

#### `check_pii()`

```python
result = await client.check_pii(
    user_id="user123",
    content="Text containing potential PII",
    organization_id="org456"
)

# Returns detailed PII detection results
```

### GDPR Methods

#### `export_user_data()`

```python
data = await client.export_user_data(
    user_id="user123",
    format="json"  # or "csv"
)

# Returns all compliance data for the user
```

#### `delete_user_data()`

```python
result = await client.delete_user_data(
    user_id="user123",
    confirmation="CONFIRM_DELETE"
)

# Returns:
{
    "status": "success",
    "deleted_records": 150,
    "compliance": "GDPR Article 17 - Right to Erasure"
}
```

#### `get_user_data_summary()`

```python
summary = await client.get_user_data_summary(user_id="user123")

# Returns:
{
    "user_id": "user123",
    "total_records": 150,
    "can_export": true,
    "can_delete": true,
    "export_url": "/api/compliance/user/user123/data-export"
}
```

### Utility Methods

#### `get_check_status()`

```python
check = await client.get_check_status(check_id="550e8400-...")
```

#### `get_user_checks()`

```python
checks = await client.get_user_checks(
    user_id="user123",
    limit=100,
    status="fail"  # Optional filter
)
```

#### `check_pci_card_data()`

```python
result = await client.check_pci_card_data(
    content="Text that might contain card numbers",
    user_id="user123"
)

# Returns PCI-DSS compliance check result
```

#### `health_check()`

```python
health = await client.health_check()

# Returns:
{
    "status": "healthy",
    "service": "compliance_service",
    "version": "1.0.0"
}
```

---

## Error Handling

### Handle Check Failures

```python
try:
    result = await compliance_client.check_text(
        user_id=user_id,
        content=content
    )
    
    if not result.get("passed"):
        # Handle compliance failure
        if result.get("risk_level") == "critical":
            # Block immediately
            raise HTTPException(403, "Content blocked")
        elif result.get("risk_level") == "high":
            # Block and log
            await log_violation(user_id, result)
            raise HTTPException(403, "Content blocked")
        elif result.get("risk_level") == "medium":
            # Flag for review
            await flag_for_review(result.get("check_id"))
            # Allow but warn
            warnings.append("Content flagged for review")
    
except httpx.HTTPError as e:
    logger.error(f"Compliance service unavailable: {e}")
    # Decide: allow or block when service is down?
    # Option 1: Fail closed (block)
    raise HTTPException(503, "Compliance check unavailable")
    # Option 2: Fail open (allow but log)
    # logger.warning("Allowing content due to service unavailability")
```

---

## Best Practices

### 1. Use Singleton Pattern

```python
# In your service's main.py
@app.on_event("startup")
async def startup():
    global compliance_client
    compliance_client = await get_compliance_client()

@app.on_event("shutdown")
async def shutdown():
    await compliance_client.close()
```

### 2. Handle Service Unavailability

```python
async def check_with_fallback(content: str, user_id: str):
    """Check compliance with fallback"""
    try:
        result = await compliance_client.check_text(user_id, content)
        return result
    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        # Decide your fallback strategy
        return {"passed": True, "fallback": True}  # Fail open
        # or
        return {"passed": False, "fallback": True}  # Fail closed
```

### 3. Cache Results (for identical content)

```python
from cachetools import TTLCache

compliance_cache = TTLCache(maxsize=1000, ttl=3600)

async def check_with_cache(content: str, user_id: str):
    """Check with caching"""
    import hashlib
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    
    # Check cache
    if content_hash in compliance_cache:
        return compliance_cache[content_hash]
    
    # Perform check
    result = await compliance_client.check_text(user_id, content)
    
    # Cache if passed
    if result.get("passed"):
        compliance_cache[content_hash] = result
    
    return result
```

### 4. Async Background Checks

```python
import asyncio

async def check_in_background(content: str, user_id: str):
    """Non-blocking compliance check"""
    asyncio.create_task(
        compliance_client.check_text(user_id, content)
    )
    # Return immediately, check happens in background
```

---

## Service Discovery Integration

```python
from core.service_discovery import ServiceDiscovery
from microservices.compliance_service.client import ComplianceServiceClient

# In your service startup
async def startup():
    # Get compliance service URL from Consul
    service_discovery = ServiceDiscovery(consul_registry)
    compliance_url = service_discovery.get_service_url("compliance_service")
    
    # Initialize client with discovered URL
    global compliance_client
    compliance_client = ComplianceServiceClient(compliance_url)
```

---

## Testing

### Mock the Client in Tests

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_upload_with_compliance():
    # Mock compliance client
    with patch('your_service.compliance_client') as mock_client:
        mock_client.check_file = AsyncMock(return_value={
            "passed": True,
            "check_id": "test_check",
            "status": "pass"
        })
        
        # Test your endpoint
        response = await upload_file(user_id="test", file=test_file)
        
        assert response["status"] == "success"
        mock_client.check_file.assert_called_once()
```

---

## Troubleshooting

### Issue: "Connection refused"

**Solution:** Ensure compliance_service is running:
```bash
curl http://localhost:8250/health
```

### Issue: "Timeout errors"

**Solution:** Increase client timeout:
```python
client = ComplianceServiceClient("http://localhost:8250")
client.client.timeout = httpx.Timeout(30.0)  # 30 seconds
```

### Issue: "Service not found in Consul"

**Solution:** Check service registration:
```bash
consul catalog services
consul catalog nodes -service=compliance_service
```

---

## See Also

- [README.md](README.md) - Service overview
- [COMPLIANCE_STANDARDS.md](COMPLIANCE_STANDARDS.md) - Regulatory compliance
- [examples/integration_example.py](examples/integration_example.py) - More examples

---

**Last Updated:** 2025-10-22  
**Version:** 1.0.0

