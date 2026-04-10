-- Product Service Migration: add embedding, audio, image, and video model SKUs
-- Version: 016
-- Date: 2026-04-09
-- Description: seeds explicit catalog and cost-definition coverage for the
--              customer-facing OpenAI media models emitted by isA_Model.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('text-embedding-3-small', 'Text Embedding 3 Small', 'TEXT-EMBED-3-SMALL',
 'OpenAI text-embedding-3-small embedding inference',
 'ai_models', 'model_inference', 0.00000002, 'USD', 'per_token',
 '["embedding", "retrieval", "semantic_search"]'::jsonb,
 '{"max_tokens": 8192}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "text-embedding-3-small",
    "input_cost_per_1k": 0.00002,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "embedding_provider_tokens",
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

('text-embedding-3-large', 'Text Embedding 3 Large', 'TEXT-EMBED-3-LARGE',
 'OpenAI text-embedding-3-large embedding inference',
 'ai_models', 'model_inference', 0.00000013, 'USD', 'per_token',
 '["embedding", "retrieval", "higher_accuracy"]'::jsonb,
 '{"max_tokens": 8192}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "text-embedding-3-large",
    "input_cost_per_1k": 0.00013,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "embedding_provider_tokens",
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

('whisper-1', 'Whisper 1', 'WHISPER-1',
 'OpenAI Whisper speech-to-text transcription',
 'ai_models', 'model_inference', 0.006, 'USD', 'per_minute',
 '["speech_to_text", "transcription"]'::jsonb,
 '{"free_tier_minutes": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "whisper-1",
    "list_price_per_minute": 0.006,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "audio_minutes",
      "cost_components": [
        {
          "component_id": "transcription_provider_runtime",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "audio_minutes",
          "unit_type": "minute"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-4o-mini-transcribe', 'GPT-4o Mini Transcribe', 'GPT4O-MINI-TRANSCRIBE',
 'OpenAI GPT-4o Mini Transcribe speech-to-text model',
 'ai_models', 'model_inference', 0.003, 'USD', 'per_minute',
 '["speech_to_text", "transcription", "low_latency"]'::jsonb,
 '{"free_tier_minutes": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4o-mini-transcribe",
    "list_price_per_minute": 0.003,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "audio_minutes",
      "cost_components": [
        {
          "component_id": "transcription_provider_runtime",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "audio_minutes",
          "unit_type": "minute"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-4o-transcribe', 'GPT-4o Transcribe', 'GPT4O-TRANSCRIBE',
 'OpenAI GPT-4o Transcribe speech-to-text model',
 'ai_models', 'model_inference', 0.006, 'USD', 'per_minute',
 '["speech_to_text", "transcription", "higher_accuracy"]'::jsonb,
 '{"free_tier_minutes": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4o-transcribe",
    "list_price_per_minute": 0.006,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "audio_minutes",
      "cost_components": [
        {
          "component_id": "transcription_provider_runtime",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "audio_minutes",
          "unit_type": "minute"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-4o-transcribe-diarize', 'GPT-4o Transcribe Diarize', 'GPT4O-TRANSCRIBE-DIARIZE',
 'OpenAI GPT-4o Transcribe model with diarization',
 'ai_models', 'model_inference', 0.006, 'USD', 'per_minute',
 '["speech_to_text", "transcription", "diarization"]'::jsonb,
 '{"free_tier_minutes": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4o-transcribe-diarize",
    "list_price_per_minute": 0.006,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "audio_minutes",
      "cost_components": [
        {
          "component_id": "transcription_provider_runtime",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "audio_minutes",
          "unit_type": "minute"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('tts-1', 'TTS 1', 'TTS-1',
 'OpenAI legacy text-to-speech model',
 'ai_models', 'model_inference', 0.000015, 'USD', 'per_character',
 '["text_to_speech", "audio_generation"]'::jsonb,
 '{"free_tier_characters": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "tts-1",
    "list_price_per_1k_characters": 0.015,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "text_characters",
      "cost_components": [
        {
          "component_id": "tts_provider_runtime",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "text_characters",
          "unit_type": "character"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpt-4o-realtime-preview-2024-10-01', 'GPT-4o Realtime Preview', 'GPT4O-REALTIME-PREVIEW',
 'OpenAI GPT-4o realtime preview model used by the current audio runtime',
 'ai_models', 'model_inference', 0.000004, 'USD', 'per_token',
 '["realtime", "audio", "interactive"]'::jsonb,
 '{"max_tokens": 128000}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "gpt-4o-realtime-preview-2024-10-01",
    "input_cost_per_1k": 0.004,
    "output_cost_per_1k": 0.016,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "tokens",
      "cost_components": [
        {
          "component_id": "realtime_provider_tokens",
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

('dall-e-2', 'DALL·E 2', 'DALLE-2',
 'OpenAI DALL·E 2 image generation',
 'ai_models', 'model_inference', 0.020, 'USD', 'per_image',
 '["image_generation"]'::jsonb,
 '{"free_tier_images": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "dall-e-2",
    "list_price_per_image": 0.020,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "images",
      "cost_components": [
        {
          "component_id": "image_generation_provider",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "images",
          "unit_type": "image"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('dall-e-3', 'DALL·E 3', 'DALLE-3',
 'OpenAI DALL·E 3 image generation',
 'ai_models', 'model_inference', 0.040, 'USD', 'per_image',
 '["image_generation", "higher_quality"]'::jsonb,
 '{"free_tier_images": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "dall-e-3",
    "list_price_per_image": 0.040,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "images",
      "cost_components": [
        {
          "component_id": "image_generation_provider",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "images",
          "unit_type": "image"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('sora-2', 'Sora 2', 'SORA-2',
 'OpenAI Sora 2 video generation',
 'ai_models', 'model_inference', 0.10, 'USD', 'per_second',
 '["video_generation", "text_to_video", "image_to_video"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "sora-2",
    "list_price_per_second_720p": 0.10,
    "list_price_per_second_1080p": 0.30,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "video_seconds",
      "cost_components": [
        {
          "component_id": "video_generation_provider",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "video_seconds",
          "unit_type": "second"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('sora-2-pro', 'Sora 2 Pro', 'SORA-2-PRO',
 'OpenAI Sora 2 Pro video generation',
 'ai_models', 'model_inference', 0.30, 'USD', 'per_second',
 '["video_generation", "higher_quality"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "openai",
    "model": "sora-2-pro",
    "list_price_per_second_720p": 0.30,
    "list_price_per_second_1080p": 0.70,
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "video_seconds",
      "cost_components": [
        {
          "component_id": "video_generation_provider",
          "component_type": "external_api",
          "bundled": true,
          "customer_visible": false,
          "provider": "openai",
          "meter_type": "video_seconds",
          "unit_type": "second"
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
    currency = EXCLUDED.currency,
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
    min_quantity, max_quantity, unit_price, currency, metadata,
    created_at, updated_at
) VALUES
('pricing_text_embedding_3_small_base', 'text-embedding-3-small', 'base', 0, NULL, 0.00000002, 'USD', '{"unit": "token"}'::jsonb, NOW(), NOW()),
('pricing_text_embedding_3_large_base', 'text-embedding-3-large', 'base', 0, NULL, 0.00000013, 'USD', '{"unit": "token"}'::jsonb, NOW(), NOW()),
('pricing_whisper_1_base', 'whisper-1', 'base', 0, NULL, 0.006, 'USD', '{"unit": "minute"}'::jsonb, NOW(), NOW()),
('pricing_gpt4o_mini_transcribe_base', 'gpt-4o-mini-transcribe', 'base', 0, NULL, 0.003, 'USD', '{"unit": "minute"}'::jsonb, NOW(), NOW()),
('pricing_gpt4o_transcribe_base', 'gpt-4o-transcribe', 'base', 0, NULL, 0.006, 'USD', '{"unit": "minute"}'::jsonb, NOW(), NOW()),
('pricing_gpt4o_transcribe_diarize_base', 'gpt-4o-transcribe-diarize', 'base', 0, NULL, 0.006, 'USD', '{"unit": "minute"}'::jsonb, NOW(), NOW()),
('pricing_tts_1_base', 'tts-1', 'base', 0, NULL, 0.000015, 'USD', '{"unit": "character"}'::jsonb, NOW(), NOW()),
('pricing_gpt4o_realtime_preview_base', 'gpt-4o-realtime-preview-2024-10-01', 'base', 0, NULL, 0.000004, 'USD', '{"unit": "token", "input_cost_per_1k": 0.004, "output_cost_per_1k": 0.016}'::jsonb, NOW(), NOW()),
('pricing_dalle_2_base', 'dall-e-2', 'base', 0, NULL, 0.020, 'USD', '{"unit": "image"}'::jsonb, NOW(), NOW()),
('pricing_dalle_3_base', 'dall-e-3', 'base', 0, NULL, 0.040, 'USD', '{"unit": "image"}'::jsonb, NOW(), NOW()),
('pricing_sora_2_base', 'sora-2', 'base', 0, NULL, 0.10, 'USD', '{"unit": "second"}'::jsonb, NOW(), NOW()),
('pricing_sora_2_pro_base', 'sora-2-pro', 'base', 0, NULL, 0.30, 'USD', '{"unit": "second"}'::jsonb, NOW(), NOW())
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
    cost_per_unit, unit_type, unit_size,
    original_cost_usd, margin_percentage,
    free_tier_limit, free_tier_period,
    is_active, description, metadata
) VALUES
('cost_text_embedding_3_small_input', 'text-embedding-3-small', 'model_inference', 'openai', 'text-embedding-3-small', 'input', 3, 'token', 1000, 0.00002, 30.0, 0, 'monthly', TRUE, 'Text Embedding 3 Small input tokens (per 1K tokens)', '{}'::jsonb),
('cost_text_embedding_3_large_input', 'text-embedding-3-large', 'model_inference', 'openai', 'text-embedding-3-large', 'input', 17, 'token', 1000, 0.00013, 30.0, 0, 'monthly', TRUE, 'Text Embedding 3 Large input tokens (per 1K tokens)', '{}'::jsonb),
('cost_whisper_1_input', 'whisper-1', 'model_inference', 'openai', 'whisper-1', 'input', 780, 'minute', 1, 0.006, 30.0, 0, 'monthly', TRUE, 'Whisper 1 transcription audio minutes', '{}'::jsonb),
('cost_gpt4o_mini_transcribe_input', 'gpt-4o-mini-transcribe', 'model_inference', 'openai', 'gpt-4o-mini-transcribe', 'input', 390, 'minute', 1, 0.003, 30.0, 0, 'monthly', TRUE, 'GPT-4o Mini Transcribe audio minutes', '{}'::jsonb),
('cost_gpt4o_transcribe_input', 'gpt-4o-transcribe', 'model_inference', 'openai', 'gpt-4o-transcribe', 'input', 780, 'minute', 1, 0.006, 30.0, 0, 'monthly', TRUE, 'GPT-4o Transcribe audio minutes', '{}'::jsonb),
('cost_gpt4o_transcribe_diarize_input', 'gpt-4o-transcribe-diarize', 'model_inference', 'openai', 'gpt-4o-transcribe-diarize', 'input', 780, 'minute', 1, 0.006, 30.0, 0, 'monthly', TRUE, 'GPT-4o Transcribe Diarize audio minutes', '{}'::jsonb),
('cost_tts_1_input', 'tts-1', 'model_inference', 'openai', 'tts-1', 'input', 1950, 'character', 1000, 0.015, 30.0, 0, 'monthly', TRUE, 'TTS 1 text characters (per 1K characters)', '{}'::jsonb),
('cost_gpt4o_realtime_preview_input', 'gpt-4o-realtime-preview-2024-10-01', 'model_inference', 'openai', 'gpt-4o-realtime-preview-2024-10-01', 'input', 520, 'token', 1000, 0.004, 30.0, 0, 'monthly', TRUE, 'GPT-4o realtime preview input tokens (per 1K tokens)', '{}'::jsonb),
('cost_gpt4o_realtime_preview_output', 'gpt-4o-realtime-preview-2024-10-01', 'model_inference', 'openai', 'gpt-4o-realtime-preview-2024-10-01', 'output', 2080, 'token', 1000, 0.016, 30.0, 0, 'monthly', TRUE, 'GPT-4o realtime preview output tokens (per 1K tokens)', '{}'::jsonb),
('cost_dalle_2_input', 'dall-e-2', 'model_inference', 'openai', 'dall-e-2', 'input', 2600, 'image', 1, 0.020, 30.0, 0, 'monthly', TRUE, 'DALL·E 2 generated images', '{}'::jsonb),
('cost_dalle_3_input', 'dall-e-3', 'model_inference', 'openai', 'dall-e-3', 'input', 5200, 'image', 1, 0.040, 30.0, 0, 'monthly', TRUE, 'DALL·E 3 generated images', '{}'::jsonb),
('cost_sora_2_input', 'sora-2', 'model_inference', 'openai', 'sora-2', 'input', 13000, 'second', 1, 0.10, 30.0, 0, 'monthly', TRUE, 'Sora 2 generated video seconds', '{"resolution_tier": "720p_default"}'::jsonb),
('cost_sora_2_pro_input', 'sora-2-pro', 'model_inference', 'openai', 'sora-2-pro', 'input', 39000, 'second', 1, 0.30, 30.0, 0, 'monthly', TRUE, 'Sora 2 Pro generated video seconds', '{"resolution_tier": "720p_default"}'::jsonb)
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
    free_tier_limit = EXCLUDED.free_tier_limit,
    free_tier_period = EXCLUDED.free_tier_period,
    is_active = EXCLUDED.is_active,
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
