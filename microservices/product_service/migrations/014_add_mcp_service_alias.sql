-- Product Service Migration: canonical MCP service product alias
-- Version: 014
-- Date: 2026-04-09
-- Description: Add canonical mcp_service product/pricing rows alongside legacy mcp_tools

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    created_at, updated_at
) VALUES (
    'mcp_service',
    'MCP Service',
    'MCP-SERVICE',
    'Managed MCP tool execution for browser, fetch, code, image, and speech workloads',
    'tools',
    'mcp_service',
    0.003,
    'USD',
    'per_request',
    '["web_search", "web_fetch", "browser_automation", "code_interpreter", "image_generation", "speech_to_text", "text_to_speech"]'::jsonb,
    '{
      "web_search_monthly": 100,
      "web_fetch_monthly": 200,
      "browser_minutes_monthly": 30,
      "code_interpreter_monthly": 100,
      "image_gen_monthly": 10,
      "stt_minutes_monthly": 60,
      "tts_chars_monthly": 10000
    }'::jsonb,
    TRUE,
    '{
      "provider": "internal",
      "service_type": "mcp_service",
      "alias_of": "mcp_tools",
      "billing_profile": {
        "billing_surface": "abstract_service",
        "invoiceable": true,
        "primary_meter": "tool_calls",
        "cost_components": [
          {
            "component_id": "mcp_tool_provider",
            "component_type": "external_api",
            "bundled": true,
            "customer_visible": false,
            "provider": "internal"
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
      }
    }'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (product_id) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    product_code = EXCLUDED.product_code,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    product_type = EXCLUDED.product_type,
    base_price = EXCLUDED.base_price,
    currency = EXCLUDED.currency,
    billing_interval = EXCLUDED.billing_interval,
    features = EXCLUDED.features,
    quota_limits = EXCLUDED.quota_limits,
    is_active = EXCLUDED.is_active,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

INSERT INTO product.product_pricing (
    pricing_id, product_id, tier_name,
    min_quantity, max_quantity, unit_price, currency, metadata,
    created_at, updated_at
) VALUES (
    'pricing_mcp_service_base',
    'mcp_service',
    'base',
    0,
    NULL,
    0.003,
    'USD',
    '{
      "unit": "request",
      "web_search_per_req": 0.003,
      "web_fetch_per_req": 0.001,
      "browser_per_min": 0.01,
      "code_interpreter_per_exec": 0.002,
      "image_gen_per_image": 0.04,
      "stt_per_min": 0.006,
      "tts_per_1k_chars": 0.015
    }'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
