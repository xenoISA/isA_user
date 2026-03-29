-- Product Service Migration: Refresh product catalog to align with cost_definitions
-- Version: 007
-- Date: 2026-03-28
-- Description: Upsert products and product_pricing rows matching current cost_definitions (migration 003).
--              Soft-deactivate stale products from test data (migration 999).
-- Idempotent: Safe to run multiple times via INSERT ... ON CONFLICT ... DO UPDATE.
-- Parent Epic: #174

-- ====================
-- Step 1: Soft-deactivate stale products
-- ====================
-- These products exist in 999_insert_test_data_v2 but no longer match cost_definitions.

UPDATE product.products
SET is_active = FALSE, updated_at = NOW()
WHERE product_id IN ('gpt-4', 'claude-3-5-sonnet', 'prod_ai_tokens')
  AND is_active = TRUE;

-- ====================
-- Step 2: Upsert AI model products (from cost_definitions)
-- ====================

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
-- Claude Sonnet 4
('claude-sonnet-4', 'Claude Sonnet 4', 'CLAUDE-SONNET4',
 'Anthropic Claude Sonnet 4 model inference (claude-sonnet-4-20250514)',
 'ai_models', 'model_inference', 0.003, 'USD', 'per_token',
 '["advanced_reasoning", "coding", "analysis", "200k_context"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{"provider": "anthropic", "model": "claude-sonnet-4-20250514", "context_window": 200000, "input_cost_per_1k": 0.003, "output_cost_per_1k": 0.015}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- Claude Opus 4
('claude-opus-4', 'Claude Opus 4', 'CLAUDE-OPUS4',
 'Anthropic Claude Opus 4 model inference (claude-opus-4-20250514)',
 'ai_models', 'model_inference', 0.015, 'USD', 'per_token',
 '["frontier_reasoning", "complex_analysis", "coding", "200k_context"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{"provider": "anthropic", "model": "claude-opus-4-20250514", "context_window": 200000, "input_cost_per_1k": 0.015, "output_cost_per_1k": 0.075}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- Claude Haiku 3.5
('claude-haiku-35', 'Claude Haiku 3.5', 'CLAUDE-HAIKU35',
 'Anthropic Claude 3.5 Haiku model inference (claude-3-5-haiku-20241022)',
 'ai_models', 'model_inference', 0.0008, 'USD', 'per_token',
 '["fast_inference", "cost_effective", "200k_context"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "context_window": 200000, "input_cost_per_1k": 0.0008, "output_cost_per_1k": 0.004}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- GPT-4o (update existing row from 999)
('gpt-4o', 'GPT-4o', 'GPT4O',
 'OpenAI GPT-4o model inference (gpt-4o-2024-11-20)',
 'ai_models', 'model_inference', 0.0025, 'USD', 'per_token',
 '["advanced_reasoning", "multimodal", "vision", "128k_context"]'::jsonb,
 '{"max_tokens": 128000}'::jsonb,
 TRUE,
 '{"provider": "openai", "model": "gpt-4o-2024-11-20", "context_window": 128000, "input_cost_per_1k": 0.0025, "output_cost_per_1k": 0.01}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- GPT-4o Mini (update existing row from 999)
('gpt-4o-mini', 'GPT-4o Mini', 'GPT4O-MINI',
 'OpenAI GPT-4o Mini model inference (gpt-4o-mini-2024-07-18)',
 'ai_models', 'model_inference', 0.00015, 'USD', 'per_token',
 '["fast_inference", "cost_effective", "multimodal", "128k_context"]'::jsonb,
 '{"max_tokens": 128000}'::jsonb,
 TRUE,
 '{"provider": "openai", "model": "gpt-4o-mini-2024-07-18", "context_window": 128000, "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- Gemini 2.0 Flash
('gemini-2-flash', 'Gemini 2.0 Flash', 'GEMINI2-FLASH',
 'Google Gemini 2.0 Flash model inference',
 'ai_models', 'model_inference', 0.00015, 'USD', 'per_token',
 '["fast_inference", "cost_effective", "multimodal", "1m_context"]'::jsonb,
 '{"max_tokens": 1000000}'::jsonb,
 TRUE,
 '{"provider": "google", "model": "gemini-2.0-flash", "context_window": 1000000, "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006}'::jsonb,
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

-- ====================
-- Step 3: Upsert infrastructure / service products
-- ====================

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
-- MinIO Storage (existing from 999, refresh to match cost_definitions)
('minio_storage', 'MinIO Storage', 'MINIO-STORAGE',
 'S3-compatible object storage (MinIO)',
 'storage', 'storage_minio', 0.023, 'USD', 'monthly',
 '["object_storage", "s3_compatible", "versioning"]'::jsonb,
 '{"free_tier_gb": 5, "max_storage_gb": 1000}'::jsonb,
 TRUE,
 '{"provider": "internal", "model": "minio", "storage_type": "object", "cost_per_gb_month": 0.023, "egress_cost_per_gb": 0.009}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- MCP Tools
('mcp_tools', 'MCP Tools', 'MCP-TOOLS',
 'MCP tool execution services (web search, browser, code interpreter, image gen, STT, TTS)',
 'tools', 'mcp_service', 0.003, 'USD', 'per_request',
 '["web_search", "web_fetch", "browser_automation", "code_interpreter", "image_generation", "speech_to_text", "text_to_speech"]'::jsonb,
 '{"web_search_monthly": 100, "web_fetch_monthly": 200, "browser_minutes_monthly": 30, "code_interpreter_monthly": 100, "image_gen_monthly": 10, "stt_minutes_monthly": 60, "tts_chars_monthly": 10000}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "mcp_service"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- Agent Execution (existing from 999, refresh)
('advanced_agent', 'Advanced Agent', 'ADV-AGENT',
 'AI agent execution with reasoning, tool use, and memory',
 'ai_agents', 'agent_execution', 0.50, 'USD', 'per_execution',
 '["reasoning", "tool_use", "memory", "multi_step"]'::jsonb,
 '{"max_executions_per_month": 1000, "free_tier_executions": 10}'::jsonb,
 TRUE,
 '{"provider": "internal", "capabilities": ["reasoning", "tool_use", "memory"]}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- API Gateway (existing from 999, refresh)
('api_gateway', 'API Gateway', 'API-GATEWAY',
 'API gateway with rate limiting, authentication, and monitoring',
 'infrastructure', 'api_gateway', 3.50, 'USD', 'monthly',
 '["rate_limiting", "authentication", "monitoring", "load_balancing"]'::jsonb,
 '{"max_requests_per_month": 10000000, "free_tier_requests": 1000000}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "api_gateway"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- NATS Messaging
('nats_messaging', 'NATS Messaging', 'NATS-MSG',
 'NATS JetStream event messaging and streaming',
 'infrastructure', 'messaging', 0.001, 'USD', 'per_message',
 '["pub_sub", "jetstream", "queue_groups", "key_value"]'::jsonb,
 '{"max_messages_per_month": 10000000, "free_tier_messages": 100000}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "messaging", "model": "nats"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

-- Compute (general)
('compute_general', 'Compute', 'COMPUTE-GEN',
 'General compute resources for workloads',
 'infrastructure', 'compute', 0.01, 'USD', 'per_minute',
 '["container_execution", "gpu_access", "auto_scaling"]'::jsonb,
 '{"max_compute_minutes_per_month": 100000}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "compute"}'::jsonb,
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

-- ====================
-- Step 4: Upsert product_pricing rows
-- ====================

INSERT INTO product.product_pricing (
    pricing_id, product_id, tier_name,
    min_quantity, max_quantity,
    unit_price, currency, metadata
) VALUES
-- Claude Sonnet 4: input $0.003/1K, output $0.015/1K
('pricing_claude_sonnet4_input', 'claude-sonnet-4', 'input',
 0, NULL, 0.000003, 'USD',
 '{"unit": "token", "input_cost_per_1k": 0.003, "credits_per_1k": 390, "billing_type": "usage_based"}'::jsonb),

('pricing_claude_sonnet4_output', 'claude-sonnet-4', 'output',
 0, NULL, 0.000015, 'USD',
 '{"unit": "token", "output_cost_per_1k": 0.015, "credits_per_1k": 1950, "billing_type": "usage_based"}'::jsonb),

-- Claude Opus 4: input $0.015/1K, output $0.075/1K
('pricing_claude_opus4_input', 'claude-opus-4', 'input',
 0, NULL, 0.000015, 'USD',
 '{"unit": "token", "input_cost_per_1k": 0.015, "credits_per_1k": 1950, "billing_type": "usage_based"}'::jsonb),

('pricing_claude_opus4_output', 'claude-opus-4', 'output',
 0, NULL, 0.000075, 'USD',
 '{"unit": "token", "output_cost_per_1k": 0.075, "credits_per_1k": 9750, "billing_type": "usage_based"}'::jsonb),

-- Claude Haiku 3.5: input $0.0008/1K, output $0.004/1K
('pricing_claude_haiku35_input', 'claude-haiku-35', 'input',
 0, NULL, 0.0000008, 'USD',
 '{"unit": "token", "input_cost_per_1k": 0.0008, "credits_per_1k": 104, "billing_type": "usage_based"}'::jsonb),

('pricing_claude_haiku35_output', 'claude-haiku-35', 'output',
 0, NULL, 0.000004, 'USD',
 '{"unit": "token", "output_cost_per_1k": 0.004, "credits_per_1k": 520, "billing_type": "usage_based"}'::jsonb),

-- GPT-4o: input $0.0025/1K, output $0.01/1K (refresh existing)
('pricing_gpt4o_base', 'gpt-4o', 'base',
 0, NULL, 0.000005, 'USD',
 '{"unit": "token", "input_cost_per_1k": 0.0025, "output_cost_per_1k": 0.01, "credits_per_1k_input": 325, "credits_per_1k_output": 1300, "billing_type": "usage_based"}'::jsonb),

-- GPT-4o Mini: input $0.00015/1K, output $0.0006/1K (refresh existing)
('pricing_gpt4o_mini_base', 'gpt-4o-mini', 'base',
 0, NULL, 0.0000003, 'USD',
 '{"unit": "token", "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006, "credits_per_1k_input": 20, "credits_per_1k_output": 78, "billing_type": "usage_based"}'::jsonb),

-- Gemini 2.0 Flash: input $0.00015/1K, output $0.0006/1K
('pricing_gemini2_flash_base', 'gemini-2-flash', 'base',
 0, NULL, 0.0000003, 'USD',
 '{"unit": "token", "input_cost_per_1k": 0.00015, "output_cost_per_1k": 0.0006, "credits_per_1k_input": 20, "credits_per_1k_output": 78, "billing_type": "usage_based"}'::jsonb),

-- MinIO Storage (refresh existing tiers)
('pricing_minio_base', 'minio_storage', 'base',
 0, 107374182400, 0.000000000023, 'USD',
 '{"unit": "byte", "cost_per_gb_month": 0.023, "credits_per_gb_month": 3000, "free_tier_gb": 5}'::jsonb),

('pricing_minio_tier2', 'minio_storage', 'tier2',
 107374182400, NULL, 0.000000000020, 'USD',
 '{"unit": "byte", "cost_per_gb_month": 0.020, "discount": "volume_discount"}'::jsonb),

('pricing_minio_egress', 'minio_storage', 'egress',
 0, NULL, 0.000000009, 'USD',
 '{"unit": "byte", "cost_per_gb": 0.009, "credits_per_gb": 1170, "free_tier_gb": 10}'::jsonb),

-- MCP Tools (aggregate pricing by most common operation)
('pricing_mcp_tools_base', 'mcp_tools', 'base',
 0, NULL, 0.003, 'USD',
 '{"unit": "request", "web_search_per_req": 0.003, "web_fetch_per_req": 0.001, "browser_per_min": 0.01, "code_interpreter_per_exec": 0.002, "image_gen_per_image": 0.04, "stt_per_min": 0.006, "tts_per_1k_chars": 0.015}'::jsonb),

-- Agent Execution (refresh existing)
('pricing_agent_base', 'advanced_agent', 'base',
 0, 1000, 0.50, 'USD',
 '{"unit": "execution", "cost_per_execution": 0.50, "free_tier_executions": 10}'::jsonb),

-- API Gateway (refresh existing)
('pricing_api_gw_base', 'api_gateway', 'base',
 0, 1000000000, 0.0000035, 'USD',
 '{"unit": "request", "cost_per_million": 3.50, "free_tier_requests": 1000000}'::jsonb),

-- NATS Messaging
('pricing_nats_base', 'nats_messaging', 'base',
 0, NULL, 0.000001, 'USD',
 '{"unit": "message", "cost_per_million": 1.00, "free_tier_messages": 100000}'::jsonb),

-- Compute
('pricing_compute_base', 'compute_general', 'base',
 0, NULL, 0.01, 'USD',
 '{"unit": "minute", "cost_per_minute": 0.01}'::jsonb)

ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- ====================
-- Step 5: Verification — check alignment between products and cost_definitions
-- ====================
-- Run this query after migration to verify alignment:
--
-- SELECT
--     cd.model_name AS cost_model,
--     cd.provider AS cost_provider,
--     p.product_id,
--     p.is_active,
--     CASE
--         WHEN p.product_id IS NOT NULL THEN 'ALIGNED'
--         ELSE 'MISSING PRODUCT'
--     END AS status
-- FROM product.cost_definitions cd
-- LEFT JOIN product.products p
--     ON p.metadata->>'model' = cd.model_name
--    AND p.metadata->>'provider' = cd.provider
-- WHERE cd.service_type = 'model_inference'
--   AND cd.operation_type = 'input'
-- ORDER BY cd.provider, cd.model_name;
--
-- Expected: All 7 model rows show ALIGNED with is_active = TRUE.
-- Stale products (gpt-4, claude-3-5-sonnet, prod_ai_tokens) should show is_active = FALSE.
