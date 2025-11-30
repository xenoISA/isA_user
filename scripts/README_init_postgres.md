# PostgreSQL Database Initialization Script

## Overview

`init_postgres.sh` is a comprehensive database initialization script for the ISA Platform that manages schema creation, migrations, and test data across 27 microservices.

## Features

- ✅ **Automated Schema Creation** - Creates 27 service schemas with 100+ tables
- ✅ **Dependency Management** - Executes migrations in 8 phases respecting service dependencies
- ✅ **Smart File Handling** - Automatically skips deprecated files (*.deprecated, *.old, *.backup)
- ✅ **Optional Test Data** - Control test data loading via command-line flag
- ✅ **Cleanup Mode** - Remove all test data in reverse dependency order
- ✅ **Verification** - Built-in schema verification and statistics
- ✅ **Colorful Output** - Easy-to-read progress with color-coded messages

## Test Results (Verified 2025-11-22)

### Database Statistics
- **Schemas Created**: 27/27 (100%)
- **Total Tables**: 100
- **Functions**: 10
- **Errors**: 0
- **Execution Time**: ~2 minutes

### Schema Distribution
```
memory_service       → 9 tables
telemetry_service    → 8 tables
event_service        → 6 tables
ota_service          → 6 tables
payment_service      → 6 tables
notification_service → 5 tables
media_service        → 5 tables
organization_service → 5 tables
auth_service         → 5 tables
billing_service      → 4 tables
device_service       → 4 tables
storage_service      → 4 tables
[... 15 other services with 1-3 tables each]
```

## Usage

### 1. Initialize Schema Only (Production)
```bash
./scripts/init_postgres.sh
```

### 2. Initialize Schema + Test Data (Development)
```bash
./scripts/init_postgres.sh --with-seed-data
```

### 3. Cleanup All Test Data
```bash
./scripts/init_postgres.sh --cleanup
```

### 4. Custom Database Configuration
```bash
# Environment variables
DB_HOST=localhost \
DB_PORT=5432 \
DB_NAME=isa_platform \
DB_USER=postgres \
DB_PASSWORD=secret \
./scripts/init_postgres.sh
```

### 5. Kubernetes Environment
```bash
# Step 1: Port forward postgres pod
kubectl port-forward -n isa-cloud-staging postgres-0 5432:5432 &

# Step 2: Run initialization
DB_HOST=localhost DB_USER=postgres ./scripts/init_postgres.sh

# Step 3: With test data
DB_HOST=localhost DB_USER=postgres ./scripts/init_postgres.sh --with-seed-data
```

## Migration Execution Phases

The script executes migrations in **8 phases** based on service dependencies:

### Phase 1: Core Identity & Authentication
- `auth_service` - User authentication (5 tables)
- `account_service` - User profiles (1 table)
- `authorization_service` - Permissions (1 table)
- `organization_service` - Organizations & family sharing (5 tables)

### Phase 2: Foundation Services
- `device_service` - Device management (4 tables)
- `session_service` - User sessions (2 tables)
- `event_service` - Event sourcing (6 tables)

### Phase 3: Business Logic
- `product_service` - Product catalog (2 tables)
- `wallet_service` - Digital wallets (2 tables)
- `payment_service` - Payment processing (6 tables)
- `billing_service` - Usage billing (4 tables)
- `order_service` - Order management (1 table)

### Phase 4: Storage & Media
⚠️ **Critical Order**: storage → media → album
- `storage_service` - File storage (4 tables) **[Must run first]**
- `media_service` - Photo metadata (5 tables) **[Depends on storage]**
- `album_service` - Photo albums (3 tables) **[Depends on storage]**

### Phase 5: AI & Intelligence
- `memory_service` - AI memory system (9 tables)

### Phase 6: Integration & Support
- `notification_service` - Notifications (5 tables)
- `calendar_service` - Calendar sync (2 tables)
- `location_service` - Location data (2 tables)
- `weather_service` - Weather API (3 tables)
- `invitation_service` - Org invitations (1 table)

### Phase 7: Infrastructure & Operations
- `task_service` - Task automation (3 tables)
- `ota_service` - Firmware updates (6 tables)
- `telemetry_service` - Metrics & monitoring (8 tables)
- `audit_service` - Audit logs (1 table)
- `compliance_service` - Compliance tracking (2 tables)
- `vault_service` - Secrets management (3 tables)

### Phase 8: Optional Services
- `document_service` (if exists)

## Configuration Options

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | PostgreSQL host |
| `DB_PORT` | 5432 | PostgreSQL port |
| `DB_NAME` | isa_platform | Database name |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | (empty) | Database password |

### Command-Line Flags
| Flag | Description |
|------|-------------|
| `--with-seed-data` | Load test data after schema initialization |
| `--cleanup` | Remove all test data (reverse order) |
| `-h, --help` | Show help message |

## Output Example

