-- Product Service Migration: add remaining configured llm/omni SKUs
-- Version: 018
-- Date: 2026-04-09
-- Description: seeds the remaining LLM and omni model SKUs that are currently
--              configured in isA_Model provider YAMLs but still missing from
--              product_service. This keeps the billing catalog aligned with
--              the actual model IDs that can be emitted on the token billing
--              path.
--
-- Pricing source:
-- - isA_Model provider configuration snapshots on 2026-04-09:
--   * isa_model/core/config/providers/openai_models.yaml
--   * isa_model/core/config/providers/cerebras_models.yaml
--   * isa_model/core/config/providers/openrouter_models.yaml

WITH seeded_models (
    product_id,
    product_name,
    provider,
    transport_model,
    description,
    input_cost_per_1m,
    output_cost_per_1m,
    context_window,
    max_output_tokens,
    supports_vision,
    performance_tier
) AS (
    VALUES
    ('claude-3-opus', 'Claude 3 Opus', 'openrouter', 'anthropic/claude-3-opus', 'Anthropic''s most powerful model for complex tasks', 15.000000, 75.000000, 200000, 4096, TRUE, 'premium'),
    ('claude-3.5-sonnet', 'Claude 3.5 Sonnet', 'openrouter', 'anthropic/claude-3.5-sonnet', 'Anthropic''s Claude 3.5 Sonnet - excellent balance of intelligence and speed', 3.000000, 15.000000, 200000, 8192, TRUE, 'premium'),
    ('deepseek-chat-v3-0324', 'DeepSeek Chat V3 0324', 'openrouter', 'deepseek/deepseek-chat-v3-0324', 'DeepSeek Chat V3 - fast and capable chat model', 0.140000, 0.280000, 64000, 8192, FALSE, 'standard'),
    ('deepseek-r1', 'DeepSeek R1', 'openrouter', 'deepseek/deepseek-r1', 'DeepSeek R1 - advanced reasoning model with chain-of-thought', 0.550000, 2.190000, 64000, 8192, FALSE, 'premium'),
    ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash Experimental', 'openrouter', 'google/gemini-2.0-flash-exp', 'Google''s fast experimental Gemini 2.0 model', 0.000000, 0.000000, 1000000, 8192, TRUE, 'standard'),
    ('gemini-pro-1.5', 'Gemini Pro 1.5', 'openrouter', 'google/gemini-pro-1.5', 'Google''s Gemini Pro 1.5 with massive context window', 1.250000, 5.000000, 2000000, 8192, TRUE, 'premium'),
    ('glm-5', 'GLM-5', 'openrouter', 'zhipu/glm-5', 'GLM-5 744B MoE — 40B active params, frontier model on SWE-bench/AIME, 200K context', 1.000000, 3.200000, 200000, 16384, FALSE, 'premium'),
    ('glm-5-turbo', 'GLM-5 Turbo', 'openrouter', 'zhipu/glm-5-turbo', 'GLM-5 Turbo — optimized for high-throughput agentic workloads, multi-step tool chains', 0.500000, 1.600000, 200000, 16384, FALSE, 'high'),
    ('glm-5.1', 'GLM-5.1', 'openrouter', 'zhipu/glm-5.1', 'GLM-5.1 — latest Zhipu model, 94.6% of Claude Opus 4.6 coding perf, open-weights', 1.000000, 3.200000, 200000, 16384, FALSE, 'premium'),
    ('gpt-oss-120b', 'GPT OSS 120B', 'cerebras', 'gpt-oss-120b', 'OpenAI GPT OSS 120B - Ultra-fast inference at ~3000 tokens/sec. Best performance-to-speed ratio.', 1.000000, 1.000000, 8192, 8192, FALSE, 'premium'),
    ('llama-3.1-sonar-large-128k-online', 'Llama 3.1 Sonar Large 128K Online', 'openrouter', 'perplexity/llama-3.1-sonar-large-128k-online', 'Perplexity''s online model with real-time web search', 1.000000, 1.000000, 128000, 8192, FALSE, 'premium'),
    ('llama-3.3-70b', 'Llama 3.3 70B', 'cerebras', 'llama-3.3-70b', 'Llama 3.3 70B - Powerful reasoning at ~2100 tokens/sec. Excellent for complex tasks.', 0.600000, 0.600000, 8192, 8192, FALSE, 'premium'),
    ('llama-3.3-70b-instruct', 'Llama 3.3 70B Instruct', 'openrouter', 'meta-llama/llama-3.3-70b-instruct', 'Meta''s Llama 3.3 70B - powerful open-source model', 0.400000, 0.400000, 128000, 8192, FALSE, 'high'),
    ('llama-4-scout-17b-16e-instruct', 'Llama 4 Scout 17B 16E Instruct', 'cerebras', 'llama-4-scout-17b-16e-instruct', 'Llama 4 Scout 109B - High-performance instruction following at ~2600 tokens/sec.', 0.800000, 0.800000, 8192, 8192, FALSE, 'premium'),
    ('llama3.1-8b', 'Llama 3.1 8B', 'cerebras', 'llama3.1-8b', 'Llama 3.1 8B - Fast and efficient at ~2200 tokens/sec. Cost-effective for general tasks.', 0.100000, 0.100000, 8192, 8192, FALSE, 'standard'),
    ('mistral-large', 'Mistral Large', 'openrouter', 'mistralai/mistral-large', 'Mistral''s flagship large model', 2.000000, 6.000000, 128000, 8192, FALSE, 'premium'),
    ('mixtral-8x22b-instruct', 'Mixtral 8x22B Instruct', 'openrouter', 'mistralai/mixtral-8x22b-instruct', 'Mistral''s Mixture of Experts model - excellent price/performance', 0.900000, 0.900000, 64000, 8192, FALSE, 'high'),
    ('o4-mini', 'o4-mini', 'openai', 'o4-mini', 'OpenAI''s o4-mini reasoning model optimized for fast, cost-efficient reasoning with exceptional performance in math, coding, and visual tasks.', 1.100000, 4.400000, 200000, 100000, TRUE, 'premium'),
    ('o4-mini-deep-search', 'o4-mini Deep Search', 'openai', 'o4-mini-deep-search', 'OpenAI''s o4-mini deep research model for comprehensive research tasks with web search capabilities and in-depth analysis.', 2.000000, 8.000000, 200000, 100000, TRUE, 'premium'),
    ('qwen-2.5-72b-instruct', 'Qwen 2.5 72B Instruct', 'openrouter', 'qwen/qwen-2.5-72b-instruct', 'Alibaba''s Qwen 2.5 72B - strong multilingual capabilities', 0.400000, 0.400000, 128000, 8192, FALSE, 'high'),
    ('qwen-3-32b', 'Qwen 3 32B', 'cerebras', 'qwen-3-32b', 'Qwen 3 32B - Balanced performance at ~2600 tokens/sec. Good for various tasks.', 0.400000, 0.400000, 32768, 8192, FALSE, 'standard'),
    ('qwen3.5-122b-a10b', 'Qwen3.5 122B A10B', 'openrouter', 'qwen/qwen3.5-122b-a10b', 'Qwen3.5 122B MoE — 10B active params, strong balance of speed and quality, multimodal', 0.350000, 1.400000, 262144, 8192, TRUE, 'high'),
    ('qwen3.5-27b', 'Qwen3.5 27B', 'openrouter', 'qwen/qwen3.5-27b', 'Qwen3.5 27B Dense — fast dense model with linear attention, strong vision-language', 0.200000, 0.800000, 262144, 8192, TRUE, 'standard'),
    ('qwen3.5-35b-a3b', 'Qwen3.5 35B A3B', 'openrouter', 'qwen/qwen3.5-35b-a3b', 'Qwen3.5 35B MoE — 3B active params, ultra-efficient for coding and chat, multimodal', 0.140000, 0.560000, 262144, 8192, TRUE, 'standard'),
    ('qwen3.5-397b-a17b', 'Qwen3.5 397B A17B', 'openrouter', 'qwen/qwen3.5-397b-a17b', 'Qwen3.5 397B MoE flagship — 17B active params, 262K native context, 201 languages, multimodal', 0.700000, 2.800000, 262144, 8192, TRUE, 'premium'),
    ('qwen3.5-plus', 'Qwen3.5 Plus', 'openrouter', 'qwen/qwen3.5-plus', 'Qwen3.5 Plus — Alibaba Cloud hosted flagship, hybrid GDN + MoE, multimodal', 0.800000, 3.200000, 262144, 8192, TRUE, 'premium')
)
INSERT INTO product.products (
    product_id,
    product_name,
    product_code,
    description,
    category,
    product_type,
    base_price,
    currency,
    billing_interval,
    features,
    quota_limits,
    is_active,
    metadata,
    product_kind,
    fulfillment_type,
    inventory_policy,
    requires_shipping,
    tax_category
)
SELECT
    sm.product_id,
    sm.product_name,
    upper(left(trim(BOTH '_' FROM regexp_replace(sm.product_id, '[^a-zA-Z0-9]+', '_', 'g')), 60)),
    sm.description,
    'ai_models',
    'model_inference',
    round((sm.input_cost_per_1m / 1000.0)::numeric, 8),
    'USD',
    'per_token',
    to_jsonb(
        ARRAY_REMOVE(
            ARRAY[
                sm.provider,
                sm.performance_tier,
                CASE WHEN sm.supports_vision THEN 'vision' ELSE 'text_generation' END,
                'configured_catalog'
            ],
            NULL
        )
    ),
    jsonb_build_object(
        'max_tokens',
        sm.context_window,
        'max_output_tokens',
        sm.max_output_tokens
    ),
    TRUE,
    jsonb_build_object(
        'provider',
        sm.provider,
        'model',
        sm.product_id,
        'transport_model',
        sm.transport_model,
        'input_cost_per_1k',
        round((sm.input_cost_per_1m / 1000.0)::numeric, 8),
        'output_cost_per_1k',
        round((sm.output_cost_per_1m / 1000.0)::numeric, 8),
        'pricing_source',
        'isa_model_provider_config_2026_04_09',
        'billing_profile',
        jsonb_build_object(
            'billing_surface',
            'abstract_service',
            'invoiceable',
            TRUE,
            'primary_meter',
            'tokens',
            'cost_components',
            jsonb_build_array(
                jsonb_build_object(
                    'component_id',
                    'model_provider_tokens',
                    'component_type',
                    'token_compute',
                    'bundled',
                    TRUE,
                    'customer_visible',
                    FALSE,
                    'provider',
                    sm.provider,
                    'meter_type',
                    'tokens',
                    'unit_type',
                    'token'
                )
            )
        )
    ),
    'digital',
    'digital',
    'infinite',
    FALSE,
    'digital_goods'
