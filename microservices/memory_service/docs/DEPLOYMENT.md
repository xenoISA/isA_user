# Memory Service Deployment Guide

## ✅ Deployment Checklist

### 1. Database Migrations
- [x] Created 9 migration files (000-009)
- [x] Executed all migrations successfully
- [x] Verified schema `memory` created
- [x] Verified 9 tables created
- [x] Verified 3 functions created

### 2. Service Configuration
- [x] Port assigned: **8223**
- [x] Updated main.py with correct port
- [x] Updated README.md
- [x] Updated client.py default URLs
- [x] Updated all test scripts (6 files)

### 3. Supervisor Configuration
- [x] Added to `supervisord.staging.conf`
- [x] Added to `support_services` group
- [x] Configured with proper logging paths

## Database Schema

Successfully created in `isa_platform` database:

```
memory schema tables:
├── factual_memories       (9 indexes, 1 trigger)
├── episodic_memories      (8 indexes, 1 trigger)
├── procedural_memories    (7 indexes, 1 trigger)
├── semantic_memories      (7 indexes, 1 trigger)
├── working_memories       (6 indexes, 1 trigger)
├── session_memories       (6 indexes, 1 trigger)
├── session_summaries      (4 indexes)
├── memory_metadata        (7 indexes)
└── memory_associations    (4 indexes)

Functions:
├── track_memory_access()
├── update_memory_metadata()
└── update_updated_at()
```

## Service Details

- **Service Name**: memory_service
- **Port**: 8223
- **Group**: support_services
- **Base URL**: http://localhost:8223
- **Health Endpoint**: http://localhost:8223/health

## Starting the Service

### Using supervisor (in Docker)
```bash
cd deployment/staging
./isa-service start memory_service

# Check status
./isa-service status memory_service

# View logs
./isa-service logs memory_service
```

### Local development
```bash
cd microservices/memory_service
python main.py
```

## Testing

### Run all tests
```bash
cd microservices/memory_service/tests
./run_all_tests.sh
```

### Run individual test suites
```bash
./test_factual_memory.sh
./test_episodic_memory.sh
./test_procedural_memory.sh
./test_semantic_memory.sh
./test_working_memory.sh
./test_session_memory.sh
```

## Verification

### 1. Check database
```bash
docker exec -i staging-postgres psql -U postgres -d isa_platform -c "\dt memory.*"
```

### 2. Check service health
```bash
curl http://localhost:8223/health | python3 -m json.tool
```

### 3. Test AI extraction
```bash
curl -X POST http://localhost:8223/memories/factual/extract \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "dialog_content": "My name is John and I live in Tokyo",
    "importance_score": 0.8
  }'
```

## Architecture

- **PostgreSQL**: Structured data (no embeddings)
- **Qdrant**: Vector embeddings (to be integrated)
- **ISA Model**: AI extraction + embeddings (http://localhost:8082)
- **Port**: 8223
- **API Style**: REST (FastAPI)

## Next Steps

1. Start memory_service in staging environment
2. Run integration tests
3. Integrate Qdrant for vector storage
4. Add to API gateway routing
5. Create Postman collection
6. Monitor service logs and performance

## Files Created/Modified

### New Files
- All Python service files (repositories, services, models)
- 9 SQL migration files
- 6 bash test scripts + run_all_tests.sh
- client.py (HTTP client)
- __init__.py (package)
- main.py (FastAPI service)
- README.md (documentation)

### Modified Files
- `deployment/staging/config/supervisord.staging.conf` (added memory_service)

## Port Assignment

Previously `8210` was chosen but **conflicted with order_service**.
New assignment: **8223** (after media_service 8222)

Current port map:
- 8201: auth_service
- 8202: account_service  
- 8203: session_service
- 8204: authorization_service
- 8205: audit_service
- 8206: notification_service
- 8207: payment_service
- 8208: wallet_service
- 8209: storage_service
- 8210: order_service ⚠️ (conflict avoided)
- 8211: task_service
- 8212: organization_service
- 8213: invitation_service
- 8214: vault_service
- 8215: product_service
- 8216: billing_service
- 8217: calendar_service
- 8218: weather_service
- 8219: album_service
- 8220: device_service
- 8221: ota_service
- 8222: media_service
- **8223: memory_service** ✅ (newly assigned)
- 8225: telemetry_service
- 8230: event_service
