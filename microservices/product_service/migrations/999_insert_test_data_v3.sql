-- Insert test data for product service tests (v3)
-- Updated to match current cost_definitions models
-- Replaces 999_insert_test_data_v2.sql

-- 1. Deactivate stale test products
UPDATE product.products SET is_active = FALSE
WHERE product_id IN ('gpt-4', 'claude-3-5-sonnet', 'prod_ai_tokens')
  AND is_active = TRUE;

-- 2. Insert Current AI Model Products
INSERT INTO product.products (product_id, product_name, product_code, description, category, product_type, base_price, currency, billing_interval, features, quota_limits, is_active, metadata, created_at, updated_at)
VALUES
    -- Claude Sonnet 4
    ('claude-sonnet-4', 'Claude Sonnet 4', 'CLAUDE-SONNET-4', 'Anthropic Claude Sonnet 4 model inference', 'ai_models', 'model_inference', 0.003, 'USD', 'per_token',
     '["advanced_reasoning", "coding", "analysis", "vision"]'::jsonb,
     '{"max_tokens": 200000}'::jsonb,
     true,
     '{"provider": "anthropic", "model": "claude-sonnet-4-20250514", "context_window": 200000, "input_cost_per_1k": 0.003, "output_cost_per_1k": 0.015}'::jsonb,
     NOW(), NOW()),

    -- Claude Opus 4
    ('claude-opus-4', 'Claude Opus 4', 'CLAUDE-OPUS-4', 'Anthropic Claude Opus 4 model inference', 'ai_models', 'model_inference', 0.015, 'USD', 'per_token',
     '["advanced_reasoning", "coding", "analysis", "vision", "deep_thinking"]'::jsonb,
     '{"max_tokens": 200000}'::jsonb,
     true,
     '{"provider": "anthropic", "model": "claude-opus-4-20250514", "context_window": 200000, "input_cost_per_1k": 0.015, "output_cost_per_1k": 0.075}'::jsonb,
     NOW(), NOW()),

    -- Claude Haiku 3.5
    ('claude-haiku-35', 'Claude Haiku 3.5', 'CLAUDE-HAIKU-35', 'Anthropic Claude Haiku 3.5 model inference', 'ai_models', 'model_inference', 0.0008, 'USD', 'per_token',
     '["fast_inference", "cost_effective", "coding"]'::jsonb,
     '{"max_tokens": 200000}'::jsonb,
     true,
     '{"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "context_window": 200000, "input_cost_per_1k": 0.0008, "output_cost_per_1k": 0.004}'::jsonb,
     NOW(), NOW()),

    -- GPT-4o
    ('gpt-4o', 'GPT-4o', 'GPT4O', 'OpenAI GPT-4o model inference', 'ai_models', 'model_inference', 0.0025, 'USD', 'per_token',
     '["advanced_reasoning", "multimodal", "vision"]'::jsonb,
     '{"max_tokens": 128000}'::jsonb,
     true,
     '{"provider": "openai", "model": "gpt-4o", "context_window": 128000, "input_cost_per_1k": 0.0025, "output_cost_per_1k": 0.01}'::jsonb,
     NOW(), NOW()),

    -- GPT-4o Mini
    ('gpt-4o-mini', 'GPT-4o Mini', 'GPT4O-MINI', 'OpenAI GPT-4o Mini model inference', 'ai_models', 'model_inference', 0.00015, 'USD', 'per_token',
     '["fast_inference", "cost_effective", "multimodal"]'::jsonb,
     '{"max_tokens": 128000}'::jsonb,
     true,
     '{"provider": "openai", "model": "gpt-4o-mini", "context_window": 128000, "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006}'::jsonb,
     NOW(), NOW()),

    -- Gemini 2.0 Flash
    ('gemini-2-flash', 'Gemini 2.0 Flash', 'GEMINI-2-FLASH', 'Google Gemini 2.0 Flash model inference', 'ai_models', 'model_inference', 0.00015, 'USD', 'per_token',
     '["fast_inference", "cost_effective", "multimodal", "long_context"]'::jsonb,
     '{"max_tokens": 1000000}'::jsonb,
     true,
     '{"provider": "google", "model": "gemini-2.0-flash", "context_window": 1000000, "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006}'::jsonb,
     NOW(), NOW()),

    -- Infrastructure: MinIO Storage
    ('minio_storage', 'MinIO Storage', 'MINIO-STORAGE', 'Object storage service', 'storage', 'storage_minio', 0.023, 'USD', 'monthly',
     '["object_storage", "s3_compatible"]'::jsonb,
     '{"max_storage_gb": 1000}'::jsonb,
     true,
     '{"provider": "minio", "storage_type": "object"}'::jsonb,
     NOW(), NOW()),

    -- Infrastructure: API Gateway
    ('api_gateway', 'API Gateway', 'API-GATEWAY', 'API gateway service', 'infrastructure', 'api_gateway', 3.50, 'USD', 'monthly',
     '["rate_limiting", "authentication", "monitoring"]'::jsonb,
     '{"max_requests_per_month": 10000000}'::jsonb,
     true,
     '{"provider": "internal", "features": ["rate_limiting", "authentication"]}'::jsonb,
     NOW(), NOW()),

    -- Infrastructure: Advanced Agent
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
    features = EXCLUDED.features,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- 3. Insert Pricing Tiers for AI Models