FROM seeded_models sm
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

WITH seeded_models (
    product_id,
    product_name,
    provider,
    transport_model,
    description,
    input_cost_per_1m,
    output_cost_per_1m,
    context_window,
    max_output_tokens,
    supports_vision,
    performance_tier
) AS (
    VALUES
    ('claude-3-opus', 'Claude 3 Opus', 'openrouter', 'anthropic/claude-3-opus', 'Anthropic''s most powerful model for complex tasks', 15.000000, 75.000000, 200000, 4096, TRUE, 'premium'),
    ('claude-3.5-sonnet', 'Claude 3.5 Sonnet', 'openrouter', 'anthropic/claude-3.5-sonnet', 'Anthropic''s Claude 3.5 Sonnet - excellent balance of intelligence and speed', 3.000000, 15.000000, 200000, 8192, TRUE, 'premium'),
    ('deepseek-chat-v3-0324', 'DeepSeek Chat V3 0324', 'openrouter', 'deepseek/deepseek-chat-v3-0324', 'DeepSeek Chat V3 - fast and capable chat model', 0.140000, 0.280000, 64000, 8192, FALSE, 'standard'),
    ('deepseek-r1', 'DeepSeek R1', 'openrouter', 'deepseek/deepseek-r1', 'DeepSeek R1 - advanced reasoning model with chain-of-thought', 0.550000, 2.190000, 64000, 8192, FALSE, 'premium'),
    ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash Experimental', 'openrouter', 'google/gemini-2.0-flash-exp', 'Google''s fast experimental Gemini 2.0 model', 0.000000, 0.000000, 1000000, 8192, TRUE, 'standard'),
    ('gemini-pro-1.5', 'Gemini Pro 1.5', 'openrouter', 'google/gemini-pro-1.5', 'Google''s Gemini Pro 1.5 with massive context window', 1.250000, 5.000000, 2000000, 8192, TRUE, 'premium'),
    ('glm-5', 'GLM-5', 'openrouter', 'zhipu/glm-5', 'GLM-5 744B MoE — 40B active params, frontier model on SWE-bench/AIME, 200K context', 1.000000, 3.200000, 200000, 16384, FALSE, 'premium'),
    ('glm-5-turbo', 'GLM-5 Turbo', 'openrouter', 'zhipu/glm-5-turbo', 'GLM-5 Turbo — optimized for high-throughput agentic workloads, multi-step tool chains', 0.500000, 1.600000, 200000, 16384, FALSE, 'high'),
    ('glm-5.1', 'GLM-5.1', 'openrouter', 'zhipu/glm-5.1', 'GLM-5.1 — latest Zhipu model, 94.6% of Claude Opus 4.6 coding perf, open-weights', 1.000000, 3.200000, 200000, 16384, FALSE, 'premium'),
    ('gpt-oss-120b', 'GPT OSS 120B', 'cerebras', 'gpt-oss-120b', 'OpenAI GPT OSS 120B - Ultra-fast inference at ~3000 tokens/sec. Best performance-to-speed ratio.', 1.000000, 1.000000, 8192, 8192, FALSE, 'premium'),
    ('llama-3.1-sonar-large-128k-online', 'Llama 3.1 Sonar Large 128K Online', 'openrouter', 'perplexity/llama-3.1-sonar-large-128k-online', 'Perplexity''s online model with real-time web search', 1.000000, 1.000000, 128000, 8192, FALSE, 'premium'),
    ('llama-3.3-70b', 'Llama 3.3 70B', 'cerebras', 'llama-3.3-70b', 'Llama 3.3 70B - Powerful reasoning at ~2100 tokens/sec. Excellent for complex tasks.', 0.600000, 0.600000, 8192, 8192, FALSE, 'premium'),
    ('llama-3.3-70b-instruct', 'Llama 3.3 70B Instruct', 'openrouter', 'meta-llama/llama-3.3-70b-instruct', 'Meta''s Llama 3.3 70B - powerful open-source model', 0.400000, 0.400000, 128000, 8192, FALSE, 'high'),
    ('llama-4-scout-17b-16e-instruct', 'Llama 4 Scout 17B 16E Instruct', 'cerebras', 'llama-4-scout-17b-16e-instruct', 'Llama 4 Scout 109B - High-performance instruction following at ~2600 tokens/sec.', 0.800000, 0.800000, 8192, 8192, FALSE, 'premium'),
    ('llama3.1-8b', 'Llama 3.1 8B', 'cerebras', 'llama3.1-8b', 'Llama 3.1 8B - Fast and efficient at ~2200 tokens/sec. Cost-effective for general tasks.', 0.100000, 0.100000, 8192, 8192, FALSE, 'standard'),
    ('mistral-large', 'Mistral Large', 'openrouter', 'mistralai/mistral-large', 'Mistral''s flagship large model', 2.000000, 6.000000, 128000, 8192, FALSE, 'premium'),
    ('mixtral-8x22b-instruct', 'Mixtral 8x22B Instruct', 'openrouter', 'mistralai/mixtral-8x22b-instruct', 'Mistral''s Mixture of Experts model - excellent price/performance', 0.900000, 0.900000, 64000, 8192, FALSE, 'high'),
    ('o4-mini', 'o4-mini', 'openai', 'o4-mini', 'OpenAI''s o4-mini reasoning model optimized for fast, cost-efficient reasoning with exceptional performance in math, coding, and visual tasks.', 1.100000, 4.400000, 200000, 100000, TRUE, 'premium'),
    ('o4-mini-deep-search', 'o4-mini Deep Search', 'openai', 'o4-mini-deep-search', 'OpenAI''s o4-mini deep research model for comprehensive research tasks with web search capabilities and in-depth analysis.', 2.000000, 8.000000, 200000, 100000, TRUE, 'premium'),
    ('qwen-2.5-72b-instruct', 'Qwen 2.5 72B Instruct', 'openrouter', 'qwen/qwen-2.5-72b-instruct', 'Alibaba''s Qwen 2.5 72B - strong multilingual capabilities', 0.400000, 0.400000, 128000, 8192, FALSE, 'high'),
    ('qwen-3-32b', 'Qwen 3 32B', 'cerebras', 'qwen-3-32b', 'Qwen 3 32B - Balanced performance at ~2600 tokens/sec. Good for various tasks.', 0.400000, 0.400000, 32768, 8192, FALSE, 'standard'),
    ('qwen3.5-122b-a10b', 'Qwen3.5 122B A10B', 'openrouter', 'qwen/qwen3.5-122b-a10b', 'Qwen3.5 122B MoE — 10B active params, strong balance of speed and quality, multimodal', 0.350000, 1.400000, 262144, 8192, TRUE, 'high'),
    ('qwen3.5-27b', 'Qwen3.5 27B', 'openrouter', 'qwen/qwen3.5-27b', 'Qwen3.5 27B Dense — fast dense model with linear attention, strong vision-language', 0.200000, 0.800000, 262144, 8192, TRUE, 'standard'),
    ('qwen3.5-35b-a3b', 'Qwen3.5 35B A3B', 'openrouter', 'qwen/qwen3.5-35b-a3b', 'Qwen3.5 35B MoE — 3B active params, ultra-efficient for coding and chat, multimodal', 0.140000, 0.560000, 262144, 8192, TRUE, 'standard'),
    ('qwen3.5-397b-a17b', 'Qwen3.5 397B A17B', 'openrouter', 'qwen/qwen3.5-397b-a17b', 'Qwen3.5 397B MoE flagship — 17B active params, 262K native context, 201 languages, multimodal', 0.700000, 2.800000, 262144, 8192, TRUE, 'premium'),
    ('qwen3.5-plus', 'Qwen3.5 Plus', 'openrouter', 'qwen/qwen3.5-plus', 'Qwen3.5 Plus — Alibaba Cloud hosted flagship, hybrid GDN + MoE, multimodal', 0.800000, 3.200000, 262144, 8192, TRUE, 'premium')
)
INSERT INTO product.product_pricing (
    pricing_id,
    product_id,
    tier_name,
    min_quantity,
    max_quantity,
    unit_price,
    currency,
    metadata
)
SELECT
    format(
        'pricing_%s_%s',
        trim(BOTH '_' FROM regexp_replace(lower(sm.product_id), '[^a-z0-9]+', '_', 'g')),
        price_tier.tier_name
    ),
    sm.product_id,
    price_tier.tier_name,
    0,
    NULL,
    round((price_tier.cost_per_1m / 1000000.0)::numeric, 8),
    'USD',
    jsonb_build_object(
        'unit',
        'token',
        format('%s_cost_per_1k', price_tier.tier_name),
        round((price_tier.cost_per_1m / 1000.0)::numeric, 8),
        'credits_per_1k',
        round(price_tier.cost_per_1m * 0.13),
        'billing_type',
        'usage_based'
    )
