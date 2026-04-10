-- Product Service Migration: Backfill billing profiles for abstract-service products
-- Version: 012
-- Date: 2026-04-09
-- Description: Annotate current customer-facing products with explicit billing profiles
--              and bundled cost components so pricing and reporting can distinguish
--              invoiceable abstract services from underlying resource or external-API cost inputs.

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "tokens",
          "unit_type": "token",
          "notes": "Provider-backed model inference token cost"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id IN ('gpt-4o', 'gpt-4o-mini');

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
          "provider": "openai",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id = 'mcp_service';

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "runtime_minutes",
      "cost_components": [
        {
          "component_id": "agent_runtime_capacity",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute",
          "notes": "Managed runtime occupancy for deployed or shared agents"
        },
        {
          "component_id": "agent_runtime_network",
          "component_type": "network",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "network_session",
          "unit_type": "request"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id IN ('agent_runtime_dedicated', 'agent_runtime_shared');

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "request_count",
      "cost_components": [
        {
          "component_id": "web_execution_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "web_access_stack",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "provider_requests",
          "unit_type": "request",
          "notes": "May include browser, proxy, phone, captcha, or search providers"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id IN ('web_search', 'web_deep_search', 'web_crawl');

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "summary_requests",
      "cost_components": [
        {
          "component_id": "web_access_stack",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "provider_requests",
          "unit_type": "request"
        },
        {
          "component_id": "summary_model_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id = 'web_search_summary';

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "automation_executions",
      "cost_components": [
        {
          "component_id": "web_execution_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "web_access_stack",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "provider_requests",
          "unit_type": "request"
        },
        {
          "component_id": "automation_model_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id = 'web_automation';

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "execution_count",
      "cost_components": [
        {
          "component_id": "python_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "runtime_minutes",
          "unit_type": "minute"
        },
        {
          "component_id": "python_scratch_storage",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "scratch_storage",
          "unit_type": "gb"
        },
        {
          "component_id": "python_network_egress",
          "component_type": "network",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "egress_gb",
          "unit_type": "gb"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id = 'python_repl_execution';

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
          "unit_type": "request",
          "notes": "Vector retrieval and hybrid index access are bundled into the abstract data product"
        },
        {
          "component_id": "hybrid_data_model_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id IN (
    'digital_knowledge_store',
    'digital_knowledge_search',
    'digital_rag_response',
    'data_catalog_search',
    'data_fabric_query'
);

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    '{
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "storage_gb_months",
      "cost_components": [
        {
          "component_id": "object_storage_capacity",
          "component_type": "storage",
          "bundled": true,
          "customer_visible": false,
          "provider": "minio",
          "meter_type": "storage_gb_month",
          "unit_type": "gb_month"
        },
        {
          "component_id": "storage_egress",
          "component_type": "network",
          "bundled": false,
          "customer_visible": true,
          "provider": "internal",
          "meter_type": "egress_gb",
          "unit_type": "gb",
          "notes": "May be invoiced separately when egress billing is enabled"
        }
      ]
    }'::jsonb,
    true
)
WHERE product_id = 'minio_storage';
