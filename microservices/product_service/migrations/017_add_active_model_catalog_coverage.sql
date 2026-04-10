-- Product Service Migration: add active model catalog coverage for emitted inference SKUs
-- Version: 017
-- Date: 2026-04-09
-- Description: seeds the model SKUs currently emitted by isA_Model but still
--              missing from product_service, and backfills billing profiles on
--              existing active model products that were created before the
--              abstract-service billing profile work.
--
-- Pricing sources verified on 2026-04-09:
-- - OpenAI API pricing: https://openai.com/api/pricing/
-- - Anthropic pricing: https://www.anthropic.com/pricing
-- - DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
-- - OpenRouter model pages for observed provider-qualified models:
--   https://openrouter.ai/mistralai/ministral-3b
--   https://openrouter.ai/nvidia/nemotron-3-nano-30b-a3b%3Afree

UPDATE product.products
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{billing_profile}',
    jsonb_build_object(
        'billing_surface', 'abstract_service',
        'invoiceable', true,
        'primary_meter', 'tokens',
        'cost_components', jsonb_build_array(
            jsonb_build_object(
                'component_id', 'model_provider_tokens',
                'component_type', 'token_compute',
                'bundled', true,
                'customer_visible', false,
                'provider', COALESCE(metadata->>'provider', 'external'),
                'meter_type', 'tokens',
                'unit_type', 'token',
                'notes', 'Provider-backed model inference token cost'
            )
        )
    ),
    true
),
updated_at = NOW()
WHERE product_type = 'model_inference'
  AND is_active = TRUE
  AND NOT (COALESCE(metadata, '{}'::jsonb) ? 'billing_profile');

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('gpt-4.1', 'GPT-4.1', 'GPT41',
 'OpenAI GPT-4.1 model inference',
 'ai_models', 'model_inference', 0.002, 'USD', 'per_token',
 '["reasoning", "coding", "multimodal"]'::jsonb,
 '{"max_tokens": 1047576}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4.1",
    "input_cost_per_1k": 0.002,
    "output_cost_per_1k": 0.008,
    "pricing_source": "openai_api_pricing_2026_04_09",
    "billing_profile": {
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
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-4.1-mini', 'GPT-4.1 Mini', 'GPT41-MINI',
 'OpenAI GPT-4.1 Mini model inference',
 'ai_models', 'model_inference', 0.0004, 'USD', 'per_token',
 '["fast_inference", "coding", "multimodal"]'::jsonb,
 '{"max_tokens": 1047576}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "input_cost_per_1k": 0.0004,
    "output_cost_per_1k": 0.0016,
    "pricing_source": "openai_api_pricing_2026_04_09",
    "billing_profile": {
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
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-4.1-nano', 'GPT-4.1 Nano', 'GPT41-NANO',
 'OpenAI GPT-4.1 Nano model inference',
 'ai_models', 'model_inference', 0.0001, 'USD', 'per_token',
 '["fast_inference", "low_cost", "multimodal"]'::jsonb,
 '{"max_tokens": 1047576}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4.1-nano",
    "input_cost_per_1k": 0.0001,
    "output_cost_per_1k": 0.0004,
    "pricing_source": "openai_api_pricing_2026_04_09",
    "billing_profile": {
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
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-5.4', 'GPT-5.4', 'GPT54',
 'OpenAI GPT-5.4 model inference',
 'ai_models', 'model_inference', 0.0025, 'USD', 'per_token',
 '["reasoning", "coding", "high_quality"]'::jsonb,
 '{"max_tokens": 400000}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-5.4",
    "input_cost_per_1k": 0.0025,
    "output_cost_per_1k": 0.02,
    "pricing_source": "openai_api_pricing_2026_04_09",
    "billing_profile": {
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
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-5-mini', 'GPT-5 Mini', 'GPT5-MINI',
 'OpenAI GPT-5 Mini model inference',
 'ai_models', 'model_inference', 0.00025, 'USD', 'per_token',
 '["fast_inference", "reasoning", "vision"]'::jsonb,
 '{"max_tokens": 400000}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-5-mini",
    "canonical_model": "gpt-5.4-mini",
    "input_cost_per_1k": 0.00025,
    "output_cost_per_1k": 0.002,
    "pricing_source": "openai_api_pricing_2026_04_09",
    "billing_profile": {
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
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-5-nano', 'GPT-5 Nano', 'GPT5-NANO',
 'OpenAI GPT-5 Nano model inference',
 'ai_models', 'model_inference', 0.00005, 'USD', 'per_token',
 '["fast_inference", "low_cost", "vision"]'::jsonb,
 '{"max_tokens": 400000}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-5-nano",
    "canonical_model": "gpt-5.4-nano",
    "input_cost_per_1k": 0.00005,
    "output_cost_per_1k": 0.0004,
    "pricing_source": "openai_api_pricing_2026_04_09",
    "billing_profile": {
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
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-sonnet-4-6', 'Claude Sonnet 4.6', 'CLAUDE-SONNET46',
 'Anthropic Claude Sonnet 4.6 model inference',
 'ai_models', 'model_inference', 0.003, 'USD', 'per_token',
 '["reasoning", "coding", "analysis", "200k_context"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "input_cost_per_1k": 0.003,
    "output_cost_per_1k": 0.015,
    "pricing_source": "anthropic_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-opus-4-6', 'Claude Opus 4.6', 'CLAUDE-OPUS46',
 'Anthropic Claude Opus 4.6 model inference',
 'ai_models', 'model_inference', 0.005, 'USD', 'per_token',
 '["frontier_reasoning", "complex_analysis", "coding", "200k_context"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic",
    "model": "claude-opus-4-6",
    "input_cost_per_1k": 0.005,
    "output_cost_per_1k": 0.025,
    "pricing_source": "anthropic_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-haiku-4-5', 'Claude Haiku 4.5', 'CLAUDE-HAIKU45',
 'Anthropic Claude Haiku 4.5 model inference',
 'ai_models', 'model_inference', 0.001, 'USD', 'per_token',
 '["fast_inference", "low_cost", "coding", "200k_context"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic",
    "model": "claude-haiku-4-5",
    "input_cost_per_1k": 0.001,
    "output_cost_per_1k": 0.005,
    "pricing_source": "anthropic_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-sonnet-4-20250514', 'Claude Sonnet 4 (2025-05-14)', 'CLAUDE-SONNET4-20250514',
 'Anthropic Claude Sonnet 4 legacy pinned model inference',
 'ai_models', 'model_inference', 0.003, 'USD', 'per_token',
 '["reasoning", "coding", "analysis", "pinned_release"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "model_family": "claude-sonnet-4",
    "input_cost_per_1k": 0.003,
    "output_cost_per_1k": 0.015,
    "pricing_source": "anthropic_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-opus-4-20250514', 'Claude Opus 4 (2025-05-14)', 'CLAUDE-OPUS4-20250514',
 'Anthropic Claude Opus 4 legacy pinned model inference',
 'ai_models', 'model_inference', 0.015, 'USD', 'per_token',
 '["frontier_reasoning", "coding", "pinned_release"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic",
    "model": "claude-opus-4-20250514",
    "model_family": "claude-opus-4",
    "input_cost_per_1k": 0.015,
    "output_cost_per_1k": 0.075,
    "pricing_source": "anthropic_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('claude-haiku-4-20250506', 'Claude Haiku 4 (2025-05-06)', 'CLAUDE-HAIKU4-20250506',
 'Anthropic Claude Haiku legacy pinned model inference',
 'ai_models', 'model_inference', 0.001, 'USD', 'per_token',
 '["fast_inference", "low_cost", "pinned_release"]'::jsonb,
 '{"max_tokens": 200000}'::jsonb,
 TRUE,
 '{
    "provider": "anthropic",
    "model": "claude-haiku-4-20250506",
    "model_family": "claude-haiku-4",
    "input_cost_per_1k": 0.001,
    "output_cost_per_1k": 0.005,
    "pricing_source": "anthropic_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "anthropic",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('deepseek-reasoner', 'DeepSeek Reasoner', 'DEEPSEEK-REASONER',
 'DeepSeek Reasoner model inference',
 'ai_models', 'model_inference', 0.00055, 'USD', 'per_token',
 '["reasoning", "analysis", "cost_effective"]'::jsonb,
 '{"max_tokens": 64000}'::jsonb,
 TRUE,
 '{
    "provider": "deepseek",
    "model": "deepseek-reasoner",
    "input_cost_per_1k": 0.00055,
    "output_cost_per_1k": 0.00219,
    "pricing_source": "deepseek_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "deepseek",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('mistralai/ministral-3b-2512', 'Ministral 3B 2512', 'MINISTRAL-3B-2512',
 'OpenRouter-hosted Ministral 3B 2512 model inference',
 'ai_models', 'model_inference', 0.00004, 'USD', 'per_token',
 '["openrouter", "cost_effective", "general_reasoning"]'::jsonb,
 '{"max_tokens": 32768}'::jsonb,
 TRUE,
 '{
    "provider": "openrouter",
    "model": "mistralai/ministral-3b-2512",
    "input_cost_per_1k": 0.00004,
    "output_cost_per_1k": 0.00004,
    "pricing_source": "openrouter_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "openrouter",
          "meter_type": "tokens",
          "unit_type": "token"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('nvidia/nemotron-3-nano-30b-a3b:free', 'Nemotron 3 Nano 30B A3B Free', 'NEMOTRON-3-NANO-30B-A3B-FREE',
 'OpenRouter-hosted free Nemotron 3 Nano 30B A3B model inference',
 'ai_models', 'model_inference', 0.0, 'USD', 'per_token',
 '["openrouter", "free_tier", "general_reasoning"]'::jsonb,
 '{"max_tokens": 32768}'::jsonb,
 TRUE,
 '{
    "provider": "openrouter",
    "model": "nvidia/nemotron-3-nano-30b-a3b:free",
    "input_cost_per_1k": 0.0,
    "output_cost_per_1k": 0.0,
    "pricing_source": "openrouter_pricing_2026_04_09",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "model_provider_tokens",
          "component_type": "token_compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "openrouter",
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

INSERT INTO product.product_pricing (
    pricing_id, product_id, tier_name, min_quantity, max_quantity, unit_price, currency, metadata
) VALUES
('pricing_gpt41_input', 'gpt-4.1', 'input', 0, NULL, 0.00000200, 'USD', '{"unit": "token", "input_cost_per_1k": 0.002, "credits_per_1k": 260, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt41_output', 'gpt-4.1', 'output', 0, NULL, 0.00000800, 'USD', '{"unit": "token", "output_cost_per_1k": 0.008, "credits_per_1k": 1040, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt41_mini_input', 'gpt-4.1-mini', 'input', 0, NULL, 0.00000040, 'USD', '{"unit": "token", "input_cost_per_1k": 0.0004, "credits_per_1k": 52, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt41_mini_output', 'gpt-4.1-mini', 'output', 0, NULL, 0.00000160, 'USD', '{"unit": "token", "output_cost_per_1k": 0.0016, "credits_per_1k": 208, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt41_nano_input', 'gpt-4.1-nano', 'input', 0, NULL, 0.00000010, 'USD', '{"unit": "token", "input_cost_per_1k": 0.0001, "credits_per_1k": 13, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt41_nano_output', 'gpt-4.1-nano', 'output', 0, NULL, 0.00000040, 'USD', '{"unit": "token", "output_cost_per_1k": 0.0004, "credits_per_1k": 52, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt54_input', 'gpt-5.4', 'input', 0, NULL, 0.00000250, 'USD', '{"unit": "token", "input_cost_per_1k": 0.0025, "credits_per_1k": 325, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt54_output', 'gpt-5.4', 'output', 0, NULL, 0.00002000, 'USD', '{"unit": "token", "output_cost_per_1k": 0.02, "credits_per_1k": 2600, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt5_mini_input', 'gpt-5-mini', 'input', 0, NULL, 0.00000025, 'USD', '{"unit": "token", "input_cost_per_1k": 0.00025, "credits_per_1k": 33, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt5_mini_output', 'gpt-5-mini', 'output', 0, NULL, 0.00000200, 'USD', '{"unit": "token", "output_cost_per_1k": 0.002, "credits_per_1k": 260, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt5_nano_input', 'gpt-5-nano', 'input', 0, NULL, 0.00000005, 'USD', '{"unit": "token", "input_cost_per_1k": 0.00005, "credits_per_1k": 7, "billing_type": "usage_based"}'::jsonb),
('pricing_gpt5_nano_output', 'gpt-5-nano', 'output', 0, NULL, 0.00000040, 'USD', '{"unit": "token", "output_cost_per_1k": 0.0004, "credits_per_1k": 52, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_sonnet46_input', 'claude-sonnet-4-6', 'input', 0, NULL, 0.00000300, 'USD', '{"unit": "token", "input_cost_per_1k": 0.003, "credits_per_1k": 390, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_sonnet46_output', 'claude-sonnet-4-6', 'output', 0, NULL, 0.00001500, 'USD', '{"unit": "token", "output_cost_per_1k": 0.015, "credits_per_1k": 1950, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_opus46_input', 'claude-opus-4-6', 'input', 0, NULL, 0.00000500, 'USD', '{"unit": "token", "input_cost_per_1k": 0.005, "credits_per_1k": 650, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_opus46_output', 'claude-opus-4-6', 'output', 0, NULL, 0.00002500, 'USD', '{"unit": "token", "output_cost_per_1k": 0.025, "credits_per_1k": 3250, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_haiku45_input', 'claude-haiku-4-5', 'input', 0, NULL, 0.00000100, 'USD', '{"unit": "token", "input_cost_per_1k": 0.001, "credits_per_1k": 130, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_haiku45_output', 'claude-haiku-4-5', 'output', 0, NULL, 0.00000500, 'USD', '{"unit": "token", "output_cost_per_1k": 0.005, "credits_per_1k": 650, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_sonnet4_20250514_input', 'claude-sonnet-4-20250514', 'input', 0, NULL, 0.00000300, 'USD', '{"unit": "token", "input_cost_per_1k": 0.003, "credits_per_1k": 390, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_sonnet4_20250514_output', 'claude-sonnet-4-20250514', 'output', 0, NULL, 0.00001500, 'USD', '{"unit": "token", "output_cost_per_1k": 0.015, "credits_per_1k": 1950, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_opus4_20250514_input', 'claude-opus-4-20250514', 'input', 0, NULL, 0.00001500, 'USD', '{"unit": "token", "input_cost_per_1k": 0.015, "credits_per_1k": 1950, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_opus4_20250514_output', 'claude-opus-4-20250514', 'output', 0, NULL, 0.00007500, 'USD', '{"unit": "token", "output_cost_per_1k": 0.075, "credits_per_1k": 9750, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_haiku4_20250506_input', 'claude-haiku-4-20250506', 'input', 0, NULL, 0.00000100, 'USD', '{"unit": "token", "input_cost_per_1k": 0.001, "credits_per_1k": 130, "billing_type": "usage_based"}'::jsonb),
('pricing_claude_haiku4_20250506_output', 'claude-haiku-4-20250506', 'output', 0, NULL, 0.00000500, 'USD', '{"unit": "token", "output_cost_per_1k": 0.005, "credits_per_1k": 650, "billing_type": "usage_based"}'::jsonb),
('pricing_deepseek_reasoner_input', 'deepseek-reasoner', 'input', 0, NULL, 0.00000055, 'USD', '{"unit": "token", "input_cost_per_1k": 0.00055, "credits_per_1k": 72, "billing_type": "usage_based"}'::jsonb),
('pricing_deepseek_reasoner_output', 'deepseek-reasoner', 'output', 0, NULL, 0.00000219, 'USD', '{"unit": "token", "output_cost_per_1k": 0.00219, "credits_per_1k": 285, "billing_type": "usage_based"}'::jsonb),
('pricing_ministral_3b_2512_input', 'mistralai/ministral-3b-2512', 'input', 0, NULL, 0.00000004, 'USD', '{"unit": "token", "input_cost_per_1k": 0.00004, "credits_per_1k": 5, "billing_type": "usage_based"}'::jsonb),
('pricing_ministral_3b_2512_output', 'mistralai/ministral-3b-2512', 'output', 0, NULL, 0.00000004, 'USD', '{"unit": "token", "output_cost_per_1k": 0.00004, "credits_per_1k": 5, "billing_type": "usage_based"}'::jsonb),
('pricing_nemotron_3_nano_30b_a3b_free_input', 'nvidia/nemotron-3-nano-30b-a3b:free', 'input', 0, NULL, 0.0, 'USD', '{"unit": "token", "input_cost_per_1k": 0.0, "credits_per_1k": 0, "billing_type": "usage_based"}'::jsonb),
('pricing_nemotron_3_nano_30b_a3b_free_output', 'nvidia/nemotron-3-nano-30b-a3b:free', 'output', 0, NULL, 0.0, 'USD', '{"unit": "token", "output_cost_per_1k": 0.0, "credits_per_1k": 0, "billing_type": "usage_based"}'::jsonb)
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
    effective_from, effective_until, free_tier_limit, free_tier_period,
    is_active, description, metadata, created_at, updated_at
) VALUES
('cost_gpt41_input', 'gpt-4.1', 'model_inference', 'openai', 'gpt-4.1', 'input', 260, 'token', 1000, 0.002, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-4.1 input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt41_output', 'gpt-4.1', 'model_inference', 'openai', 'gpt-4.1', 'output', 1040, 'token', 1000, 0.008, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-4.1 output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt41_mini_input', 'gpt-4.1-mini', 'model_inference', 'openai', 'gpt-4.1-mini', 'input', 52, 'token', 1000, 0.0004, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-4.1 Mini input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt41_mini_output', 'gpt-4.1-mini', 'model_inference', 'openai', 'gpt-4.1-mini', 'output', 208, 'token', 1000, 0.0016, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-4.1 Mini output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt41_nano_input', 'gpt-4.1-nano', 'model_inference', 'openai', 'gpt-4.1-nano', 'input', 13, 'token', 1000, 0.0001, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-4.1 Nano input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt41_nano_output', 'gpt-4.1-nano', 'model_inference', 'openai', 'gpt-4.1-nano', 'output', 52, 'token', 1000, 0.0004, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-4.1 Nano output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt54_input', 'gpt-5.4', 'model_inference', 'openai', 'gpt-5.4', 'input', 325, 'token', 1000, 0.0025, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-5.4 input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt54_output', 'gpt-5.4', 'model_inference', 'openai', 'gpt-5.4', 'output', 2600, 'token', 1000, 0.02, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-5.4 output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt5_mini_input', 'gpt-5-mini', 'model_inference', 'openai', 'gpt-5-mini', 'input', 33, 'token', 1000, 0.00025, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-5 Mini input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt5_mini_output', 'gpt-5-mini', 'model_inference', 'openai', 'gpt-5-mini', 'output', 260, 'token', 1000, 0.002, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-5 Mini output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt5_nano_input', 'gpt-5-nano', 'model_inference', 'openai', 'gpt-5-nano', 'input', 7, 'token', 1000, 0.00005, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-5 Nano input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_gpt5_nano_output', 'gpt-5-nano', 'model_inference', 'openai', 'gpt-5-nano', 'output', 52, 'token', 1000, 0.0004, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenAI GPT-5 Nano output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_sonnet46_input', 'claude-sonnet-4-6', 'model_inference', 'anthropic', 'claude-sonnet-4-6', 'input', 390, 'token', 1000, 0.003, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Sonnet 4.6 input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_sonnet46_output', 'claude-sonnet-4-6', 'model_inference', 'anthropic', 'claude-sonnet-4-6', 'output', 1950, 'token', 1000, 0.015, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Sonnet 4.6 output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_opus46_input', 'claude-opus-4-6', 'model_inference', 'anthropic', 'claude-opus-4-6', 'input', 650, 'token', 1000, 0.005, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Opus 4.6 input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_opus46_output', 'claude-opus-4-6', 'model_inference', 'anthropic', 'claude-opus-4-6', 'output', 3250, 'token', 1000, 0.025, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Opus 4.6 output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_haiku45_input', 'claude-haiku-4-5', 'model_inference', 'anthropic', 'claude-haiku-4-5', 'input', 130, 'token', 1000, 0.001, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Haiku 4.5 input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_haiku45_output', 'claude-haiku-4-5', 'model_inference', 'anthropic', 'claude-haiku-4-5', 'output', 650, 'token', 1000, 0.005, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Haiku 4.5 output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_sonnet4_20250514_input', 'claude-sonnet-4-20250514', 'model_inference', 'anthropic', 'claude-sonnet-4-20250514', 'input', 390, 'token', 1000, 0.003, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Sonnet 4 legacy input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_sonnet4_20250514_output', 'claude-sonnet-4-20250514', 'model_inference', 'anthropic', 'claude-sonnet-4-20250514', 'output', 1950, 'token', 1000, 0.015, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Sonnet 4 legacy output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_opus4_20250514_input', 'claude-opus-4-20250514', 'model_inference', 'anthropic', 'claude-opus-4-20250514', 'input', 1950, 'token', 1000, 0.015, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Opus 4 legacy input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_opus4_20250514_output', 'claude-opus-4-20250514', 'model_inference', 'anthropic', 'claude-opus-4-20250514', 'output', 9750, 'token', 1000, 0.075, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Opus 4 legacy output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_haiku4_20250506_input', 'claude-haiku-4-20250506', 'model_inference', 'anthropic', 'claude-haiku-4-20250506', 'input', 130, 'token', 1000, 0.001, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Haiku legacy input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_claude_haiku4_20250506_output', 'claude-haiku-4-20250506', 'model_inference', 'anthropic', 'claude-haiku-4-20250506', 'output', 650, 'token', 1000, 0.005, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'Anthropic Claude Haiku legacy output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_deepseek_reasoner_input', 'deepseek-reasoner', 'model_inference', 'deepseek', 'deepseek-reasoner', 'input', 72, 'token', 1000, 0.00055, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'DeepSeek Reasoner input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_deepseek_reasoner_output', 'deepseek-reasoner', 'model_inference', 'deepseek', 'deepseek-reasoner', 'output', 285, 'token', 1000, 0.00219, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'DeepSeek Reasoner output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_ministral_3b_2512_input', 'mistralai/ministral-3b-2512', 'model_inference', 'openrouter', 'mistralai/ministral-3b-2512', 'input', 5, 'token', 1000, 0.00004, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenRouter Ministral 3B 2512 input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_ministral_3b_2512_output', 'mistralai/ministral-3b-2512', 'model_inference', 'openrouter', 'mistralai/ministral-3b-2512', 'output', 5, 'token', 1000, 0.00004, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenRouter Ministral 3B 2512 output pricing', '{}'::jsonb, NOW(), NOW()),
('cost_nemotron_3_nano_30b_a3b_free_input', 'nvidia/nemotron-3-nano-30b-a3b:free', 'model_inference', 'openrouter', 'nvidia/nemotron-3-nano-30b-a3b:free', 'input', 0, 'token', 1000, 0.0, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenRouter Nemotron 3 Nano 30B A3B free input pricing', '{}'::jsonb, NOW(), NOW()),
('cost_nemotron_3_nano_30b_a3b_free_output', 'nvidia/nemotron-3-nano-30b-a3b:free', 'model_inference', 'openrouter', 'nvidia/nemotron-3-nano-30b-a3b:free', 'output', 0, 'token', 1000, 0.0, 30.0, NOW(), NULL, 0, 'monthly', TRUE, 'OpenRouter Nemotron 3 Nano 30B A3B free output pricing', '{}'::jsonb, NOW(), NOW())
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
