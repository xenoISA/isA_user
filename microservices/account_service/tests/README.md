# Account Service Tests

Comprehensive test suite for account_service with PostgreSQL gRPC client.

## Setup

1. **Run migrations:**
   ```bash
   cd microservices/account_service/migrations
   psql -h localhost -U isa_user -d isa_db -f 001_create_users_table.sql
   ```

2. **Seed test data:**
   ```bash
   ./manage_test_data.sh seed
   ```

## Running Tests

```bash
# Run all tests
pytest microservices/account_service/tests/test_account_service.py -v

# Run specific test
pytest microservices/account_service/tests/test_account_service.py::TestAccountRepository::test_01_ensure_account_create_new -v

# Run with output
pytest microservices/account_service/tests/test_account_service.py -v -s
```

## Test Coverage

### Account Repository Tests (17 tests)

1. ✅ `test_01_ensure_account_create_new` - Create new account
2. ✅ `test_02_ensure_account_already_exists` - Ensure existing account
3. ✅ `test_03_get_account_by_id` - Get account by ID
4. ✅ `test_04_get_account_by_email` - Get account by email
5. ✅ `test_05_get_nonexistent_account` - Handle nonexistent account
6. ✅ `test_06_update_account_profile` - Update profile
7. ✅ `test_07_update_account_preferences` - Update preferences
8. ✅ `test_08_merge_preferences` - Merge preferences
9. ✅ `test_09_deactivate_account` - Deactivate account
10. ✅ `test_10_activate_account` - Activate account
11. ✅ `test_11_list_accounts_no_filters` - List all accounts
12. ✅ `test_12_list_active_accounts` - List active accounts
13. ✅ `test_13_list_by_subscription_status` - Filter by subscription
14. ✅ `test_14_search_accounts_by_name` - Search by name
15. ✅ `test_15_search_accounts_by_email` - Search by email
16. ✅ `test_16_get_account_stats` - Get statistics
17. ✅ `test_17_delete_account_soft_delete` - Soft delete

## Cleanup

```bash
# Remove test data
cd microservices/account_service/migrations
./manage_test_data.sh cleanup
```

## Notes

- Tests use real database (not mocked)
- Tests assume PostgreSQL gRPC client is running on `isa-postgres-grpc:50061`
- Test data is created in `account` schema
- All tests use `account.users` table
