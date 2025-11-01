  # ============== Database (PostgreSQL) ==============
  postgres:
    image: staging-isa-postgres:amd64
    container_name: staging-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=staging_postgres_2024
      - POSTGRES_DB=isa_platform
      - POSTGRES_PORT=5432
      - CONSUL_ENABLED=false
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
      - SERVICE_NAME=postgres-db
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - staging-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

## PostgreSQL Database Migration Guide

### Running Migrations

#### For account_service:
```bash
# Method 1: Using Docker exec
cd microservices/account_service/migrations
docker exec -i staging-postgres psql -U postgres -d isa_platform < 001_create_users_table.sql

# Method 2: Using manage_test_data.sh
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=isa_platform
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=staging_postgres_2024

# Seed test data
./manage_test_data.sh seed

# Clean up test data
./manage_test_data.sh cleanup
```

#### For other services:
Follow the same pattern. Each service has its own schema:
- `auth` schema → auth_service
- `account` schema → account_service
- `payment` schema → payment_service
- etc.

### Verifying Migrations

```bash
# Check if schema exists
docker exec -i staging-postgres psql -U postgres -d isa_platform -c "\dn"

# Check tables in schema
docker exec -i staging-postgres psql -U postgres -d isa_platform -c "\dt account.*"

# View data
docker exec -i staging-postgres psql -U postgres -d isa_platform -c "SELECT * FROM account.users LIMIT 5;"
```

### Testing Migrated Services

```bash
cd deployment/staging

# Restart service to pick up changes
./isa-service restart account_service

# Check service health
curl -s http://localhost:8202/health/detailed | python3 -m json.tool

# Run integration tests
cd ../../microservices/account_service/tests
./account_test.sh
```
