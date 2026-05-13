from pathlib import Path


MIGRATION = Path(
    "microservices/product_service/migrations/"
    "025_add_memory_vector_and_pool_products.sql"
)


def test_migration_025_adds_remaining_platform_meter_taxonomy():
    migration_sql = MIGRATION.read_text()

    for product_id in [
        "browser_pool_session",
        "memory_vector_storage",
        "memory_vector_query",
        "memory_graph_query",
        "knowledge_base_lookup",
    ]:
        assert product_id in migration_sql

    for service_type in [
        '"service_type":"browser_pool"',
        '"service_type":"vector_storage"',
        '"service_type":"data_service"',
    ]:
        assert service_type in migration_sql

    for operation_type in [
        "session_seconds",
        "vector_storage_bytes",
        "vector_query",
        "graph_query",
        "knowledge_base_lookup",
    ]:
        assert operation_type in migration_sql

    assert '"product_namespace":"kb:*"' in migration_sql


def test_migration_025_adds_pricing_and_cost_definitions():
    migration_sql = MIGRATION.read_text()

    for pricing_id in [
        "pricing_browser_pool_session_default",
        "pricing_memory_vector_storage_default",
        "pricing_memory_vector_query_default",
        "pricing_memory_graph_query_default",
        "pricing_knowledge_base_lookup_default",
    ]:
        assert pricing_id in migration_sql

    for cost_id in [
        "cost_browser_pool_session_seconds",
        "cost_memory_vector_storage_bytes",
        "cost_memory_vector_query",
        "cost_memory_graph_query",
        "cost_knowledge_base_lookup",
    ]:
        assert cost_id in migration_sql

    assert "ON CONFLICT (product_id) DO UPDATE" in migration_sql
    assert "ON CONFLICT (pricing_id) DO UPDATE" in migration_sql
    assert "ON CONFLICT (cost_id) DO UPDATE" in migration_sql
