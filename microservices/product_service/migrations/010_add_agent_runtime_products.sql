-- Product Service Migration: Add dedicated and shared agent runtime products
-- Version: 010
-- Date: 2026-04-09
-- Description: Seed runtime-occupancy SKUs for deployed and shared agent runtimes.
-- Idempotent: Safe to run multiple times via INSERT ... ON CONFLICT ... DO UPDATE.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('agent_runtime_dedicated', 'Dedicated Agent Runtime', 'AGENT-RUNTIME-DEDICATED',
 'Dedicated VM-backed agent runtime occupancy',
 'ai_agents', 'agent_runtime', 0.0300, 'USD', 'per_minute',
 '["dedicated_runtime", "isolated_vm", "managed_agent"]'::jsonb,
 '{"free_tier_minutes": 0}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "agent_runtime", "operation_type": "vm_occupancy", "runtime_class": "dedicated", "unit": "minute"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('agent_runtime_shared', 'Shared Agent Runtime', 'AGENT-RUNTIME-SHARED',
 'Shared managed agent runtime occupancy',
 'ai_agents', 'agent_runtime', 0.0100, 'USD', 'per_minute',
 '["shared_runtime", "managed_agent", "pooled_capacity"]'::jsonb,
 '{"free_tier_minutes": 0}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "agent_runtime", "operation_type": "vm_occupancy", "runtime_class": "shared", "unit": "minute"}'::jsonb,
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
('pricing_agent_runtime_dedicated_default', 'agent_runtime_dedicated', 'default', 0, NULL, 0.0300, 'USD',
 '{"unit": "minute", "billing_type": "usage_based"}'::jsonb),
('pricing_agent_runtime_shared_default', 'agent_runtime_shared', 'default', 0, NULL, 0.0100, 'USD',
 '{"unit": "minute", "billing_type": "usage_based"}'::jsonb)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