INSERT INTO product.product_pricing (pricing_id, product_id, tier_name, min_quantity, max_quantity, unit_price, currency, metadata, created_at, updated_at)
VALUES
    -- Claude Sonnet 4: $3/1M input, $15/1M output
    ('pricing_claude_sonnet4_base', 'claude-sonnet-4', 'base', 0, NULL, 0.000003, 'USD',
     '{"unit": "token", "input_cost_per_1k": 0.003, "output_cost_per_1k": 0.015, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW()),

    -- Claude Opus 4: $15/1M input, $75/1M output
    ('pricing_claude_opus4_base', 'claude-opus-4', 'base', 0, NULL, 0.000015, 'USD',
     '{"unit": "token", "input_cost_per_1k": 0.015, "output_cost_per_1k": 0.075, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW()),

    -- Claude Haiku 3.5: $0.80/1M input, $4/1M output
    ('pricing_claude_haiku35_base', 'claude-haiku-35', 'base', 0, NULL, 0.0000008, 'USD',
     '{"unit": "token", "input_cost_per_1k": 0.0008, "output_cost_per_1k": 0.004, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW()),

    -- GPT-4o: $2.50/1M input, $10/1M output
    ('pricing_gpt4o_base', 'gpt-4o', 'base', 0, NULL, 0.0000025, 'USD',
     '{"unit": "token", "input_cost_per_1k": 0.0025, "output_cost_per_1k": 0.01, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW()),

    -- GPT-4o Mini: $0.15/1M input, $0.60/1M output
    ('pricing_gpt4o_mini_base', 'gpt-4o-mini', 'base', 0, NULL, 0.00000015, 'USD',
     '{"unit": "token", "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW()),

    -- Gemini 2.0 Flash: $0.15/1M input, $0.60/1M output
    ('pricing_gemini2_flash_base', 'gemini-2-flash', 'base', 0, NULL, 0.00000015, 'USD',
     '{"unit": "token", "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006, "billing_type": "usage_based"}'::jsonb,
     NOW(), NOW()),

    -- MinIO Storage: $0.023/GB/month
    ('pricing_minio_base', 'minio_storage', 'base', 0, 107374182400, 0.000000000023, 'USD',
     '{"unit": "byte", "cost_per_gb_month": 0.023, "free_tier_gb": 1}'::jsonb,
     NOW(), NOW()),

    -- API Gateway: $3.50/million requests
    ('pricing_api_gw_base', 'api_gateway', 'base', 0, 1000000000, 0.0000035, 'USD',
     '{"unit": "request", "cost_per_million": 3.50, "free_tier_requests": 1000000}'::jsonb,
     NOW(), NOW()),

    -- Advanced Agent: $0.50/execution
    ('pricing_agent_base', 'advanced_agent', 'base', 0, 1000, 0.50, 'USD',
     '{"unit": "execution", "cost_per_execution": 0.50, "free_tier_executions": 10}'::jsonb,
     NOW(), NOW())
ON CONFLICT (pricing_id) DO UPDATE SET
    unit_price = EXCLUDED.unit_price,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
