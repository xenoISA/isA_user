-- Product Service Migration: Seed subscription tiers and cost definitions
-- Version: 003
-- Date: 2025-11-28
-- Description: Initial data for subscription tiers and cost definitions
-- Reference: /docs/design/billing-credit-subscription-design.md
-- Credit Rate: 1 Credit = $0.00001 USD (100,000 Credits = $1 USD)

-- ====================
-- Subscription Tiers
-- ====================

-- Free Tier
INSERT INTO product.subscription_tiers (
    tier_id, tier_name, tier_code, description,
    monthly_price_usd, yearly_price_usd,
    monthly_credits, credit_rollover, max_rollover_credits,
    target_audience, min_seats, max_seats,
    features, usage_limits,
    support_level, priority_queue,
    is_active, is_public, display_order, trial_days
) VALUES (
    'tier_free_001',
    'Free',
    'free',
    'Get started with AI-powered features at no cost',
    0,
    0,
    1000000,  -- 1M credits = $10 USD value
    FALSE,
    NULL,
    'individual',
    1,
    1,
    '["Basic AI models", "5GB storage", "Community support", "Standard rate limits"]'::jsonb,
    '{"model_inference": {"daily_requests": 100}, "storage_gb": 5, "mcp_tools": {"daily_requests": 50}}'::jsonb,
    'community',
    FALSE,
    TRUE,
    TRUE,
    0,
    0
) ON CONFLICT (tier_id) DO UPDATE SET
    monthly_credits = EXCLUDED.monthly_credits,
    features = EXCLUDED.features,
    usage_limits = EXCLUDED.usage_limits,
    updated_at = NOW();

-- Pro Tier
INSERT INTO product.subscription_tiers (
    tier_id, tier_name, tier_code, description,
    monthly_price_usd, yearly_price_usd,
    monthly_credits, credit_rollover, max_rollover_credits,
    target_audience, min_seats, max_seats,
    features, usage_limits,
    support_level, priority_queue,
    is_active, is_public, display_order, trial_days
) VALUES (
    'tier_pro_001',
    'Pro',
    'pro',
    'For professionals who need more power and flexibility',
    20,
    192,  -- $16/month when paid yearly (20% discount)
    30000000,  -- 30M credits = $300 USD value
    TRUE,
    15000000,  -- Can rollover up to 15M credits
    'individual',
    1,
    1,
    '["All AI models including Claude Opus", "50GB storage", "Email support", "Higher rate limits", "API access", "Priority queue"]'::jsonb,
    '{"model_inference": {"daily_requests": 1000}, "storage_gb": 50, "mcp_tools": {"daily_requests": 500}}'::jsonb,
    'email',
    TRUE,
    TRUE,
    TRUE,
    1,
    14
) ON CONFLICT (tier_id) DO UPDATE SET
    monthly_price_usd = EXCLUDED.monthly_price_usd,
    monthly_credits = EXCLUDED.monthly_credits,
    features = EXCLUDED.features,
    usage_limits = EXCLUDED.usage_limits,
    updated_at = NOW();

-- Max Tier
INSERT INTO product.subscription_tiers (
    tier_id, tier_name, tier_code, description,
    monthly_price_usd, yearly_price_usd,
    monthly_credits, credit_rollover, max_rollover_credits,
    target_audience, min_seats, max_seats,
    features, usage_limits,
    support_level, priority_queue,
    is_active, is_public, display_order, trial_days
) VALUES (
    'tier_max_001',
    'Max',
    'max',
    'Maximum power for demanding workloads',
    50,
    480,  -- $40/month when paid yearly (20% discount)
    100000000,  -- 100M credits = $1000 USD value
    TRUE,
    50000000,  -- Can rollover up to 50M credits
    'individual',
    1,
    1,
    '["All AI models with highest priority", "200GB storage", "Priority email support", "Unlimited rate limits", "Advanced API features", "Custom integrations"]'::jsonb,
    '{"model_inference": {"daily_requests": -1}, "storage_gb": 200, "mcp_tools": {"daily_requests": -1}}'::jsonb,
    'priority',
    TRUE,
    TRUE,
    TRUE,
    2,
    14
) ON CONFLICT (tier_id) DO UPDATE SET
    monthly_price_usd = EXCLUDED.monthly_price_usd,
    monthly_credits = EXCLUDED.monthly_credits,
    features = EXCLUDED.features,
    usage_limits = EXCLUDED.usage_limits,
    updated_at = NOW();

