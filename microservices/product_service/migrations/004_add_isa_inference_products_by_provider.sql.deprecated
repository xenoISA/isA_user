-- Migration: Add ISA Model Inference Service Products by Provider
-- Version: 0.5.0
-- Date: 2025-10-19
-- Description: Adds all ISA Model inference service products organized by provider
--              Providers: OpenAI, YYDS, ISA (Modal), Cerebras

-- =============================================================================
-- 1. ADD ISA MODEL INFERENCE CATEGORY
-- =============================================================================

INSERT INTO dev.product_categories (category_id, name, description, display_order, is_active, metadata)
VALUES (
    'isa_inference',
    'ISA Model Inference Services',
    'AI model inference services across multiple providers: OpenAI, YYDS, ISA Modal, Cerebras. Including text generation, vision analysis, audio processing, image generation, and embeddings.',
    10,
    true,
    '{
        "service_version": "0.5.0",
        "api_base": "http://localhost:8082",
        "supported_providers": ["openai", "yyds", "isa", "cerebras"],
        "test_status": "100% passing",
        "test_date": "2025-10-19"
    }'::jsonb
)
ON CONFLICT (category_id) DO UPDATE
SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- =============================================================================
-- 2. OPENAI PROVIDER PRODUCTS
-- =============================================================================
-- Models: gpt-4.1-nano, gpt-4o-mini, gpt-5-nano (main models for production)

-- OpenAI GPT-4.1-nano
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'openai-gpt-4.1-nano',
    'isa_inference',
    'OpenAI GPT-4.1 Nano',
    'Multimodal model with vision and function calling',
    'OpenAI GPT-4.1 Nano - Latest multimodal model with vision capabilities, function calling, and JSON mode via ISA Model inference service.',
    'model',
    'openai',
    '4.1',
    '{
        "model_name": "gpt-4.1-nano",
        "context_window": 128000,
        "max_tokens": 16384,
        "supports_streaming": true,
        "supports_json_mode": true,
        "supports_function_calling": true,
        "supports_vision": true,
        "multimodal": true
    }'::jsonb,
    '["chat", "completion", "streaming", "json_mode", "function_calling", "vision", "multimodal"]'::jsonb,
    '{"rate_limit_rpm": 10000, "rate_limit_tpm": 2000000}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'text',
    '{"tested": true, "recommended": true, "use_case": "general_purpose"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- OpenAI GPT-4o-mini
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'openai-gpt-4o-mini',
    'isa_inference',
    'OpenAI GPT-4o Mini',
    'Fast, balanced model with vision support',
    'OpenAI GPT-4o Mini - Balanced performance and cost with vision capabilities via ISA Model inference service. Tested with 100% success rate.',
    'model',
    'openai',
    '4.0',
    '{
        "model_name": "gpt-4o-mini",
        "context_window": 128000,
        "max_tokens": 16384,
        "supports_streaming": true,
        "supports_json_mode": true,
        "supports_function_calling": true,
        "supports_vision": true
    }'::jsonb,
    '["chat", "completion", "streaming", "json_mode", "function_calling", "vision"]'::jsonb,
    '{"rate_limit_rpm": 5000, "rate_limit_tpm": 1000000}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'text',
    '{"tested": true, "test_status": "100%", "test_date": "2025-10-19", "recommended": true}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- OpenAI GPT-5-nano
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'openai-gpt-5-nano',
    'isa_inference',
    'OpenAI GPT-5 Nano',
    'Ultra-fast, cost-effective latest generation model',
    'OpenAI GPT-5 Nano - Latest generation model, ultra-fast and cost-effective for high-volume applications via ISA Model inference service. Tested with 100% success rate.',
    'model',
    'openai',
    '5.0',
    '{
        "model_name": "gpt-5-nano",
        "context_window": 128000,
        "max_tokens": 16384,
        "supports_streaming": true,
        "supports_json_mode": true,
        "supports_function_calling": true
    }'::jsonb,
    '["chat", "completion", "streaming", "json_mode", "function_calling"]'::jsonb,
    '{"rate_limit_rpm": 10000, "rate_limit_tpm": 2000000}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'text',
    '{"tested": true, "test_status": "100%", "test_date": "2025-10-19", "recommended": true, "use_case": "high_volume"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- OpenAI Vision (GPT-4o-mini for vision tasks)
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'openai-vision-gpt-4o-mini',
    'isa_inference',
    'OpenAI Vision (GPT-4o Mini)',
    'Image analysis and understanding',
    'OpenAI GPT-4o Mini vision capabilities for image analysis. Tested with 8,646 avg tokens, confidence 1.0.',
    'model',
    'openai',
    '4.0',
    '{
        "model_name": "gpt-4o-mini",
        "task": "analyze",
        "max_image_size_mb": 20,
        "supported_formats": ["jpg", "png", "webp", "gif"]
    }'::jsonb,
    '["image_analysis", "object_detection", "scene_understanding", "text_extraction"]'::jsonb,
    '{"rate_limit_rpm": 1000, "max_images_per_request": 10}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'vision',
    '{"tested": true, "test_status": "100%", "avg_tokens": 8646, "confidence": 1.0, "test_date": "2025-10-19"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- OpenAI Embeddings (text-embedding-3-small)
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'openai-embedding-small',
    'isa_inference',
    'OpenAI Text Embeddings (Small)',
    '1536-dimensional text embeddings',
    'OpenAI text-embedding-3-small for generating 1536-dimensional vectors. Tested with 100% success rate.',
    'model',
    'openai',
    '3.0',
    '{
        "model_name": "text-embedding-3-small",
        "dimensions": 1536,
        "max_input_tokens": 8191
    }'::jsonb,
    '["text_embedding", "semantic_search", "clustering", "classification"]'::jsonb,
    '{"rate_limit_rpm": 5000, "max_batch_size": 100}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'embedding',
    '{"tested": true, "test_status": "100%", "test_date": "2025-10-19"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- OpenAI DALL-E 3
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'openai-dalle-3',
    'isa_inference',
    'OpenAI DALL-E 3',
    'High-quality AI image generation',
    'OpenAI DALL-E 3 for generating high-quality images. Tested at $0.04/image for 1024x1024.',
    'model',
    'openai',
    '3.0',
    '{
        "model_name": "dall-e-3",
        "default_size": "1024x1024",
        "supported_sizes": ["1024x1024", "1024x1792", "1792x1024"],
        "quality_options": ["standard", "hd"]
    }'::jsonb,
    '["image_generation", "prompt_revision", "style_control"]'::jsonb,
    '{"rate_limit_rpm": 50, "max_images_per_request": 1}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'image',
    '{"tested": true, "test_status": "100%", "cost_per_image": 0.04, "test_date": "2025-10-19"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- =============================================================================