FROM seeded_models sm
CROSS JOIN LATERAL (
    VALUES
        ('input', sm.input_cost_per_1m),
        ('output', sm.output_cost_per_1m)
) AS price_tier(tier_name, cost_per_1m)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

WITH seeded_models (
    product_id,
    product_name,
    provider,
    transport_model,
    description,
    input_cost_per_1m,
    output_cost_per_1m,
    context_window,
    max_output_tokens,
    supports_vision,
    performance_tier
) AS (
    VALUES
    ('claude-3-opus', 'Claude 3 Opus', 'openrouter', 'anthropic/claude-3-opus', 'Anthropic''s most powerful model for complex tasks', 15.000000, 75.000000, 200000, 4096, TRUE, 'premium'),
    ('claude-3.5-sonnet', 'Claude 3.5 Sonnet', 'openrouter', 'anthropic/claude-3.5-sonnet', 'Anthropic''s Claude 3.5 Sonnet - excellent balance of intelligence and speed', 3.000000, 15.000000, 200000, 8192, TRUE, 'premium'),
    ('deepseek-chat-v3-0324', 'DeepSeek Chat V3 0324', 'openrouter', 'deepseek/deepseek-chat-v3-0324', 'DeepSeek Chat V3 - fast and capable chat model', 0.140000, 0.280000, 64000, 8192, FALSE, 'standard'),
    ('deepseek-r1', 'DeepSeek R1', 'openrouter', 'deepseek/deepseek-r1', 'DeepSeek R1 - advanced reasoning model with chain-of-thought', 0.550000, 2.190000, 64000, 8192, FALSE, 'premium'),
    ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash Experimental', 'openrouter', 'google/gemini-2.0-flash-exp', 'Google''s fast experimental Gemini 2.0 model', 0.000000, 0.000000, 1000000, 8192, TRUE, 'standard'),
    ('gemini-pro-1.5', 'Gemini Pro 1.5', 'openrouter', 'google/gemini-pro-1.5', 'Google''s Gemini Pro 1.5 with massive context window', 1.250000, 5.000000, 2000000, 8192, TRUE, 'premium'),
    ('glm-5', 'GLM-5', 'openrouter', 'zhipu/glm-5', 'GLM-5 744B MoE — 40B active params, frontier model on SWE-bench/AIME, 200K context', 1.000000, 3.200000, 200000, 16384, FALSE, 'premium'),
    ('glm-5-turbo', 'GLM-5 Turbo', 'openrouter', 'zhipu/glm-5-turbo', 'GLM-5 Turbo — optimized for high-throughput agentic workloads, multi-step tool chains', 0.500000, 1.600000, 200000, 16384, FALSE, 'high'),
    ('glm-5.1', 'GLM-5.1', 'openrouter', 'zhipu/glm-5.1', 'GLM-5.1 — latest Zhipu model, 94.6% of Claude Opus 4.6 coding perf, open-weights', 1.000000, 3.200000, 200000, 16384, FALSE, 'premium'),
    ('gpt-oss-120b', 'GPT OSS 120B', 'cerebras', 'gpt-oss-120b', 'OpenAI GPT OSS 120B - Ultra-fast inference at ~3000 tokens/sec. Best performance-to-speed ratio.', 1.000000, 1.000000, 8192, 8192, FALSE, 'premium'),
    ('llama-3.1-sonar-large-128k-online', 'Llama 3.1 Sonar Large 128K Online', 'openrouter', 'perplexity/llama-3.1-sonar-large-128k-online', 'Perplexity''s online model with real-time web search', 1.000000, 1.000000, 128000, 8192, FALSE, 'premium'),
    ('llama-3.3-70b', 'Llama 3.3 70B', 'cerebras', 'llama-3.3-70b', 'Llama 3.3 70B - Powerful reasoning at ~2100 tokens/sec. Excellent for complex tasks.', 0.600000, 0.600000, 8192, 8192, FALSE, 'premium'),
    ('llama-3.3-70b-instruct', 'Llama 3.3 70B Instruct', 'openrouter', 'meta-llama/llama-3.3-70b-instruct', 'Meta''s Llama 3.3 70B - powerful open-source model', 0.400000, 0.400000, 128000, 8192, FALSE, 'high'),
    ('llama-4-scout-17b-16e-instruct', 'Llama 4 Scout 17B 16E Instruct', 'cerebras', 'llama-4-scout-17b-16e-instruct', 'Llama 4 Scout 109B - High-performance instruction following at ~2600 tokens/sec.', 0.800000, 0.800000, 8192, 8192, FALSE, 'premium'),
    ('llama3.1-8b', 'Llama 3.1 8B', 'cerebras', 'llama3.1-8b', 'Llama 3.1 8B - Fast and efficient at ~2200 tokens/sec. Cost-effective for general tasks.', 0.100000, 0.100000, 8192, 8192, FALSE, 'standard'),
    ('mistral-large', 'Mistral Large', 'openrouter', 'mistralai/mistral-large', 'Mistral''s flagship large model', 2.000000, 6.000000, 128000, 8192, FALSE, 'premium'),
    ('mixtral-8x22b-instruct', 'Mixtral 8x22B Instruct', 'openrouter', 'mistralai/mixtral-8x22b-instruct', 'Mistral''s Mixture of Experts model - excellent price/performance', 0.900000, 0.900000, 64000, 8192, FALSE, 'high'),
    ('o4-mini', 'o4-mini', 'openai', 'o4-mini', 'OpenAI''s o4-mini reasoning model optimized for fast, cost-efficient reasoning with exceptional performance in math, coding, and visual tasks.', 1.100000, 4.400000, 200000, 100000, TRUE, 'premium'),
    ('o4-mini-deep-search', 'o4-mini Deep Search', 'openai', 'o4-mini-deep-search', 'OpenAI''s o4-mini deep research model for comprehensive research tasks with web search capabilities and in-depth analysis.', 2.000000, 8.000000, 200000, 100000, TRUE, 'premium'),
    ('qwen-2.5-72b-instruct', 'Qwen 2.5 72B Instruct', 'openrouter', 'qwen/qwen-2.5-72b-instruct', 'Alibaba''s Qwen 2.5 72B - strong multilingual capabilities', 0.400000, 0.400000, 128000, 8192, FALSE, 'high'),
    ('qwen-3-32b', 'Qwen 3 32B', 'cerebras', 'qwen-3-32b', 'Qwen 3 32B - Balanced performance at ~2600 tokens/sec. Good for various tasks.', 0.400000, 0.400000, 32768, 8192, FALSE, 'standard'),
    ('qwen3.5-122b-a10b', 'Qwen3.5 122B A10B', 'openrouter', 'qwen/qwen3.5-122b-a10b', 'Qwen3.5 122B MoE — 10B active params, strong balance of speed and quality, multimodal', 0.350000, 1.400000, 262144, 8192, TRUE, 'high'),
    ('qwen3.5-27b', 'Qwen3.5 27B', 'openrouter', 'qwen/qwen3.5-27b', 'Qwen3.5 27B Dense — fast dense model with linear attention, strong vision-language', 0.200000, 0.800000, 262144, 8192, TRUE, 'standard'),
    ('qwen3.5-35b-a3b', 'Qwen3.5 35B A3B', 'openrouter', 'qwen/qwen3.5-35b-a3b', 'Qwen3.5 35B MoE — 3B active params, ultra-efficient for coding and chat, multimodal', 0.140000, 0.560000, 262144, 8192, TRUE, 'standard'),
    ('qwen3.5-397b-a17b', 'Qwen3.5 397B A17B', 'openrouter', 'qwen/qwen3.5-397b-a17b', 'Qwen3.5 397B MoE flagship — 17B active params, 262K native context, 201 languages, multimodal', 0.700000, 2.800000, 262144, 8192, TRUE, 'premium'),
    ('qwen3.5-plus', 'Qwen3.5 Plus', 'openrouter', 'qwen/qwen3.5-plus', 'Qwen3.5 Plus — Alibaba Cloud hosted flagship, hybrid GDN + MoE, multimodal', 0.800000, 3.200000, 262144, 8192, TRUE, 'premium')
)
INSERT INTO product.cost_definitions (
    cost_id,
    product_id,
    service_type,
    provider,
    model_name,
    operation_type,
    cost_per_unit,
    unit_type,
    unit_size,
    original_cost_usd,
    margin_percentage,
    effective_from,
    effective_until,
    free_tier_limit,
    free_tier_period,
    is_active,
    description,
    metadata,
    created_at,
    updated_at
)
SELECT
    format(
        'cost_%s_%s',
        trim(BOTH '_' FROM regexp_replace(lower(sm.product_id), '[^a-z0-9]+', '_', 'g')),
        price_tier.operation_type
    ),
    sm.product_id,
    'model_inference',
    sm.provider,
    sm.transport_model,
    price_tier.operation_type,
    round(price_tier.cost_per_1m * 0.13),
    'token',
    1000,
    round((price_tier.cost_per_1m / 1000.0)::numeric, 8),
    30.0,
    NOW(),
    NULL,
    0,
    'monthly',
    TRUE,
    format(
        'Configured %s %s pricing',
        sm.product_name,
        price_tier.operation_type
    ),
    jsonb_build_object(
        'pricing_source',
        'isa_model_provider_config_2026_04_09',
        'transport_model',
        sm.transport_model,
        'performance_tier',
        sm.performance_tier
    ),
    NOW(),
    NOW()
FROM seeded_models sm
CROSS JOIN LATERAL (
    VALUES
        ('input', sm.input_cost_per_1m),
        ('output', sm.output_cost_per_1m)
) AS price_tier(operation_type, cost_per_1m)
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
    effective_until = EXCLUDED.effective_until,
    free_tier_limit = EXCLUDED.free_tier_limit,
    free_tier_period = EXCLUDED.free_tier_period,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
