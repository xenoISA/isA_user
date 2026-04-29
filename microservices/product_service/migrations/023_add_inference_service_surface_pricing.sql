-- 023_add_inference_service_surface_pricing.sql
-- Seeds customer-facing inference service products and service-surface pricing.
-- This keeps the existing schema but separates payer, service surface, and execution backend:
--   subscription_*  => who pays
--   product_id      => customer-facing service surface
--   usage_details   => actual execution backend / provider / engine

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('api', 'API Inference', 'API-INFERENCE',
 'Direct inference API surface with provider-selected execution backends',
 'compute', 'model_inference', 0.0000, 'USD', 'usage_based',
 '["model_inference", "api"]'::jsonb,
 '{"free_tier_tokens": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "model_inference",
    "service_surface": "api",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "api_provider_usage",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "provider_routed",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('codex-sub', 'Codex Subscription Inference', 'CODEX-SUB-INFERENCE',
 'Customer-facing Codex subscription proxy inference service',
 'compute', 'model_inference', 0.0013, 'USD', 'usage_based',
 '["model_inference", "proxy_sub", "codex-sub"]'::jsonb,
 '{"free_tier_tokens": 0}'::jsonb,
 TRUE,
 '{
    "provider": "codex-sub",
    "service_type": "model_inference",
    "service_surface": "codex-sub",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "codex_sub_proxy_usage",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "codex_sub_proxy",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-sub', 'Claude Subscription Inference', 'CLAUDE-SUB-INFERENCE',
 'Customer-facing Claude subscription proxy inference service',
 'compute', 'model_inference', 0.0015, 'USD', 'usage_based',
 '["model_inference", "proxy_sub", "claude-sub"]'::jsonb,
 '{"free_tier_tokens": 0}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic-sub",
    "service_type": "model_inference",
    "service_surface": "claude-sub",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "claude_sub_proxy_usage",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic_sub_proxy",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('local-gpu', 'Local GPU Inference', 'LOCAL-GPU-INFERENCE',
 'Customer-facing local GPU inference service routed to local GPU runtimes',
 'compute', 'model_inference', 0.0005, 'USD', 'usage_based',
 '["model_inference", "local_gpu"]'::jsonb,
 '{"free_tier_tokens": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "model_inference",
    "service_surface": "local-gpu",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "local_gpu_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "local_gpu",
          "meter_type": "tokens",
          "unit_type": "token"
        },
        {
          "component_id": "local_gpu_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "local_gpu",
          "meter_type": "gpu_seconds",
          "unit_type": "second"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('cloud-gpu', 'Cloud GPU Inference', 'CLOUD-GPU-INFERENCE',
 'Customer-facing cloud GPU inference service routed to Modal or similar GPU runtimes',
 'compute', 'model_inference', 0.0008, 'USD', 'usage_based',
 '["model_inference", "cloud_gpu", "modal"]'::jsonb,
 '{"free_tier_tokens": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "model_inference",
    "service_surface": "cloud-gpu",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "cloud_gpu_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "modal",
          "meter_type": "tokens",
          "unit_type": "token"
        },
        {
          "component_id": "cloud_gpu_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "modal",
          "meter_type": "gpu_seconds",
          "unit_type": "second"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('local-ollama', 'Local Ollama Inference', 'LOCAL-OLLAMA-INFERENCE',
 'Customer-facing local Ollama inference service',
 'compute', 'model_inference', 0.0002, 'USD', 'usage_based',
 '["model_inference", "local_ollama", "ollama"]'::jsonb,
 '{"free_tier_tokens": 0}'::jsonb,
 TRUE,
 '{
    "provider": "ollama",
    "service_type": "model_inference",
    "service_surface": "local-ollama",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "local_ollama_usage",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "ollama",
          "meter_type": "tokens",
          "unit_type": "token"
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

UPDATE product.cost_definitions
SET product_id = 'local-gpu',
    metadata = COALESCE(metadata, '{}'::jsonb) || '{"service_surface":"local-gpu"}'::jsonb,
    updated_at = NOW()
WHERE service_type = 'model_inference'
  AND COALESCE(metadata->>'backend', '') = 'local_gpu';

INSERT INTO product.cost_definitions (
    cost_id, product_id, service_type, provider, model_name, operation_type,
    cost_per_unit, unit_type, unit_size, original_cost_usd, margin_percentage,
    effective_from, effective_until, free_tier_limit, free_tier_period, is_active,
    description, metadata, created_at, updated_at
) VALUES
    ('cost_codex_sub_input', 'codex-sub', 'model_inference', 'codex-sub', NULL, 'input', 120, 'token', 1000, 0.0009, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Codex subscription proxy input token pricing fallback (per 1K tokens)',
     '{"service_surface":"codex-sub","backend":"cloud","sku_family":"proxy_sub_inference"}'::jsonb, NOW(), NOW()),
    ('cost_codex_sub_output', 'codex-sub', 'model_inference', 'codex-sub', NULL, 'output', 560, 'token', 1000, 0.0043, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Codex subscription proxy output token pricing fallback (per 1K tokens)',
     '{"service_surface":"codex-sub","backend":"cloud","sku_family":"proxy_sub_inference"}'::jsonb, NOW(), NOW()),

    ('cost_claude_sub_input', 'claude-sub', 'model_inference', 'anthropic-sub', NULL, 'input', 150, 'token', 1000, 0.0011, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Claude subscription proxy input token pricing fallback (per 1K tokens)',
     '{"service_surface":"claude-sub","backend":"cloud","sku_family":"proxy_sub_inference"}'::jsonb, NOW(), NOW()),
    ('cost_claude_sub_output', 'claude-sub', 'model_inference', 'anthropic-sub', NULL, 'output', 600, 'token', 1000, 0.0046, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Claude subscription proxy output token pricing fallback (per 1K tokens)',
     '{"service_surface":"claude-sub","backend":"cloud","sku_family":"proxy_sub_inference"}'::jsonb, NOW(), NOW()),

    ('cost_local_ollama_input', 'local-ollama', 'model_inference', 'ollama', NULL, 'input', 18, 'token', 1000, 0.00014, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Local Ollama input token pricing fallback (per 1K tokens)',
     '{"service_surface":"local-ollama","backend":"local","engine_used":"ollama","sku_family":"local_ollama_inference"}'::jsonb, NOW(), NOW()),
    ('cost_local_ollama_output', 'local-ollama', 'model_inference', 'ollama', NULL, 'output', 72, 'token', 1000, 0.00055, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Local Ollama output token pricing fallback (per 1K tokens)',
     '{"service_surface":"local-ollama","backend":"local","engine_used":"ollama","sku_family":"local_ollama_inference"}'::jsonb, NOW(), NOW()),

    ('cost_cloud_gpu_modal_input', 'cloud-gpu', 'model_inference', NULL, NULL, 'input', 65, 'token', 1000, 0.0005, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Cloud GPU shared inference input pricing fallback (per 1K tokens)',
     '{"service_surface":"cloud-gpu","backend":"modal","sku_family":"cloud_gpu_inference","tenancy_mode":"shared"}'::jsonb, NOW(), NOW()),
    ('cost_cloud_gpu_modal_output', 'cloud-gpu', 'model_inference', NULL, NULL, 'output', 260, 'token', 1000, 0.0020, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Cloud GPU shared inference output pricing fallback (per 1K tokens)',
     '{"service_surface":"cloud-gpu","backend":"modal","sku_family":"cloud_gpu_inference","tenancy_mode":"shared"}'::jsonb, NOW(), NOW()),
    ('cost_cloud_gpu_modal_gpu_seconds', 'cloud-gpu', 'model_inference', NULL, NULL, 'gpu_seconds', 18, 'second', 1, 0.00014, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Cloud GPU shared runtime pricing (per GPU-second)',
     '{"service_surface":"cloud-gpu","backend":"modal","sku_family":"cloud_gpu_inference","tenancy_mode":"shared","pricing_dimension":"gpu_seconds"}'::jsonb, NOW(), NOW()),
    ('cost_cloud_gpu_modal_prefill_seconds', 'cloud-gpu', 'model_inference', NULL, NULL, 'prefill_seconds', 8, 'second', 1, 0.00006, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Cloud GPU shared prefill pricing (per second)',
     '{"service_surface":"cloud-gpu","backend":"modal","sku_family":"cloud_gpu_inference","tenancy_mode":"shared","pricing_dimension":"prefill_seconds"}'::jsonb, NOW(), NOW()),
    ('cost_cloud_gpu_modal_queue_seconds', 'cloud-gpu', 'model_inference', NULL, NULL, 'queue_seconds', 2, 'second', 1, 0.000015, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Cloud GPU queue pricing (per second)',
     '{"service_surface":"cloud-gpu","backend":"modal","sku_family":"cloud_gpu_inference","tenancy_mode":"shared","pricing_dimension":"queue_seconds"}'::jsonb, NOW(), NOW()),
    ('cost_cloud_gpu_modal_cold_start_seconds', 'cloud-gpu', 'model_inference', NULL, NULL, 'cold_start_seconds', 10, 'second', 1, 0.00008, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Cloud GPU cold start pricing (per second)',
     '{"service_surface":"cloud-gpu","backend":"modal","sku_family":"cloud_gpu_inference","tenancy_mode":"shared","pricing_dimension":"cold_start_seconds"}'::jsonb, NOW(), NOW())
ON CONFLICT (cost_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    service_type = EXCLUDED.service_type,
    provider = EXCLUDED.provider,
    model_name = EXCLUDED.model_name,
    operation_type = EXCLUDED.operation_type,
    cost_per_unit = EXCLUDED.cost_per_unit,
    unit_type = EXCLUDED.unit_type,
    unit_size = EXCLUDED.unit_size,
    original_cost_usd = EXCLUDED.original_cost_usd,
    margin_percentage = EXCLUDED.margin_percentage,
    effective_from = EXCLUDED.effective_from,
    effective_until = EXCLUDED.effective_until,
    free_tier_limit = EXCLUDED.free_tier_limit,
    free_tier_period = EXCLUDED.free_tier_period,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