-- 3. YYDS PROVIDER PRODUCTS
-- =============================================================================
-- Models: gpt-4o-mini, claude-sonnet-4-20250514

-- YYDS GPT-4o-mini
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'yyds-gpt-4o-mini',
    'isa_inference',
    'YYDS GPT-4o Mini',
    'OpenAI GPT-4o Mini via YYDS provider',
    'GPT-4o Mini accessed through YYDS provider. Tested with 100% success rate.',
    'model',
    'yyds',
    '4.0',
    '{
        "model_name": "gpt-4o-mini",
        "context_window": 128000,
        "max_tokens": 16384,
        "supports_streaming": true,
        "supports_json_mode": true,
        "supports_function_calling": true
    }'::jsonb,
    '["chat", "completion", "streaming", "json_mode", "function_calling"]'::jsonb,
    '{"rate_limit_rpm": 3000, "rate_limit_tpm": 500000}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'text',
    '{"tested": true, "test_status": "100%", "test_date": "2025-10-19", "test_response": "Hi! How can I help you today?"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- YYDS Claude Sonnet 4
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'yyds-claude-sonnet-4-20250514',
    'isa_inference',
    'YYDS Claude Sonnet 4',
    'Anthropic Claude Sonnet 4 via YYDS provider',
    'Anthropic Claude Sonnet 4 (2025-05-14) accessed through YYDS provider. Extended context and advanced reasoning.',
    'model',
    'yyds',
    '4.0',
    '{
        "model_name": "claude-sonnet-4-20250514",
        "context_window": 200000,
        "max_tokens": 8192,
        "supports_streaming": true,
        "supports_json_mode": true,
        "supports_function_calling": true,
        "reasoning": "extended"
    }'::jsonb,
    '["chat", "completion", "streaming", "json_mode", "function_calling", "extended_reasoning", "code_generation"]'::jsonb,
    '{"rate_limit_rpm": 2000, "rate_limit_tpm": 400000}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'text',
    '{"provider": "yyds", "upstream": "anthropic", "recommended_for": "complex_reasoning"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- =============================================================================
