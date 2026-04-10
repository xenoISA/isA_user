-- Product Service Migration: backfill remaining billing profiles
-- Version: 015
-- Date: 2026-04-09
-- Description: marks internal platform components as non-invoiceable,
--              deactivates the legacy per-execution agent SKU, and fills in
--              generic abstract-service profiles for remaining data products.

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "internal_component",
      "invoiceable": false,
      "primary_meter": "runtime_minutes",
      "cost_components": [
        {
          "component_id": "platform_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        }
      ]
    }'::jsonb,
    true
),
updated_at = NOW()
WHERE product_id IN ('api_gateway', 'compute_general', 'nats_messaging');

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tool_calls",
      "cost_components": [
        {
          "component_id": "mcp_tool_provider",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "provider_requests",
          "unit_type": "request"
        },
        {
          "component_id": "mcp_tool_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "tool_calls",
          "unit_type": "request"
        }
      ]
    }'::jsonb,
    true
),
updated_at = NOW()
WHERE product_id = 'mcp_tools';

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
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
    }'::jsonb,
    true
),
updated_at = NOW()
WHERE product_type = 'data_processing'
  AND is_active = TRUE
  AND NOT (COALESCE(metadata, '{}'::jsonb) ? 'billing_profile');

UPDATE product.products
SET is_active = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb)
        || jsonb_build_object(
            'deprecated_reason',
            'Replaced by runtime-based agent billing products',
            'deprecated_by',
            jsonb_build_array('agent_runtime_dedicated', 'agent_runtime_shared')
        ),
    updated_at = NOW()
WHERE product_id = 'advanced_agent'
  AND is_active = TRUE;
