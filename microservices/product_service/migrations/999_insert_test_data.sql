-- Insert test data for billing service tests
-- This migration adds products, plans, and pricing needed for testing

-- 1. Insert Service Plans
INSERT INTO product.service_plans (plan_id, plan_name, plan_description, plan_type, billing_cycle, base_price, currency, is_active, features, limitations, created_at, updated_at)
VALUES
    ('free-plan', 'Free Plan', 'Free tier for testing', 'freemium', 'monthly', 0.00, 'USD', true,
     '{"basic_access": true, "test_mode": true}'::jsonb,
     '{"max_requests": 1000, "max_storage": 1073741824}'::jsonb,
     NOW(), NOW())
ON CONFLICT (plan_id) DO UPDATE SET
    plan_name = EXCLUDED.plan_name,
    updated_at = NOW();

-- 2. Insert Products
INSERT INTO product.products (product_id, product_name, product_description, product_type, category, is_active, metadata, created_at, updated_at)
VALUES
    ('gpt-4', 'GPT-4 Model', 'OpenAI GPT-4 model inference', 'model_inference', 'ai_models', true,
     '{"provider": "openai", "model": "gpt-4", "context_window": 8192}'::jsonb,
     NOW(), NOW()),
    ('minio_storage', 'MinIO Storage', 'Object storage service', 'storage_minio', 'storage', true,
     '{"provider": "minio", "storage_type": "object"}'::jsonb,
     NOW(), NOW()),
    ('api_gateway', 'API Gateway', 'API gateway service', 'api_gateway', 'infrastructure', true,
     '{"provider": "internal", "features": ["rate_limiting", "authentication"]}'::jsonb,
     NOW(), NOW()),
    ('advanced_agent', 'Advanced Agent', 'Advanced AI agent execution', 'agent_execution', 'ai_agents', true,
     '{"provider": "internal", "capabilities": ["reasoning", "tool_use"]}'::jsonb,
     NOW(), NOW())
ON CONFLICT (product_id) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    updated_at = NOW();

-- 3. Insert Pricing Models
INSERT INTO product.pricing_models (pricing_id, product_id, pricing_type, base_unit_price, unit, currency, billing_cycle, free_tier_limit, is_active, pricing_tiers, metadata, created_at, updated_at)
VALUES
    -- GPT-4: $0.03 per 1000 tokens
    ('pricing_gpt4', 'gpt-4', 'usage_based', 0.00003, 'token', 'USD', 'monthly', 0, true,
     '[]'::jsonb,
     '{"cost_per_1k_tokens": 0.03}'::jsonb,
     NOW(), NOW()),

    -- MinIO Storage: $0.023 per GB per month
    ('pricing_minio', 'minio_storage', 'usage_based', 0.000000000023, 'byte', 'USD', 'monthly', 1073741824, true,
     '[{"min_units": 0, "max_units": 107374182400, "unit_price": 0.000000000023}]'::jsonb,
     '{"cost_per_gb_month": 0.023, "free_tier_gb": 1}'::jsonb,
     NOW(), NOW()),

    -- API Gateway: $3.50 per million requests
    ('pricing_api_gw', 'api_gateway', 'usage_based', 0.0000035, 'request', 'USD', 'monthly', 1000000, true,
     '[{"min_units": 0, "max_units": 1000000000, "unit_price": 0.0000035}]'::jsonb,
     '{"cost_per_million": 3.50, "free_tier_requests": 1000000}'::jsonb,
     NOW(), NOW()),

    -- Advanced Agent: $0.50 per execution
    ('pricing_agent', 'advanced_agent', 'usage_based', 0.50, 'execution', 'USD', 'monthly', 10, true,
     '[{"min_units": 0, "max_units": 1000, "unit_price": 0.50}]'::jsonb,
     '{"cost_per_execution": 0.50, "free_tier_executions": 10}'::jsonb,
     NOW(), NOW())
ON CONFLICT (pricing_id) DO UPDATE SET
    base_unit_price = EXCLUDED.base_unit_price,
    updated_at = NOW();

-- 4. Link products to free plan
INSERT INTO product.plan_products (plan_id, product_id, included_quantity, overage_pricing_id, is_unlimited, created_at)
VALUES
    ('free-plan', 'gpt-4', 10000, 'pricing_gpt4', false, NOW()),
    ('free-plan', 'minio_storage', 1073741824, 'pricing_minio', false, NOW()),
    ('free-plan', 'api_gateway', 1000, 'pricing_api_gw', false, NOW()),
    ('free-plan', 'advanced_agent', 5, 'pricing_agent', false, NOW())
ON CONFLICT (plan_id, product_id) DO UPDATE SET
    included_quantity = EXCLUDED.included_quantity,
    updated_at = NOW();