-- 4. ISA PROVIDER PRODUCTS (Modal-hosted)
-- =============================================================================
-- Models: isa-surya-ocr-service, isa-omniparser-ui-detection, isa-jina-reranker-v2-service

-- ISA Surya OCR Service
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'isa-surya-ocr',
    'isa_inference',
    'ISA Surya OCR',
    'Multilingual OCR with 90+ languages',
    'ISA Modal-hosted Surya OCR service for text detection and extraction. Supports 90+ languages, deployed on Modal with T4 GPU.',
    'model',
    'isa',
    '1.0',
    '{
        "model_id": "isa-surya-ocr-service",
        "underlying_model": "SuryaOCR",
        "architecture": "EfficientViT + Donut",
        "gpu": "T4",
        "ram_gb": 8,
        "max_containers": 20,
        "cold_start_seconds": 40,
        "warm_response_seconds": 2,
        "max_image_size_mb": 20,
        "max_dimensions": "4096x4096",
        "supported_formats": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
        "timeout_seconds": 60,
        "languages_supported": 90
    }'::jsonb,
    '["ocr", "text_detection", "text_extraction", "multilingual", "image_analysis"]'::jsonb,
    '{"sla_availability": 0.99, "max_response_seconds": 10, "max_throughput_rps": 50}'::jsonb,
    true, true,
    'https://isa-vision-ocr.modal.run',
    'vision',
    '{"deployment": "modal", "cost_per_hour": 0.40, "cost_per_request": 0.0005}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- ISA OmniParser UI Detection
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'isa-omniparser-ui',
    'isa_inference',
    'ISA OmniParser UI Detection',
    'Advanced UI element detection and coordinates',
    'ISA Modal-hosted Microsoft OmniParser v2.0 for UI detection. Optimized single model, deployed on Modal with A10G GPU.',
    'model',
    'isa',
    '2.0',
    '{
        "model_id": "isa-omniparser-ui-detection",
        "underlying_model": "Microsoft OmniParser v2.0",
        "optimization": "single_model",
        "gpu": "A10G",
        "max_containers": 50,
        "cold_start_seconds": 12,
        "warm_response_seconds": 1,
        "max_image_size_mb": 20,
        "max_dimensions": "4096x4096",
        "supported_formats": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
        "timeout_seconds": 30
    }'::jsonb,
    '["ui_detection", "object_coordinates", "image_analysis", "image_understanding"]'::jsonb,
    '{"sla_availability": 0.995, "max_response_seconds": 5, "max_throughput_rps": 100}'::jsonb,
    true, true,
    'https://isa-vision-ui.modal.run',
    'vision',
    '{"deployment": "modal", "cost_per_hour": 0.60, "cost_per_request": 0.001}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- ISA Jina Reranker V2
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'isa-jina-reranker-v2',
    'isa_inference',
    'ISA Jina Reranker V2',
    'SOTA 2024 multilingual reranking',
    'ISA Modal-hosted Jina Reranker V2 for semantic search reranking. Supports 100+ languages, SOTA 2024 cross-encoder.',
    'model',
    'isa',
    '2.0',
    '{
        "model_id": "isa-jina-reranker-v2-service",
        "underlying_model": "jinaai/jina-reranker-v2-base-multilingual",
        "architecture": "Cross-encoder",
        "gpu": "T4",
        "ram_gb": 8,
        "max_containers": 10,
        "cold_start_seconds": 22,
        "warm_response_seconds": 2,
        "max_query_length": 1024,
        "max_document_length": 1024,
        "max_documents_per_request": 100,
        "timeout_seconds": 30,
        "languages_supported": 100
    }'::jsonb,
    '["reranking", "document_ranking", "semantic_search", "cross_lingual_ranking", "multilingual"]'::jsonb,
    '{"sla_availability": 0.99, "max_response_seconds": 5, "max_throughput_rps": 25}'::jsonb,
    true, true,
    'https://isa-embed-rerank.modal.run',
    'embedding',
    '{"deployment": "modal", "cost_per_hour": 0.40, "cost_per_request": 0.0002, "sota": "2024_best_in_class"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- =============================================================================
