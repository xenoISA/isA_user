# Account Service Migration Guide

Migration from Supabase to PostgreSQL gRPC Client

## Changes Summary

### 1. Database Schema
- **New Schema:** `account` (separate from auth_service)
- **Table:** `account.users`
- **Fields:** Removed credits (moved to wallet_service), removed auth0_id
- **Kept:** user_id, email, name, subscription_status, preferences, is_active

### 2. Microservices Architecture
- ✅ Each service owns its own schema (account, auth, payment, etc.)
- ✅ Event-driven synchronization between services
- ✅ No direct database coupling
- ✅ Follows Domain-Driven Design principles

### 3. Code Changes

#### Models (models.py)
- ✅ Removed `credits_remaining` and `credits_total` fields
- ✅ Removed `auth0_id` field
- ✅ Added `user_id` to `AccountEnsureRequest`

#### Repository (account_repository.py)
- ✅ Migrated from `SupabaseClient` to `PostgresClient` (gRPC)
- ✅ Using schema: `account`
- ✅ Port: 50061 (isa-postgres-grpc)
- ✅ Added proto JSONB conversion for preferences
- ✅ Proper error handling for gRPC responses

#### Service (account_service.py)
- ✅ Updated validation to use `user_id` instead of `auth0_id`
- ✅ Removed credits-related logic
- ✅ Updated response models

## Migration Steps

### 1. Run Database Migration

```bash
cd microservices/account_service/migrations

# Connect to database
export PGPASSWORD=staging_postgres_2024
psql -h localhost -U postgres -d isa_platform -f 001_create_users_table.sql
```

### 2. Seed Test Data

```bash
# Make script executable
chmod +x manage_test_data.sh

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=isa_platform
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=staging_postgres_2024

# Seed test data
./manage_test_data.sh seed
```

### 3. Run Tests

```bash
cd ../../..  # Back to project root

# Run all account service tests
pytest microservices/account_service/tests/test_account_service.py -v -s
```

### 4. Deploy Service

```bash
cd deployment/staging

# Restart account_service to pick up changes
./isa-service restart account_service

# Check logs
./isa-service tail account_service
```

## Testing Checklist

- [ ] Migration script creates `account` schema
- [ ] Migration script creates `account.users` table
- [ ] Test data seeds successfully
- [ ] All 17 tests pass
- [ ] Service starts without errors
- [ ] Health check endpoint responds
- [ ] Can create new accounts
- [ ] Can update accounts
- [ ] Can query accounts

## Key Learnings from auth_service Migration

1. **Proto JSONB Conversion**: JSONB fields return proto objects, use `MessageToDict()`
2. **No Manual Timestamps**: Let database `DEFAULT NOW()` handle timestamps
3. **Check for None**: `insert_into()` returns `None` on failure
4. **Schema Consistency**: Use same schema name across migrations and code
5. **Port Numbers**: postgres-grpc is on port 50061 (not 50051)

## Service Dependencies

### Depends On:
- isa-postgres-grpc (port 50061)
- PostgreSQL database (isa_platform)

### Event Synchronization (Future):
- Listen to `UserCreated` events from auth_service
- Listen to `UserUpdated` events from auth_service
- Publish `AccountCreated` events
- Publish `AccountUpdated` events

## Database Connection

```python
from core.clients.postgres_client import PostgresClient

db = PostgresClient(
    host='isa-postgres-grpc',
    port=50061,
    user_id='account_service'
)
```

## Migration Status

✅ **COMPLETED**
- Schema migration created
- Repository migrated to gRPC
- Models updated
- Service logic updated
- Tests created (17 tests)
- Documentation completed

## Next Steps

1. Run migration and tests in staging
2. Set up event handlers for UserCreated/UserUpdated
3. Update API endpoints if needed
4. Update Postman collection
5. Deploy to staging environment

---

**Date:** 2025-01-24
**Version:** v0.1.0
**Status:** Ready for Testing