-- Team Tier
INSERT INTO product.subscription_tiers (
    tier_id, tier_name, tier_code, description,
    monthly_price_usd, yearly_price_usd,
    monthly_credits, credit_rollover, max_rollover_credits,
    target_audience, min_seats, max_seats, per_seat_price_usd,
    features, usage_limits,
    support_level, priority_queue,
    is_active, is_public, display_order, trial_days
) VALUES (
    'tier_team_001',
    'Team',
    'team',
    'Collaborate with your team on AI projects',
    25,  -- Per seat
    240,  -- Per seat yearly ($20/month)
    50000000,  -- 50M credits per seat = $500 USD value per seat
    TRUE,
    25000000,
    'team',
    2,
    50,
    25,
    '["All Pro features", "Team workspace", "Admin console", "Usage analytics", "Shared credit pool", "SSO integration"]'::jsonb,
    '{"model_inference": {"daily_requests": 2000}, "storage_gb": 100, "mcp_tools": {"daily_requests": 1000}}'::jsonb,
    'priority',
    TRUE,
    TRUE,
    TRUE,
    3,
    14
) ON CONFLICT (tier_id) DO UPDATE SET
    monthly_price_usd = EXCLUDED.monthly_price_usd,
    per_seat_price_usd = EXCLUDED.per_seat_price_usd,
    monthly_credits = EXCLUDED.monthly_credits,
    features = EXCLUDED.features,
    usage_limits = EXCLUDED.usage_limits,
    updated_at = NOW();

-- Enterprise Tier
INSERT INTO product.subscription_tiers (
    tier_id, tier_name, tier_code, description,
    monthly_price_usd, yearly_price_usd,
    monthly_credits, credit_rollover, max_rollover_credits,
    target_audience, min_seats, max_seats, per_seat_price_usd,
    features, usage_limits,
    support_level, priority_queue,
    is_active, is_public, display_order, trial_days
) VALUES (
    'tier_enterprise_001',
    'Enterprise',
    'enterprise',
    'Custom solutions for large organizations',
    0,  -- Custom pricing
    0,
    0,  -- Custom allocation
    TRUE,
    NULL,
    'enterprise',
    10,
    NULL,  -- Unlimited
    0,  -- Custom pricing
    '["All Max features", "Dedicated account manager", "Custom SLA", "On-premise deployment option", "Custom model fine-tuning", "Audit logs", "SAML/SCIM", "Data residency options"]'::jsonb,
    '{"model_inference": {"daily_requests": -1}, "storage_gb": -1, "mcp_tools": {"daily_requests": -1}}'::jsonb,
    'dedicated',
    TRUE,
    TRUE,
    FALSE,  -- Not shown in public pricing, contact sales
    4,
    30
) ON CONFLICT (tier_id) DO UPDATE SET
    features = EXCLUDED.features,
    usage_limits = EXCLUDED.usage_limits,
    updated_at = NOW();

-- ====================
-- Cost Definitions - Model Inference
-- ====================
-- All costs include 30% margin
-- 1 Credit = $0.00001 USD

-- Claude Sonnet 4 (claude-sonnet-4-20250514)
-- Input: $3/1M tokens → with 30% margin: $3.90/1M → 390,000 credits/1M tokens → 390 credits/1K tokens
-- Output: $15/1M tokens → with 30% margin: $19.50/1M → 1,950,000 credits/1M tokens → 1,950 credits/1K tokens