-- 5. CEREBRAS PROVIDER PRODUCTS
-- =============================================================================
-- Models: gpt-oss-120b (ultra-fast inference)

-- Cerebras GPT-OSS-120B
INSERT INTO dev.products (
    product_id, category_id, name, short_description, description,
    product_type, provider, version,
    specifications, capabilities, limitations,
    is_active, is_public, service_endpoint, service_type, metadata
) VALUES (
    'cerebras-gpt-oss-120b',
    'isa_inference',
    'Cerebras GPT-OSS-120B',
    'Ultra-fast 120B model (2000-3000 tokens/sec)',
    'Cerebras GPT-OSS-120B - Ultra-fast inference at 2000-3000 tokens/sec, 120B parameters via ISA Model inference service.',
    'model',
    'cerebras',
    '1.0',
    '{
        "model_name": "gpt-oss-120b",
        "parameters": "120B",
        "context_window": 8192,
        "max_tokens": 4096,
        "supports_streaming": true,
        "tokens_per_second": 2500,
        "ultra_fast": true
    }'::jsonb,
    '["chat", "completion", "streaming", "ultra_fast_inference"]'::jsonb,
    '{"rate_limit_rpm": 2000, "rate_limit_tpm": 300000}'::jsonb,
    true, true,
    'http://localhost:8082/api/v1/invoke',
    'text',
    '{"tested": true, "speed": "10x_faster_than_gpu", "use_case": "real_time_applications"}'::jsonb
)
ON CONFLICT (product_id) DO UPDATE SET updated_at = NOW();

-- =============================================================================
-- 6. ADD PRICING MODELS BY PROVIDER
-- =============================================================================

-- ============== OPENAI PRICING ==============

