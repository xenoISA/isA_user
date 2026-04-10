-- Product Service Migration: Add explicit pipeline and user-profile products
-- Version: 013
-- Date: 2026-04-09
-- Description: Seed invoiceable products for data pipeline operations and
--              the curated user-profile query used by isA_Data.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('data_pipeline_run', 'Data Pipeline Run', 'DATA-PIPELINE-RUN',
 'Managed pipeline execution run through isA_Data',
 'data_products', 'data_processing', 0.0200, 'USD', 'per_operation',
 '["pipeline", "data", "orchestration"]'::jsonb,
 '{"free_tier_operations": 25}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "data_pipeline",
    "operation_type": "pipeline_run",
    "unit": "operation",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "compute_tokens",
      "cost_components": [
        {
          "component_id": "pipeline_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "pipeline_intermediate_storage",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "scratch_storage",
          "unit_type": "gb"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('data_etl_job', 'Data ETL Job', 'DATA-ETL-JOB',
 'Managed ETL job execution through isA_Data',
 'data_products', 'data_processing', 0.0120, 'USD', 'per_operation',
 '["data", "etl", "transformation"]'::jsonb,
 '{"free_tier_operations": 50}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "data_pipeline",
    "operation_type": "etl_job",
    "unit": "operation",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "compute_tokens",
      "cost_components": [
        {
          "component_id": "pipeline_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "pipeline_intermediate_storage",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "scratch_storage",
          "unit_type": "gb"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('data_query_execution', 'Data Query Execution', 'DATA-QUERY-EXEC',
 'Managed data query execution through isA_Data pipelines',
 'data_products', 'data_processing', 0.0080, 'USD', 'per_operation',
 '["data", "query", "execution"]'::jsonb,
 '{"free_tier_operations": 100}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "data_pipeline",
    "operation_type": "query_execution",
    "unit": "operation",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "compute_tokens",
      "cost_components": [
        {
          "component_id": "pipeline_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "pipeline_intermediate_storage",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "scratch_storage",
          "unit_type": "gb"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('data_export', 'Data Export', 'DATA-EXPORT',
 'Managed export job through isA_Data',
 'data_products', 'data_processing', 0.0100, 'USD', 'per_operation',
 '["data", "export", "delivery"]'::jsonb,
 '{"free_tier_operations": 25}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "data_pipeline",
    "operation_type": "data_export",
    "unit": "operation",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "compute_tokens",
      "cost_components": [
        {
          "component_id": "pipeline_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "pipeline_intermediate_storage",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "scratch_storage",
          "unit_type": "gb"
        },
        {
          "component_id": "pipeline_export_network",
          "component_type": "network",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "egress_gb",
          "unit_type": "gb"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('curated.account.user_profiles', 'User Profile Query', 'DATA-USER-PROFILES',
 'Curated user profile query exposed by isA_Data',
 'data_products', 'data_processing', 0.0035, 'USD', 'per_request',
 '["data", "profile", "account"]'::jsonb,
 '{"free_tier_requests": 500}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "data_service",
    "operation_type": "user_profile_query",
    "unit": "request",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "data_product_requests",
      "cost_components": [
        {
          "component_id": "hybrid_data_storage",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "storage_gb_month",
          "unit_type": "gb_month"
        },
        {
          "component_id": "hybrid_data_vector_search",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "vector_queries",
          "unit_type": "request"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods')
ON CONFLICT (product_id) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    product_code = EXCLUDED.product_code,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    product_type = EXCLUDED.product_type,
    base_price = EXCLUDED.base_price,
    billing_interval = EXCLUDED.billing_interval,
    features = EXCLUDED.features,
    quota_limits = EXCLUDED.quota_limits,
    is_active = EXCLUDED.is_active,
    metadata = EXCLUDED.metadata,
    product_kind = EXCLUDED.product_kind,
    fulfillment_type = EXCLUDED.fulfillment_type,
    inventory_policy = EXCLUDED.inventory_policy,
    requires_shipping = EXCLUDED.requires_shipping,
    tax_category = EXCLUDED.tax_category,
    updated_at = NOW();

INSERT INTO product.product_pricing (
    pricing_id, product_id, tier_name,
    min_quantity, max_quantity,
    unit_price, currency, metadata
) VALUES
('pricing_data_pipeline_run_default', 'data_pipeline_run', 'default', 0, NULL, 0.0200, 'USD',
 '{"unit": "operation", "billing_type": "usage_based"}'::jsonb),
('pricing_data_etl_job_default', 'data_etl_job', 'default', 0, NULL, 0.0120, 'USD',
 '{"unit": "operation", "billing_type": "usage_based"}'::jsonb),
('pricing_data_query_execution_default', 'data_query_execution', 'default', 0, NULL, 0.0080, 'USD',
 '{"unit": "operation", "billing_type": "usage_based"}'::jsonb),
('pricing_data_export_default', 'data_export', 'default', 0, NULL, 0.0100, 'USD',
 '{"unit": "operation", "billing_type": "usage_based"}'::jsonb),
('pricing_curated_user_profiles_default', 'curated.account.user_profiles', 'default', 0, NULL, 0.0035, 'USD',
 '{"unit": "request", "billing_type": "usage_based"}'::jsonb)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
