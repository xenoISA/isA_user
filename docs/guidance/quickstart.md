# Quick Start

Get started with isA User platform.

## Prerequisites

- Python 3.11+
- Docker & Kubernetes (for production)
- PostgreSQL, Redis (minimum infrastructure)

## Installation

```bash
cd isA_user
pip install -r deployment/requirements/base.txt
```

## Start a Service

### Single Service (Development)

```bash
# Start auth service
cd microservices/auth_service
uvicorn main:app --reload --port 8201

# Or use the start script
./scripts/start_user_service.sh auth_service
```

### Multiple Services

```bash
# Start core services
for service in auth account session authorization; do
    cd microservices/${service}_service
    uvicorn main:app --port 820${i} &
    cd ../..
done
```

## Basic Usage

### 1. Create User Account

```python
import httpx

async def create_account():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8202/api/v1/accounts",
            json={
                "email": "user@example.com",
                "name": "John Doe",
                "password": "secure_password"
            }
        )
        return response.json()
```

### 2. Authenticate

```python
async def login():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8201/api/v1/auth/login",
            json={
                "email": "user@example.com",
                "password": "secure_password"
            }
        )
        return response.json()  # Returns JWT token
```

### 3. Make Authenticated Request

```python
async def get_profile(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8202/api/v1/accounts/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

## cURL Examples

### Register

```bash
curl -X POST "http://localhost:8202/api/v1/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "secure_password"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8201/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

### Get Profile

```bash
curl "http://localhost:8202/api/v1/accounts/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Upload File

```bash
curl -X POST "http://localhost:8209/api/v1/storage/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/file.jpg"
```

### Create Payment

```bash
curl -X POST "http://localhost:8207/api/v1/payments/intent" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "currency": "usd",
    "description": "Product purchase"
  }'
```

## Service Discovery

Services register with Consul automatically:

```bash
# List registered services
curl "http://localhost:8500/v1/catalog/services"

# Get service instances
curl "http://localhost:8500/v1/catalog/service/auth_service"
```

## Health Checks

Each service exposes health endpoints:

```bash
# Check service health
curl "http://localhost:8201/health"

# Response
{
  "status": "healthy",
  "service": "auth_service",
  "version": "1.0.0",
  "dependencies": {
    "postgres": "healthy",
    "redis": "healthy"
  }
}
```

## Configuration

### Environment Variables

```bash
# Core
ENVIRONMENT=development
DEBUG=true

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=isa_user
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Service Discovery
CONSUL_HOST=localhost
CONSUL_PORT=8500

# Auth
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRY=3600
```

### Service-Specific Config

Each service has its own configuration in `config/`:

```yaml
# config/ports.yaml
services:
  auth_service: 8201
  account_service: 8202
  session_service: 8203
  # ... etc
```

## Kubernetes Deployment

### Port Forward for Testing

```bash
# Forward auth service
kubectl port-forward -n isa-cloud-staging svc/auth-service 8201:8201

# Use the script for multiple services
./scripts/port-forward-test.sh
```

### Deploy to Staging

```bash
# Apply manifests
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/user-configmap.yaml
kubectl apply -f deployment/k8s/manifests/
```

## API Documentation

Each service provides Swagger documentation:

```
http://localhost:8201/docs  # Auth service
http://localhost:8202/docs  # Account service
http://localhost:8207/docs  # Payment service
# ... etc
```

## Testing

### Run Unit Tests

```bash
cd microservices/auth_service
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
# Requires K8s port-forwarding
pytest tests/integration/ -v
```

### Run Smoke Tests

```bash
./tests/smoke/auth_service/test_auth.sh
```

## Next Steps

- [Authentication](./authentication) - Auth details
- [Payments](./payments) - Payment processing
- [Storage](./storage) - File management
- [Architecture](./architecture) - System design