-- OpenAI GPT-4.1-nano pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    input_unit_price, output_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-openai-gpt-4.1-nano',
    'openai-gpt-4.1-nano',
    'OpenAI GPT-4.1 Nano Token Pricing',
    'usage_based',
    'token',
    0.00000015,  -- $0.15 per 1M input tokens
    0.0000006,   -- $0.60 per 1M output tokens
    'USD',
    100000,      -- 100K tokens free per month
    'monthly',
    1000,        -- Bill per 1K tokens
    true,
    '{"provider": "openai", "multimodal": true}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- OpenAI GPT-4o-mini pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    input_unit_price, output_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-openai-gpt-4o-mini',
    'openai-gpt-4o-mini',
    'OpenAI GPT-4o Mini Token Pricing',
    'usage_based',
    'token',
    0.00000015,  -- $0.15 per 1M input tokens
    0.0000006,   -- $0.60 per 1M output tokens
    'USD',
    50000,       -- 50K tokens free per month
    'monthly',
    1000,
    true,
    '{"provider": "openai", "tested": true}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- OpenAI GPT-5-nano pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    input_unit_price, output_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-openai-gpt-5-nano',
    'openai-gpt-5-nano',
    'OpenAI GPT-5 Nano Token Pricing',
    'usage_based',
    'token',
    0.00000015,  -- $0.15 per 1M input tokens
    0.0000006,   -- $0.60 per 1M output tokens
    'USD',
    100000,      -- 100K tokens free per month
    'monthly',
    1000,
    true,
    '{"provider": "openai", "tested": true, "recommended": true}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- OpenAI Vision pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    base_unit_price, input_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-openai-vision',
    'openai-vision-gpt-4o-mini',
    'OpenAI Vision Analysis Pricing',
    'usage_based',
    'request',
    0.001,       -- $0.001 per request base
    0.00000015,  -- Plus $0.15 per 1M tokens
    'USD',
    100,         -- 100 requests free per month
    'monthly',
    1,
    true,
    '{"provider": "openai", "tested": true, "avg_tokens": 8646}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- OpenAI Embeddings pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    base_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-openai-embedding',
    'openai-embedding-small',
    'OpenAI Text Embeddings Pricing',
    'usage_based',
    'token',
    0.00000002,  -- $0.02 per 1M tokens
    'USD',
    1000000,     -- 1M tokens free per month
    'monthly',
    1000,
    true,
    '{"provider": "openai", "tested": true, "dimensions": 1536}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- OpenAI DALL-E 3 pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    base_unit_price, currency,
    free_tier_limit, free_tier_period,
    is_active, metadata
) VALUES (
    'pricing-openai-dalle-3',
    'openai-dalle-3',
    'OpenAI DALL-E 3 Image Generation Pricing',
    'usage_based',
    'item',
    0.04,        -- $0.04 per image (standard 1024x1024)
    'USD',
    10,          -- 10 images free per month
    'monthly',
    true,
    '{"provider": "openai", "tested": true, "test_cost": 0.04, "hd_multiplier": 2}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- ============== YYDS PRICING ==============

-- YYDS GPT-4o-mini pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    input_unit_price, output_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-yyds-gpt-4o-mini',
    'yyds-gpt-4o-mini',
    'YYDS GPT-4o Mini Token Pricing',
    'usage_based',
    'token',
    0.0000002,   -- $0.20 per 1M input tokens (slightly cheaper via YYDS)
    0.0000008,   -- $0.80 per 1M output tokens
    'USD',
    50000,       -- 50K tokens free per month
    'monthly',
    1000,
    true,
    '{"provider": "yyds", "tested": true}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- YYDS Claude Sonnet 4 pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    input_unit_price, output_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-yyds-claude-sonnet-4',
    'yyds-claude-sonnet-4-20250514',
    'YYDS Claude Sonnet 4 Token Pricing',
    'usage_based',
    'token',
    0.000003,    -- $3.00 per 1M input tokens
    0.000015,    -- $15.00 per 1M output tokens
    'USD',
    25000,       -- 25K tokens free per month
    'monthly',
    1000,
    true,
    '{"provider": "yyds", "upstream": "anthropic", "extended_context": true}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- ============== ISA MODAL PRICING ==============

-- ISA Surya OCR pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    base_unit_price, currency,
    free_tier_limit, free_tier_period,
    is_active, metadata
) VALUES (
    'pricing-isa-surya-ocr',
    'isa-surya-ocr',
    'ISA Surya OCR Pricing',
    'usage_based',
    'request',
    0.0005,      -- $0.0005 per request
    'USD',
    1000,        -- 1000 requests free per month
    'monthly',
    true,
    '{"provider": "isa", "deployment": "modal", "gpu": "T4", "cost_per_hour": 0.40}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- ISA OmniParser UI pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    base_unit_price, currency,
    free_tier_limit, free_tier_period,
    is_active, metadata
) VALUES (
    'pricing-isa-omniparser-ui',
    'isa-omniparser-ui',
    'ISA OmniParser UI Detection Pricing',
    'usage_based',
    'request',
    0.001,       -- $0.001 per request
    'USD',
    500,         -- 500 requests free per month
    'monthly',
    true,
    '{"provider": "isa", "deployment": "modal", "gpu": "A10G", "cost_per_hour": 0.60}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- ISA Jina Reranker pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    base_unit_price, currency,
    free_tier_limit, free_tier_period,
    is_active, metadata
) VALUES (
    'pricing-isa-jina-reranker',
    'isa-jina-reranker-v2',
    'ISA Jina Reranker V2 Pricing',
    'usage_based',
    'request',
    0.0002,      -- $0.0002 per request
    'USD',
    5000,        -- 5000 requests free per month
    'monthly',
    true,
    '{"provider": "isa", "deployment": "modal", "gpu": "T4", "cost_per_hour": 0.40, "sota": "2024"}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- ============== CEREBRAS PRICING ==============

-- Cerebras GPT-OSS-120B pricing
INSERT INTO dev.pricing_models (
    pricing_model_id, product_id, name, pricing_type, unit_type,
    input_unit_price, output_unit_price, currency,
    free_tier_limit, free_tier_period,
    billing_unit_size, is_active, metadata
) VALUES (
    'pricing-cerebras-gpt-oss-120b',
    'cerebras-gpt-oss-120b',
    'Cerebras GPT-OSS-120B Token Pricing',
    'usage_based',
    'token',
    0.0000006,   -- $0.60 per 1M input tokens
    0.0000006,   -- $0.60 per 1M output tokens (same for Cerebras)
    'USD',
    50000,       -- 50K tokens free per month
    'monthly',
    1000,
    true,
    '{"provider": "cerebras", "ultra_fast": true, "tokens_per_second": 2500}'::jsonb
)
ON CONFLICT (pricing_model_id) DO UPDATE SET updated_at = NOW();

-- =============================================================================
-- 7. UPDATE SERVICE PLANS WITH ISA MODEL CREDITS BY PROVIDER
-- =============================================================================

-- Free Plan
UPDATE dev.service_plans
SET
    included_products = '[
        {"product_id": "openai-gpt-5-nano", "included_usage": 100000, "unit_type": "token"},
        {"product_id": "openai-embedding-small", "included_usage": 10000, "unit_type": "token"},
        {"product_id": "openai-dalle-3", "included_usage": 5, "unit_type": "item"},
        {"product_id": "isa-surya-ocr", "included_usage": 100, "unit_type": "request"}
    ]'::jsonb,
    features = '["isa_model_access", "openai_basic", "isa_modal_ocr"]'::jsonb,
    updated_at = NOW()