INSERT INTO product.cost_definitions (
    cost_id, product_id, service_type, provider, model_name, operation_type,
    cost_per_unit, unit_type, unit_size,
    original_cost_usd, margin_percentage,
    free_tier_limit, free_tier_period,
    is_active, description
) VALUES
-- Claude Sonnet 4
('cost_claude_sonnet4_input', NULL, 'model_inference', 'anthropic', 'claude-sonnet-4-20250514', 'input',
 390, 'token', 1000,
 0.003, 30.0,
 10000, 'monthly',
 TRUE, 'Claude Sonnet 4 input tokens (per 1K tokens)'),

('cost_claude_sonnet4_output', NULL, 'model_inference', 'anthropic', 'claude-sonnet-4-20250514', 'output',
 1950, 'token', 1000,
 0.015, 30.0,
 2000, 'monthly',
 TRUE, 'Claude Sonnet 4 output tokens (per 1K tokens)'),

-- Claude Opus 4 (claude-opus-4-20250514)
-- Input: $15/1M tokens → with 30% margin: $19.50/1M → 1,950,000 credits/1M → 1,950 credits/1K tokens
-- Output: $75/1M tokens → with 30% margin: $97.50/1M → 9,750,000 credits/1M → 9,750 credits/1K tokens

('cost_claude_opus4_input', NULL, 'model_inference', 'anthropic', 'claude-opus-4-20250514', 'input',
 1950, 'token', 1000,
 0.015, 30.0,
 2000, 'monthly',
 TRUE, 'Claude Opus 4 input tokens (per 1K tokens)'),

('cost_claude_opus4_output', NULL, 'model_inference', 'anthropic', 'claude-opus-4-20250514', 'output',
 9750, 'token', 1000,
 0.075, 30.0,
 500, 'monthly',
 TRUE, 'Claude Opus 4 output tokens (per 1K tokens)'),

-- Claude Haiku 3.5 (claude-3-5-haiku-20241022)
-- Input: $0.80/1M tokens → with 30% margin: $1.04/1M → 104,000 credits/1M → 104 credits/1K tokens
-- Output: $4/1M tokens → with 30% margin: $5.20/1M → 520,000 credits/1M → 520 credits/1K tokens

('cost_claude_haiku35_input', NULL, 'model_inference', 'anthropic', 'claude-3-5-haiku-20241022', 'input',
 104, 'token', 1000,
 0.0008, 30.0,
 50000, 'monthly',
 TRUE, 'Claude Haiku 3.5 input tokens (per 1K tokens)'),

('cost_claude_haiku35_output', NULL, 'model_inference', 'anthropic', 'claude-3-5-haiku-20241022', 'output',
 520, 'token', 1000,
 0.004, 30.0,
 10000, 'monthly',
 TRUE, 'Claude Haiku 3.5 output tokens (per 1K tokens)'),

-- GPT-4o
-- Input: $2.50/1M tokens → with 30% margin: $3.25/1M → 325,000 credits/1M → 325 credits/1K tokens
-- Output: $10/1M tokens → with 30% margin: $13/1M → 1,300,000 credits/1M → 1,300 credits/1K tokens

('cost_gpt4o_input', NULL, 'model_inference', 'openai', 'gpt-4o', 'input',
 325, 'token', 1000,
 0.0025, 30.0,
 10000, 'monthly',
 TRUE, 'GPT-4o input tokens (per 1K tokens)'),

('cost_gpt4o_output', NULL, 'model_inference', 'openai', 'gpt-4o', 'output',
 1300, 'token', 1000,
 0.01, 30.0,
 2000, 'monthly',
 TRUE, 'GPT-4o output tokens (per 1K tokens)'),

-- GPT-4o Mini
-- Input: $0.15/1M tokens → with 30% margin: $0.195/1M → 19,500 credits/1M → 20 credits/1K tokens (rounded)
-- Output: $0.60/1M tokens → with 30% margin: $0.78/1M → 78,000 credits/1M → 78 credits/1K tokens

('cost_gpt4o_mini_input', NULL, 'model_inference', 'openai', 'gpt-4o-mini', 'input',
 20, 'token', 1000,
 0.00015, 30.0,
 100000, 'monthly',
 TRUE, 'GPT-4o Mini input tokens (per 1K tokens)'),