```
╔════════════════════════════════════════════════════════════════╗
║     ISA Platform - PostgreSQL Database Initialization         ║
╚════════════════════════════════════════════════════════════════╝

Configuration:
  Database Host: localhost
  Database Port: 5432
  Database Name: isa_platform_test
  Database User: postgres
  Project Root: /Users/xenodennis/Documents/Fun/isA_user
  Load Seed Data: false
  Cleanup Mode: false

=== Checking Database Connection ===
✓ Connected to PostgreSQL server
✓ Database 'isa_platform_test' exists

=== Creating Base Schema and Functions ===
  → Creating public.update_updated_at_column() function
    ✓ Success
  → Creating 'authenticated' role
    ✓ Success
✓ Base schema and functions created

=== Running Microservice Migrations ===

━━━ Phase 1: Core Identity & Authentication Services ━━━

→ Running migrations for: auth_service
  → Executing: 001_create_users_table.sql
    ✓ 001_create_users_table.sql
  → Executing: 002_create_organizations_table.sql
    ✓ 002_create_organizations_table.sql
  ...
  ✓ Completed 4 migrations for auth_service

[... phases 2-8 ...]

=== Verifying Database Schemas ===
  ✓ Schema: account
  ✓ Schema: album
  ✓ Schema: audit
  ...
  ✓ Schema: wallet
  ✓ Schema: weather

  Summary: 27 schemas found, 0 missing

=== Database Statistics ===
  Database: isa_platform_test
  Schemas: 28
  Tables: 100
  Functions: 10

╔════════════════════════════════════════════════════════════════╗
║          Database Initialization Completed Successfully        ║
╚════════════════════════════════════════════════════════════════╝
```

## Test Data Management

### Test Data Pattern Standard
All test data follows this ID pattern:
- Users: `test_user_001`, `test_user_002`, ...
- Organizations: `test_org_001`, `test_org_002`, ...
- Files: `test_file_001`, `test_file_002`, ...
- Devices: `test_device_001`, `test_device_002`, ...
- Email domain: `@example.com`

### Seed Data Dependencies
⚠️ **Important**: Test data must be loaded in order due to dependencies:

1. **account_service** / **auth_service** - Creates test users
2. **organization_service** - Creates test organizations
3. **device_service** - Creates test devices
4. **storage_service** - Creates test files **[Required by album/media]**
5. **album_service** - References storage test files
6. **media_service** - References storage test files
7. All other services - Reference users/orgs

### Cleanup Order
Cleanup runs in **reverse order** to respect FK relationships:
1. album_service, media_service
2. storage_service
3. notification, event, session, task, order, wallet, payment, product
4. device_service, authorization_service, organization_service
5. auth_service, account_service

## Troubleshooting

### Issue: "Cannot connect to PostgreSQL server"
**Solution**: Check if PostgreSQL is running and accessible
```bash
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT version();"
```

### Issue: "Database already exists"
**Solution**: The script will use the existing database. To start fresh:
```bash
# Drop and recreate
kubectl exec -n isa-cloud-staging postgres-0 -- psql -U postgres -c "DROP DATABASE isa_platform;"
./scripts/init_postgres.sh
```

### Issue: Port-forward disconnected
**Solution**: Restart port-forward
```bash
pkill -f "port-forward.*postgres"
kubectl port-forward -n isa-cloud-staging postgres-0 5432:5432 &
```

### Issue: Migration file errors
**Solution**: Check for deprecated files
```bash
# List all deprecated files
find microservices/*/migrations -name "*.deprecated"

# These are automatically skipped by the script
```

## Microservices Best Practices

This script follows microservices architecture best practices:

✅ **No Cross-Service Foreign Keys** - All services are loosely coupled
✅ **Application-Level Validation** - References validated via service APIs
✅ **Dedicated Schemas** - Each service owns its schema
✅ **Event-Driven Architecture** - Services communicate via events
✅ **Independent Deployment** - Each service can be updated independently

## Migration File Naming Convention

```
000_init_schema.sql              # Schema initialization (recommended)
001-099_create_*.sql             # Initial table creation
100-199_add_*.sql                # Adding new tables/columns
200-299_modify_*.sql             # Modifying structure
300-399_remove_*.sql             # Removing FKs, constraints
400-499_fix_*.sql                # Bug fixes, data type corrections
500-599_migrate_to_*.sql         # Schema migrations
900-998_seed_test_data.sql       # Test data insertion
999_cleanup_test_data.sql        # Test data cleanup
*.deprecated                     # Deprecated (auto-skipped)
*.old                            # Old files (auto-skipped)
*.backup                         # Backup files (auto-skipped)
```

## Files Fixed During Testing

The following issues were resolved:

1. ✅ **auth_service/004_create_pairing_tokens_table.sql** - Fixed INDEX syntax in CREATE TABLE
2. ✅ **storage_service/000_init_schema.sql** - Fixed CREATE ROLE IF NOT EXISTS syntax
3. ✅ **memory_service/005_create_working_memories_table.sql** - Fixed NOW() in index predicate
4. ✅ **vault_service/001_create_vault_tables.sql** - Removed cross-service foreign keys
5. ✅ **15 deprecated files** - Moved old dev schema migration files to .deprecated

## Success Criteria

After successful execution, you should see:
- ✅ 27/27 schemas created (0 missing)
- ✅ ~100 tables created across all services
- ✅ 10+ functions created
- ✅ 0 errors in output
- ✅ All services able to connect and operate independently

## Related Files

- `scripts/init_postgres.sh` - Main initialization script
- `scripts/init_minio.sh` - MinIO storage initialization
- `scripts/init_qdrant.sh` - Qdrant vector DB initialization
- `microservices/*/migrations/` - Individual service migrations
- `deployment/k8s/test_data_standard.md` - Test data naming standards

## Support

For issues or questions:
1. Check this README
2. Review test output logs
3. Verify migration files in `microservices/*/migrations/`
4. Check database state: `psql -d isa_platform -c "\dn"` (list schemas)

---

**Last Updated**: 2025-11-22
**Script Version**: 2.0.0
**Test Status**: ✅ Passing (100% success rate)