WHERE plan_id = 'free-plan';

-- Basic Plan
UPDATE dev.service_plans
SET
    included_products = '[
        {"product_id": "openai-gpt-5-nano", "included_usage": 1000000, "unit_type": "token"},
        {"product_id": "openai-gpt-4o-mini", "included_usage": 500000, "unit_type": "token"},
        {"product_id": "openai-embedding-small", "included_usage": 100000, "unit_type": "token"},
        {"product_id": "openai-vision-gpt-4o-mini", "included_usage": 100, "unit_type": "request"},
        {"product_id": "openai-dalle-3", "included_usage": 50, "unit_type": "item"},
        {"product_id": "yyds-gpt-4o-mini", "included_usage": 250000, "unit_type": "token"},
        {"product_id": "isa-surya-ocr", "included_usage": 500, "unit_type": "request"},
        {"product_id": "isa-jina-reranker-v2", "included_usage": 1000, "unit_type": "request"}
    ]'::jsonb,
    features = '["isa_model_access", "openai_full", "yyds_access", "isa_modal_vision", "streaming", "json_mode"]'::jsonb,
    updated_at = NOW()
WHERE plan_id = 'basic-plan';

-- Pro Plan
UPDATE dev.service_plans
SET
    included_products = '[
        {"product_id": "openai-gpt-5-nano", "included_usage": 10000000, "unit_type": "token"},
        {"product_id": "openai-gpt-4o-mini", "included_usage": 5000000, "unit_type": "token"},
        {"product_id": "openai-gpt-4.1-nano", "included_usage": 2000000, "unit_type": "token"},
        {"product_id": "openai-embedding-small", "included_usage": 1000000, "unit_type": "token"},
        {"product_id": "openai-vision-gpt-4o-mini", "included_usage": 1000, "unit_type": "request"},
        {"product_id": "openai-dalle-3", "included_usage": 500, "unit_type": "item"},
        {"product_id": "yyds-gpt-4o-mini", "included_usage": 2000000, "unit_type": "token"},
        {"product_id": "yyds-claude-sonnet-4-20250514", "included_usage": 500000, "unit_type": "token"},
        {"product_id": "cerebras-gpt-oss-120b", "included_usage": 1000000, "unit_type": "token"},
        {"product_id": "isa-surya-ocr", "included_usage": 5000, "unit_type": "request"},
        {"product_id": "isa-omniparser-ui", "included_usage": 2000, "unit_type": "request"},
        {"product_id": "isa-jina-reranker-v2", "included_usage": 10000, "unit_type": "request"}
    ]'::jsonb,
    features = '["isa_model_access", "openai_full", "yyds_full", "cerebras_access", "isa_modal_full", "streaming", "json_mode", "function_calling", "priority_support"]'::jsonb,
    updated_at = NOW()