('cost_gpt4o_mini_output', NULL, 'model_inference', 'openai', 'gpt-4o-mini', 'output',
 78, 'token', 1000,
 0.0006, 30.0,
 20000, 'monthly',
 TRUE, 'GPT-4o Mini output tokens (per 1K tokens)'),

-- Gemini 2.0 Flash
-- Input: Free under 128K → with margin: $0.195/1M → 19,500 credits/1M → 20 credits/1K tokens
-- Output: Free under 128K → with margin: $0.78/1M → 78,000 credits/1M → 78 credits/1K tokens

('cost_gemini2_flash_input', NULL, 'model_inference', 'google', 'gemini-2.0-flash', 'input',
 20, 'token', 1000,
 0.00015, 30.0,
 200000, 'monthly',
 TRUE, 'Gemini 2.0 Flash input tokens (per 1K tokens)'),

('cost_gemini2_flash_output', NULL, 'model_inference', 'google', 'gemini-2.0-flash', 'output',
 78, 'token', 1000,
 0.0006, 30.0,
 50000, 'monthly',
 TRUE, 'Gemini 2.0 Flash output tokens (per 1K tokens)')

ON CONFLICT (cost_id) DO UPDATE SET
    cost_per_unit = EXCLUDED.cost_per_unit,
    original_cost_usd = EXCLUDED.original_cost_usd,
    free_tier_limit = EXCLUDED.free_tier_limit,
    updated_at = NOW();

-- ====================
-- Cost Definitions - Storage (MinIO)
-- ====================
-- S3-compatible storage: ~$0.023/GB/month → with 30% margin: $0.03/GB/month
-- $0.03/GB/month = 3,000 credits/GB/month

INSERT INTO product.cost_definitions (
    cost_id, product_id, service_type, provider, model_name, operation_type,
    cost_per_unit, unit_type, unit_size,
    original_cost_usd, margin_percentage,
    free_tier_limit, free_tier_period,
    is_active, description
) VALUES
('cost_storage_minio', NULL, 'storage_minio', 'internal', 'minio', 'storage_gb_month',
 3000, 'gb_month', 1,
 0.023, 30.0,
 5, 'monthly',  -- 5GB free storage
 TRUE, 'MinIO object storage (per GB per month)'),

('cost_storage_egress', NULL, 'storage_minio', 'internal', 'minio', 'egress_gb',
 1170, 'gb', 1,
 0.009, 30.0,
 10, 'monthly',  -- 10GB free egress
 TRUE, 'MinIO egress/download (per GB)')

ON CONFLICT (cost_id) DO UPDATE SET
    cost_per_unit = EXCLUDED.cost_per_unit,
    free_tier_limit = EXCLUDED.free_tier_limit,
    updated_at = NOW();

-- ====================
-- Cost Definitions - MCP Tools
-- ====================

INSERT INTO product.cost_definitions (
    cost_id, product_id, service_type, provider, model_name, operation_type,
    cost_per_unit, unit_type, unit_size,
    original_cost_usd, margin_percentage,
    free_tier_limit, free_tier_period,
    is_active, description
) VALUES
-- Web Search (using external API)
-- ~$0.003/request → with 30% margin: $0.0039 → 390 credits/request
('cost_mcp_web_search', NULL, 'mcp_service', 'external', 'web_search', 'request',
 390, 'request', 1,
 0.003, 30.0,
 100, 'monthly',
 TRUE, 'Web search API calls (per request)'),

-- Web Fetch/Scrape
-- ~$0.001/request → with 30% margin: $0.0013 → 130 credits/request
('cost_mcp_web_fetch', NULL, 'mcp_service', 'internal', 'web_fetch', 'request',
 130, 'request', 1,
 0.001, 30.0,
 200, 'monthly',
 TRUE, 'Web page fetch/scrape (per request)'),

