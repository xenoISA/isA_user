-- Insert test data for billing service tests
-- This migration adds products and pricing needed for testing
-- Updated to match current schema (product.products and product.product_pricing)

-- 1. Insert Products
INSERT INTO product.products (product_id, product_name, product_code, description, category, product_type, base_price, currency, billing_interval, features, quota_limits, is_active, metadata, created_at, updated_at)
VALUES
    ('gpt-4', 'GPT-4 Model', 'GPT4-MODEL', 'OpenAI GPT-4 model inference', 'ai_models', 'model_inference', 0.03, 'USD', 'monthly',
     '["advanced_reasoning", "large_context"]'::jsonb,
     '{"max_tokens": 8192}'::jsonb,
     true,
     '{"provider": "openai", "model": "gpt-4", "context_window": 8192}'::jsonb,
     NOW(), NOW()),

    ('minio_storage', 'MinIO Storage', 'MINIO-STORAGE', 'Object storage service', 'storage', 'storage_minio', 0.023, 'USD', 'monthly',
     '["object_storage", "s3_compatible"]'::jsonb,
     '{"max_storage_gb": 1000}'::jsonb,
     true,
     '{"provider": "minio", "storage_type": "object"}'::jsonb,
     NOW(), NOW()),

    ('api_gateway', 'API Gateway', 'API-GATEWAY', 'API gateway service', 'infrastructure', 'api_gateway', 3.50, 'USD', 'monthly',
     '["rate_limiting", "authentication", "monitoring"]'::jsonb,
     '{"max_requests_per_month": 10000000}'::jsonb,
     true,
     '{"provider": "internal", "features": ["rate_limiting", "authentication"]}'::jsonb,
     NOW(), NOW()),

    ('advanced_agent', 'Advanced Agent', 'ADV-AGENT', 'Advanced AI agent execution', 'ai_agents', 'agent_execution', 0.50, 'USD', 'per_execution',
     '["reasoning", "tool_use", "memory"]'::jsonb,
     '{"max_executions_per_month": 1000}'::jsonb,
     true,
     '{"provider": "internal", "capabilities": ["reasoning", "tool_use"]}'::jsonb,
     NOW(), NOW())
ON CONFLICT (product_id) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    description = EXCLUDED.description,
    base_price = EXCLUDED.base_price,
    updated_at = NOW();

-- 2. Insert Pricing Tiers
-- GPT-4 Pricing: $0.03 per 1000 tokens (which is $0.00003 per token)
INSERT INTO product.product_pricing (pricing_id, product_id, tier_name, min_quantity, max_quantity, unit_price, currency, metadata, created_at, updated_at)
VALUES
    ('pricing_gpt4_base', 'gpt-4', 'base', 0, NULL, 0.00003, 'USD',
     '{"unit": "token", "cost_per_1k_tokens": 0.03, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW())
ON CONFLICT (pricing_id) DO UPDATE SET
    unit_price = EXCLUDED.unit_price,
    updated_at = NOW();

-- MinIO Storage Pricing: $0.023 per GB per month (which is $0.000000000023 per byte)
INSERT INTO product.product_pricing (pricing_id, product_id, tier_name, min_quantity, max_quantity, unit_price, currency, metadata, created_at, updated_at)
VALUES
    ('pricing_minio_base', 'minio_storage', 'base', 0, 107374182400, 0.000000000023, 'USD',
     '{"unit": "byte", "cost_per_gb_month": 0.023, "free_tier_gb": 1, "free_tier_bytes": 1073741824}'::jsonb,
     NOW(), NOW()),
    ('pricing_minio_tier2', 'minio_storage', 'tier2', 107374182400, NULL, 0.000000000020, 'USD',
     '{"unit": "byte", "cost_per_gb_month": 0.020, "discount": "volume_discount"}'::jsonb,
     NOW(), NOW())
ON CONFLICT (pricing_id) DO UPDATE SET
    unit_price = EXCLUDED.unit_price,
    updated_at = NOW();

-- API Gateway Pricing: $3.50 per million requests (which is $0.0000035 per request)
INSERT INTO product.product_pricing (pricing_id, product_id, tier_name, min_quantity, max_quantity, unit_price, currency, metadata, created_at, updated_at)
VALUES
    ('pricing_api_gw_base', 'api_gateway', 'base', 0, 1000000000, 0.0000035, 'USD',
     '{"unit": "request", "cost_per_million": 3.50, "free_tier_requests": 1000000}'::jsonb,
     NOW(), NOW())
ON CONFLICT (pricing_id) DO UPDATE SET
    unit_price = EXCLUDED.unit_price,
    updated_at = NOW();

-- Advanced Agent Pricing: $0.50 per execution
INSERT INTO product.product_pricing (pricing_id, product_id, tier_name, min_quantity, max_quantity, unit_price, currency, metadata, created_at, updated_at)
VALUES
    ('pricing_agent_base', 'advanced_agent', 'base', 0, 1000, 0.50, 'USD',
     '{"unit": "execution", "cost_per_execution": 0.50, "free_tier_executions": 10}'::jsonb,
     NOW(), NOW())
ON CONFLICT (pricing_id) DO UPDATE SET
    unit_price = EXCLUDED.unit_price,
    updated_at = NOW();
