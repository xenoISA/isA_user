-- Product Service Migration: Add dedicated local GPU endpoint products
-- Version: 024
-- Date: 2026-05-13
-- Description: Seed reservation-style pricing for provisioned local GPU inference endpoints.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('local-gpu-dedicated-endpoint', 'Dedicated Local GPU Endpoint', 'LOCAL-GPU-DEDICATED-ENDPOINT',
 'Provisioned local GPU inference endpoint billed by reserved runtime and warm idle time',
 'compute', 'model_inference', 0.0000, 'USD', 'usage_based',
 '["model_inference", "local_gpu", "dedicated_endpoint", "reservation_billed"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "model_inference",
    "service_surface": "local-gpu-dedicated-endpoint",
    "backend": "local_gpu",
    "tenancy_mode": "dedicated",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "provisioned_gpu_seconds",
      "cost_components": [
        {
          "component_id": "dedicated_local_gpu_reservation",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "local_gpu",
          "meter_type": "provisioned_gpu_seconds",
          "unit_type": "second"
        },
        {
          "component_id": "dedicated_local_gpu_warm_idle",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "local_gpu",
          "meter_type": "warm_idle_seconds",
          "unit_type": "second"
        }
      ],
      "attribution_keys": ["endpoint_id", "deployment_id", "model", "gpu_type", "gpu_count"]
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
('pricing_local_gpu_dedicated_endpoint_default', 'local-gpu-dedicated-endpoint', 'default', 0, NULL, 0.00018, 'USD',
 '{"unit":"second","billing_type":"usage_based","service_type":"model_inference","backend":"local_gpu","tenancy_mode":"dedicated","primary_meter":"provisioned_gpu_seconds"}'::jsonb)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

INSERT INTO product.cost_definitions (
    cost_id, product_id, service_type, provider, model_name, operation_type,
    cost_per_unit, unit_type, unit_size, original_cost_usd, margin_percentage,
    effective_from, effective_until, free_tier_limit, free_tier_period, is_active,
    description, metadata, created_at, updated_at
) VALUES
    ('cost_local_gpu_dedicated_provisioned_gpu_seconds', 'local-gpu-dedicated-endpoint', 'model_inference', 'local_gpu', NULL, 'provisioned_gpu_seconds',
     24, 'second', 1, 0.00018, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Dedicated local GPU endpoint reservation pricing (per provisioned GPU-second)',
     '{"service_surface":"local-gpu-dedicated-endpoint","backend":"local_gpu","tenancy_mode":"dedicated","pricing_dimension":"provisioned_gpu_seconds","requires_attribution":["endpoint_id","deployment_id"]}'::jsonb, NOW(), NOW()),
    ('cost_local_gpu_dedicated_warm_idle_seconds', 'local-gpu-dedicated-endpoint', 'model_inference', 'local_gpu', NULL, 'warm_idle_seconds',
     8, 'second', 1, 0.00006, 30.0, NOW(), NULL, 0, 'monthly', TRUE,
     'Dedicated local GPU endpoint warm idle pricing (per idle second)',
     '{"service_surface":"local-gpu-dedicated-endpoint","backend":"local_gpu","tenancy_mode":"dedicated","pricing_dimension":"warm_idle_seconds","requires_attribution":["endpoint_id","deployment_id"]}'::jsonb, NOW(), NOW())
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