-- Browser Automation
-- ~$0.01/minute → with 30% margin: $0.013 → 1,300 credits/minute
('cost_mcp_browser', NULL, 'mcp_service', 'internal', 'browser_automation', 'minute',
 1300, 'minute', 1,
 0.01, 30.0,
 30, 'monthly',  -- 30 minutes free
 TRUE, 'Browser automation (per minute)'),

-- Code Interpreter
-- ~$0.002/execution → with 30% margin: $0.0026 → 260 credits/execution
('cost_mcp_code_interpreter', NULL, 'mcp_service', 'internal', 'code_interpreter', 'execution',
 260, 'execution', 1,
 0.002, 30.0,
 100, 'monthly',
 TRUE, 'Code interpreter execution (per run)'),

-- Image Generation (e.g., DALL-E, Stable Diffusion)
-- ~$0.04/image → with 30% margin: $0.052 → 5,200 credits/image
('cost_mcp_image_gen', NULL, 'mcp_service', 'external', 'image_generation', 'image',
 5200, 'image', 1,
 0.04, 30.0,
 10, 'monthly',  -- 10 free images
 TRUE, 'Image generation (per image)'),

-- Speech-to-Text (Whisper)
-- ~$0.006/minute → with 30% margin: $0.0078 → 780 credits/minute
('cost_mcp_stt', NULL, 'mcp_service', 'openai', 'whisper', 'minute',
 780, 'minute', 1,
 0.006, 30.0,
 60, 'monthly',  -- 60 minutes free
 TRUE, 'Speech-to-text transcription (per minute)'),

-- Text-to-Speech
-- ~$0.015/1K characters → with 30% margin: $0.0195 → 1,950 credits/1K chars
('cost_mcp_tts', NULL, 'mcp_service', 'openai', 'tts', 'character',
 1950, 'character', 1000,
 0.015, 30.0,
 10000, 'monthly',  -- 10K characters free
 TRUE, 'Text-to-speech synthesis (per 1K characters)')

ON CONFLICT (cost_id) DO UPDATE SET
    cost_per_unit = EXCLUDED.cost_per_unit,
    free_tier_limit = EXCLUDED.free_tier_limit,
    updated_at = NOW();

-- ====================
-- Cost Definitions - Notifications
-- ====================

INSERT INTO product.cost_definitions (
    cost_id, product_id, service_type, provider, model_name, operation_type,
    cost_per_unit, unit_type, unit_size,
    original_cost_usd, margin_percentage,
    free_tier_limit, free_tier_period,
    is_active, description
) VALUES
-- Email notifications
-- ~$0.0001/email → with 30% margin: $0.00013 → 13 credits/email
('cost_notification_email', NULL, 'notification', 'internal', 'email', 'email',
 13, 'email', 1,
 0.0001, 30.0,
 100, 'monthly',
 TRUE, 'Email notifications (per email)'),

-- Push notifications
-- ~$0.00001/notification → with 30% margin: $0.000013 → 1.3 ≈ 2 credits/notification
('cost_notification_push', NULL, 'notification', 'internal', 'push', 'notification',
 2, 'notification', 1,
 0.00001, 30.0,
 1000, 'monthly',
 TRUE, 'Push notifications (per notification)'),

-- SMS notifications
-- ~$0.01/sms → with 30% margin: $0.013 → 1,300 credits/sms
('cost_notification_sms', NULL, 'notification', 'external', 'sms', 'sms',
 1300, 'sms', 1,
 0.01, 30.0,
 10, 'monthly',
 TRUE, 'SMS notifications (per message)')

ON CONFLICT (cost_id) DO UPDATE SET
    cost_per_unit = EXCLUDED.cost_per_unit,
    free_tier_limit = EXCLUDED.free_tier_limit,
    updated_at = NOW();

-- ====================
-- Verification Query
-- ====================
-- SELECT tier_code, tier_name, monthly_price_usd, monthly_credits FROM product.subscription_tiers ORDER BY display_order;
-- SELECT service_type, provider, model_name, operation_type, cost_per_unit, unit_type FROM product.cost_definitions ORDER BY service_type, provider;