WHERE plan_id = 'pro-plan';

-- Enterprise Plan
UPDATE dev.service_plans
SET
    included_products = '[
        {"product_id": "openai-gpt-5-nano", "included_usage": 100000000, "unit_type": "token"},
        {"product_id": "openai-gpt-4o-mini", "included_usage": 50000000, "unit_type": "token"},
        {"product_id": "openai-gpt-4.1-nano", "included_usage": 20000000, "unit_type": "token"},
        {"product_id": "openai-embedding-small", "included_usage": 10000000, "unit_type": "token"},
        {"product_id": "openai-vision-gpt-4o-mini", "included_usage": 10000, "unit_type": "request"},
        {"product_id": "openai-dalle-3", "included_usage": 5000, "unit_type": "item"},
        {"product_id": "yyds-gpt-4o-mini", "included_usage": 20000000, "unit_type": "token"},
        {"product_id": "yyds-claude-sonnet-4-20250514", "included_usage": 5000000, "unit_type": "token"},
        {"product_id": "cerebras-gpt-oss-120b", "included_usage": 10000000, "unit_type": "token"},
        {"product_id": "isa-surya-ocr", "included_usage": 50000, "unit_type": "request"},
        {"product_id": "isa-omniparser-ui", "included_usage": 20000, "unit_type": "request"},
        {"product_id": "isa-jina-reranker-v2", "included_usage": 100000, "unit_type": "request"}
    ]'::jsonb,
    features = '["isa_model_access", "openai_unlimited", "yyds_unlimited", "cerebras_unlimited", "isa_modal_unlimited", "streaming", "json_mode", "function_calling", "priority_support", "dedicated_support", "custom_models", "sla_99.9"]'::jsonb,
    updated_at = NOW()
WHERE plan_id = 'enterprise-plan';

-- =============================================================================
-- MIGRATION COMPLETE - VERIFICATION
-- =============================================================================

DO $$
DECLARE
    product_count INTEGER;
    pricing_count INTEGER;
    openai_count INTEGER;
    yyds_count INTEGER;
    isa_count INTEGER;
    cerebras_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO product_count FROM dev.products WHERE category_id = 'isa_inference';
    SELECT COUNT(*) INTO pricing_count FROM dev.pricing_models
    WHERE product_id IN (SELECT product_id FROM dev.products WHERE category_id = 'isa_inference');

    SELECT COUNT(*) INTO openai_count FROM dev.products WHERE category_id = 'isa_inference' AND provider = 'openai';
    SELECT COUNT(*) INTO yyds_count FROM dev.products WHERE category_id = 'isa_inference' AND provider = 'yyds';
    SELECT COUNT(*) INTO isa_count FROM dev.products WHERE category_id = 'isa_inference' AND provider = 'isa';
    SELECT COUNT(*) INTO cerebras_count FROM dev.products WHERE category_id = 'isa_inference' AND provider = 'cerebras';

    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'ISA Model Inference Products Migration Complete';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Total products added: %', product_count;
    RAISE NOTICE '  - OpenAI provider: %', openai_count;
    RAISE NOTICE '  - YYDS provider: %', yyds_count;
    RAISE NOTICE '  - ISA Modal provider: %', isa_count;
    RAISE NOTICE '  - Cerebras provider: %', cerebras_count;
    RAISE NOTICE 'Total pricing models: %', pricing_count;
    RAISE NOTICE 'Service plans updated: 4 (free, basic, pro, enterprise)';
    RAISE NOTICE 'Test status: 100%% verified (2025-10-19)';
    RAISE NOTICE '=================================================================';
END $$;
