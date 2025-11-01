-- Product Service Migration: Create product and pricing tables
-- Version: 001
-- Date: 2025-01-20
-- Description: Centralized product catalog and pricing for all platform services

-- 1. Create product categories table
CREATE TABLE dev.product_categories (
    id SERIAL PRIMARY KEY,
    category_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_category_id VARCHAR(255), -- For hierarchical categories
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_parent_category FOREIGN KEY (parent_category_id)
        REFERENCES dev.product_categories(category_id) ON DELETE SET NULL
);

-- 2. Create products table (everything we offer)
CREATE TABLE dev.products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL UNIQUE,
    category_id VARCHAR(255) NOT NULL,
    
    -- Product details
    name VARCHAR(100) NOT NULL,
    description TEXT,
    short_description VARCHAR(255),
    
    -- Product classification
    product_type VARCHAR(50) NOT NULL, -- model, storage, agent, mcp_tool, api_service, etc.
    provider VARCHAR(100), -- openai, anthropic, minio, internal, etc.
    
    -- Product specifications
    specifications JSONB DEFAULT '{}'::jsonb, -- model params, storage limits, agent capabilities, etc.
    capabilities JSONB DEFAULT '[]'::jsonb, -- what this product can do
    limitations JSONB DEFAULT '{}'::jsonb, -- usage limits, restrictions
    
    -- Availability
    is_active BOOLEAN DEFAULT true,
    is_public BOOLEAN DEFAULT true, -- visible to all users
    requires_approval BOOLEAN DEFAULT false, -- needs approval to use
    
    -- Versioning
    version VARCHAR(50) DEFAULT '1.0',
    release_date DATE DEFAULT CURRENT_DATE,
    deprecation_date DATE,
    
    -- Integration info
    service_endpoint VARCHAR(255), -- API endpoint if applicable
    service_type VARCHAR(50), -- which microservice handles this
    
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_product_category FOREIGN KEY (category_id)
        REFERENCES dev.product_categories(category_id) ON DELETE RESTRICT,
    CONSTRAINT product_type_valid CHECK (product_type IN (
        'model', 'storage', 'agent', 'mcp_tool', 'api_service', 'notification', 
        'computation', 'data_processing', 'integration', 'other'
    ))
);

-- 3. Create pricing models table (how we charge for products)
CREATE TABLE dev.pricing_models (
    id SERIAL PRIMARY KEY,
    pricing_model_id VARCHAR(255) NOT NULL UNIQUE,
    product_id VARCHAR(255) NOT NULL,
    
    -- Pricing model details
    name VARCHAR(100) NOT NULL,
    pricing_type VARCHAR(50) NOT NULL, -- usage_based, subscription, one_time, freemium, hybrid
    
    -- Usage-based pricing
    unit_type VARCHAR(50), -- token, request, minute, mb, gb, user, etc.
    base_unit_price DECIMAL(20, 10) DEFAULT 0, -- price per unit
    
    -- Input/Output pricing (for models)
    input_unit_price DECIMAL(20, 10) DEFAULT 0, -- price per input unit
    output_unit_price DECIMAL(20, 10) DEFAULT 0, -- price per output unit
    
    -- Fixed costs
    setup_cost DECIMAL(20, 10) DEFAULT 0, -- one-time setup cost
    base_cost_per_request DECIMAL(20, 10) DEFAULT 0, -- fixed cost per request
    
    -- Subscription pricing
    monthly_price DECIMAL(20, 10) DEFAULT 0,
    yearly_price DECIMAL(20, 10) DEFAULT 0,
    
    -- Free tier
    free_tier_limit DECIMAL(20, 8) DEFAULT 0, -- free usage limit
    free_tier_period VARCHAR(20) DEFAULT 'monthly', -- daily, monthly, yearly
    
    -- Billing configuration
    minimum_charge DECIMAL(20, 10) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    billing_unit_size INTEGER DEFAULT 1, -- e.g., round up to nearest 1000 tokens
    
    -- Tier pricing (volume discounts)
    tier_pricing JSONB DEFAULT '[]'::jsonb, -- [{"min_usage": 0, "max_usage": 1000, "unit_price": 0.01}]
    
    -- Status and timing
    is_active BOOLEAN DEFAULT true,
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,
    
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_pricing_product FOREIGN KEY (product_id)
        REFERENCES dev.products(product_id) ON DELETE CASCADE,
    CONSTRAINT pricing_type_valid CHECK (pricing_type IN (
        'usage_based', 'subscription', 'one_time', 'freemium', 'hybrid'
    )),
    CONSTRAINT pricing_unit_prices_non_negative CHECK (
        base_unit_price >= 0 AND input_unit_price >= 0 AND output_unit_price >= 0 AND
        setup_cost >= 0 AND base_cost_per_request >= 0 AND 
        monthly_price >= 0 AND yearly_price >= 0 AND minimum_charge >= 0
    )
);

-- 4. Create service plans table (bundled offerings)
CREATE TABLE dev.service_plans (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Plan details
    name VARCHAR(100) NOT NULL,
    description TEXT,
    plan_tier VARCHAR(50) NOT NULL, -- free, basic, pro, enterprise, custom
    
    -- Plan pricing
    monthly_price DECIMAL(20, 10) DEFAULT 0,
    yearly_price DECIMAL(20, 10) DEFAULT 0,
    setup_fee DECIMAL(20, 10) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    
    -- Plan features and limits
    included_credits DECIMAL(20, 8) DEFAULT 0, -- monthly credits included
    credit_rollover BOOLEAN DEFAULT false, -- unused credits roll over
    
    -- Service inclusions (JSON array)
    included_products JSONB DEFAULT '[]'::jsonb, -- [{"product_id": "gpt-4", "included_usage": 1000, "unit_type": "token"}]
    
    -- Usage limits
    usage_limits JSONB DEFAULT '{}'::jsonb, -- {"max_requests_per_day": 1000, "max_storage_gb": 10}
    
    -- Plan features
    features JSONB DEFAULT '[]'::jsonb, -- ["priority_support", "advanced_analytics", "custom_models"]
    
    -- Overage pricing
    overage_pricing JSONB DEFAULT '{}'::jsonb, -- pricing for usage beyond included amounts
    
    -- Plan availability
    is_active BOOLEAN DEFAULT true,
    is_public BOOLEAN DEFAULT true,
    requires_approval BOOLEAN DEFAULT false,
    max_users INTEGER, -- maximum users for this plan
    
    -- Target audience
    target_audience VARCHAR(50), -- individual, team, enterprise
    
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT plan_tier_valid CHECK (plan_tier IN (
        'free', 'basic', 'pro', 'enterprise', 'custom'
    )),
    CONSTRAINT plan_target_audience_valid CHECK (target_audience IN (
        'individual', 'team', 'enterprise'
    ) OR target_audience IS NULL),
    CONSTRAINT plan_prices_non_negative CHECK (
        monthly_price >= 0 AND yearly_price >= 0 AND setup_fee >= 0
    )
);

-- 5. Create product dependencies table (what depends on what)
CREATE TABLE dev.product_dependencies (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    depends_on_product_id VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL, -- required, optional, alternative
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_product_main FOREIGN KEY (product_id)
        REFERENCES dev.products(product_id) ON DELETE CASCADE,
    CONSTRAINT fk_product_dependency FOREIGN KEY (depends_on_product_id)
        REFERENCES dev.products(product_id) ON DELETE CASCADE,
    CONSTRAINT dependency_type_valid CHECK (dependency_type IN (
        'required', 'optional', 'alternative'
    )),
    UNIQUE (product_id, depends_on_product_id)
);

-- Create indexes for performance
CREATE INDEX idx_product_categories_parent ON dev.product_categories(parent_category_id);
CREATE INDEX idx_product_categories_active ON dev.product_categories(is_active) WHERE is_active = true;

CREATE INDEX idx_products_category ON dev.products(category_id);
CREATE INDEX idx_products_type ON dev.products(product_type);
CREATE INDEX idx_products_provider ON dev.products(provider);
CREATE INDEX idx_products_service_type ON dev.products(service_type);
CREATE INDEX idx_products_active ON dev.products(is_active) WHERE is_active = true;
CREATE INDEX idx_products_public ON dev.products(is_public) WHERE is_public = true;

CREATE INDEX idx_pricing_models_product ON dev.pricing_models(product_id);
CREATE INDEX idx_pricing_models_type ON dev.pricing_models(pricing_type);
CREATE INDEX idx_pricing_models_active ON dev.pricing_models(is_active) WHERE is_active = true;
CREATE INDEX idx_pricing_models_effective ON dev.pricing_models(effective_from, effective_until);

CREATE INDEX idx_service_plans_tier ON dev.service_plans(plan_tier);
CREATE INDEX idx_service_plans_active ON dev.service_plans(is_active) WHERE is_active = true;
CREATE INDEX idx_service_plans_public ON dev.service_plans(is_public) WHERE is_public = true;

CREATE INDEX idx_product_dependencies_product ON dev.product_dependencies(product_id);
CREATE INDEX idx_product_dependencies_depends ON dev.product_dependencies(depends_on_product_id);

-- Create update triggers
CREATE TRIGGER trigger_update_product_categories_updated_at
    BEFORE UPDATE ON dev.product_categories
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_products_updated_at
    BEFORE UPDATE ON dev.products
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_pricing_models_updated_at
    BEFORE UPDATE ON dev.pricing_models
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_service_plans_updated_at
    BEFORE UPDATE ON dev.service_plans
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.product_categories TO postgres;
GRANT SELECT ON dev.product_categories TO authenticated;
GRANT ALL ON SEQUENCE dev.product_categories_id_seq TO authenticated;

GRANT ALL ON dev.products TO postgres;
GRANT SELECT ON dev.products TO authenticated;
GRANT ALL ON SEQUENCE dev.products_id_seq TO authenticated;

GRANT ALL ON dev.pricing_models TO postgres;
GRANT SELECT ON dev.pricing_models TO authenticated;
GRANT ALL ON SEQUENCE dev.pricing_models_id_seq TO authenticated;

GRANT ALL ON dev.service_plans TO postgres;
GRANT SELECT ON dev.service_plans TO authenticated;
GRANT ALL ON SEQUENCE dev.service_plans_id_seq TO authenticated;

GRANT ALL ON dev.product_dependencies TO postgres;
GRANT SELECT ON dev.product_dependencies TO authenticated;
GRANT ALL ON SEQUENCE dev.product_dependencies_id_seq TO authenticated;

-- Add comments
COMMENT ON TABLE dev.product_categories IS 'Product categories for organizing the catalog';
COMMENT ON TABLE dev.products IS 'All products and services offered by the platform';
COMMENT ON TABLE dev.pricing_models IS 'Pricing configuration for each product';
COMMENT ON TABLE dev.service_plans IS 'Bundled service plans with included products and pricing';
COMMENT ON TABLE dev.product_dependencies IS 'Dependencies between products';

-- Insert initial data
INSERT INTO dev.product_categories (category_id, name, description) VALUES
('ai_models', 'AI Models', 'Language models and AI inference services'),
('storage', 'Storage', 'File storage and data management services'),
('agents', 'AI Agents', 'Autonomous AI agents and workflows'),
('mcp', 'MCP Services', 'Model Context Protocol tools and services'),
('api', 'API Services', 'Platform APIs and integrations'),
('notifications', 'Notifications', 'Messaging and notification services')
ON CONFLICT (category_id) DO NOTHING;

-- Insert AI model products (based on existing model_pricing)
INSERT INTO dev.products (product_id, category_id, name, description, product_type, provider, service_type, specifications) VALUES
('gpt-4', 'ai_models', 'GPT-4', 'Advanced language model from OpenAI', 'model', 'openai', 'model_inference', '{"context_length": 8192, "capabilities": ["text_generation", "code", "reasoning"]}'),
('gpt-4-turbo', 'ai_models', 'GPT-4 Turbo', 'Fast and efficient GPT-4 variant', 'model', 'openai', 'model_inference', '{"context_length": 128000, "capabilities": ["text_generation", "code", "reasoning", "vision"]}'),
('gpt-3.5-turbo', 'ai_models', 'GPT-3.5 Turbo', 'Fast and affordable language model', 'model', 'openai', 'model_inference', '{"context_length": 16385, "capabilities": ["text_generation", "code"]}'),
('text-embedding-3-small', 'ai_models', 'Text Embedding 3 Small', 'Small text embedding model', 'model', 'openai', 'model_inference', '{"dimensions": 1536, "capabilities": ["embedding"]}'),
('text-embedding-3-large', 'ai_models', 'Text Embedding 3 Large', 'Large text embedding model', 'model', 'openai', 'model_inference', '{"dimensions": 3072, "capabilities": ["embedding"]}')
ON CONFLICT (product_id) DO NOTHING;

-- Insert other service products
INSERT INTO dev.products (product_id, category_id, name, description, product_type, provider, service_type) VALUES
('minio_storage', 'storage', 'Minio Storage', 'Object storage service', 'storage', 'minio', 'storage_service'),
('basic_agent', 'agents', 'Basic Agent', 'Simple task automation agent', 'agent', 'internal', 'agent_service'),
('advanced_agent', 'agents', 'Advanced Agent', 'Complex reasoning and workflow agent', 'agent', 'internal', 'agent_service'),
('mcp_tools', 'mcp', 'MCP Tools', 'Model Context Protocol tool execution', 'mcp_tool', 'internal', 'mcp_service'),
('api_gateway', 'api', 'API Gateway', 'Platform API access', 'api_service', 'internal', 'gateway_service'),
('push_notifications', 'notifications', 'Push Notifications', 'Mobile and web push notifications', 'notification', 'internal', 'notification_service'),
('email_notifications', 'notifications', 'Email Notifications', 'Email delivery service', 'notification', 'internal', 'notification_service')
ON CONFLICT (product_id) DO NOTHING;

-- Insert pricing models for AI models (migrate from model_pricing)
INSERT INTO dev.pricing_models (pricing_model_id, product_id, name, pricing_type, unit_type, input_unit_price, output_unit_price, currency, free_tier_limit) VALUES
('gpt-4-pricing', 'gpt-4', 'GPT-4 Token Pricing', 'usage_based', 'token', 0.00003, 0.00006, 'CREDIT', 1000),
('gpt-4-turbo-pricing', 'gpt-4-turbo', 'GPT-4 Turbo Token Pricing', 'usage_based', 'token', 0.00001, 0.00003, 'CREDIT', 2000),
('gpt-3.5-turbo-pricing', 'gpt-3.5-turbo', 'GPT-3.5 Turbo Token Pricing', 'usage_based', 'token', 0.0000005, 0.0000015, 'CREDIT', 5000),
('text-embedding-3-small-pricing', 'text-embedding-3-small', 'Text Embedding 3 Small Pricing', 'usage_based', 'token', 0.00000002, 0, 'CREDIT', 10000),
('text-embedding-3-large-pricing', 'text-embedding-3-large', 'Text Embedding 3 Large Pricing', 'usage_based', 'token', 0.00000013, 0, 'CREDIT', 5000)
ON CONFLICT (pricing_model_id) DO NOTHING;

-- Insert pricing for other services
INSERT INTO dev.pricing_models (pricing_model_id, product_id, name, pricing_type, unit_type, base_unit_price, currency, free_tier_limit) VALUES
('minio-storage-pricing', 'minio_storage', 'Minio Storage Pricing', 'usage_based', 'mb', 0.00001, 'CREDIT', 1000),
('basic-agent-pricing', 'basic_agent', 'Basic Agent Pricing', 'usage_based', 'minute', 0.01, 'CREDIT', 60),
('advanced-agent-pricing', 'advanced_agent', 'Advanced Agent Pricing', 'usage_based', 'minute', 0.05, 'CREDIT', 10),
('mcp-tools-pricing', 'mcp_tools', 'MCP Tools Pricing', 'usage_based', 'request', 0.001, 'CREDIT', 100),
('api-gateway-pricing', 'api_gateway', 'API Gateway Pricing', 'usage_based', 'request', 0.0001, 'CREDIT', 10000),
('push-notifications-pricing', 'push_notifications', 'Push Notifications Pricing', 'usage_based', 'notification', 0.0001, 'CREDIT', 1000),
('email-notifications-pricing', 'email_notifications', 'Email Notifications Pricing', 'usage_based', 'email', 0.001, 'CREDIT', 100)
ON CONFLICT (pricing_model_id) DO NOTHING;

-- 6. Create user subscriptions table
CREATE TABLE dev.user_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- User and organization info
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    
    -- Subscription plan
    plan_id VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL,
    
    -- Subscription status
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    billing_cycle VARCHAR(50) NOT NULL DEFAULT 'monthly',
    
    -- Billing periods
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    
    -- Trial period
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    
    -- Cancellation
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    
    -- Next billing
    next_billing_date TIMESTAMPTZ,
    
    -- Payment integration
    payment_method_id VARCHAR(255),
    external_subscription_id VARCHAR(255), -- Stripe等外部订阅ID
    
    -- Usage and limits
    usage_this_period JSONB DEFAULT '{}'::jsonb,
    quota_limits JSONB DEFAULT '{}'::jsonb,
    
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Note: NO foreign keys to users/organizations tables (microservice independence)
    -- Validation happens via service-to-service communication
    CONSTRAINT fk_user_subscription_plan FOREIGN KEY (plan_id)
        REFERENCES dev.service_plans(plan_id) ON DELETE RESTRICT,
    CONSTRAINT user_subscription_status_valid CHECK (status IN (
        'active', 'trialing', 'past_due', 'canceled', 'incomplete', 
        'incomplete_expired', 'unpaid', 'paused'
    )),
    CONSTRAINT user_subscription_billing_cycle_valid CHECK (billing_cycle IN (
        'monthly', 'quarterly', 'yearly', 'one_time'
    )),
    CONSTRAINT user_subscription_period_valid CHECK (current_period_start < current_period_end)
);

-- 7. Create subscription usage table
CREATE TABLE dev.subscription_usage (
    id SERIAL PRIMARY KEY,
    usage_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Subscription info
    subscription_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    
    -- Usage period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Product usage (JSON)
    product_usage JSONB DEFAULT '{}'::jsonb, -- {product_id: {usage_amount: 100, cost: 10.50}}
    
    -- Totals
    total_usage_cost DECIMAL(20, 8) DEFAULT 0,
    credits_consumed DECIMAL(20, 8) DEFAULT 0,
    
    -- Billing status
    is_billed BOOLEAN DEFAULT false,
    billed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Note: NO foreign keys to users/organizations tables (microservice independence)
    CONSTRAINT fk_subscription_usage_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.user_subscriptions(subscription_id) ON DELETE CASCADE,
    CONSTRAINT subscription_usage_cost_non_negative CHECK (total_usage_cost >= 0),
    CONSTRAINT subscription_usage_credits_non_negative CHECK (credits_consumed >= 0),
    CONSTRAINT subscription_usage_period_valid CHECK (period_start < period_end)
);

-- 8. Create product usage records table (详细使用记录)
CREATE TABLE dev.product_usage_records (
    id SERIAL PRIMARY KEY,
    usage_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- User info
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    
    -- Product info
    product_id VARCHAR(255) NOT NULL,
    pricing_model_id VARCHAR(255) NOT NULL,
    
    -- Usage details
    usage_amount DECIMAL(20, 8) NOT NULL,
    unit_type VARCHAR(50) NOT NULL,
    unit_price DECIMAL(20, 10) NOT NULL,
    total_cost DECIMAL(20, 8) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    
    -- Timing
    usage_timestamp TIMESTAMPTZ DEFAULT NOW(),
    usage_period_start TIMESTAMPTZ,
    usage_period_end TIMESTAMPTZ,
    
    -- Details
    usage_details JSONB DEFAULT '{}'::jsonb,
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    
    -- Billing flags
    is_free_tier BOOLEAN DEFAULT false,
    is_included_in_plan BOOLEAN DEFAULT false,
    billing_status VARCHAR(20) DEFAULT 'pending',

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Note: NO foreign keys to users/organizations tables (microservice independence)
    -- Validation happens via service-to-service communication
    CONSTRAINT fk_product_usage_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.user_subscriptions(subscription_id) ON DELETE SET NULL,
    CONSTRAINT fk_product_usage_product FOREIGN KEY (product_id)
        REFERENCES dev.products(product_id) ON DELETE CASCADE,
    CONSTRAINT fk_product_usage_pricing FOREIGN KEY (pricing_model_id)
        REFERENCES dev.pricing_models(pricing_model_id) ON DELETE CASCADE,
    CONSTRAINT product_usage_amount_non_negative CHECK (usage_amount >= 0),
    CONSTRAINT product_usage_unit_price_non_negative CHECK (unit_price >= 0),
    CONSTRAINT product_usage_total_cost_non_negative CHECK (total_cost >= 0)
);

-- Additional indexes for subscription tables
CREATE INDEX idx_user_subscriptions_user ON dev.user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_org ON dev.user_subscriptions(organization_id);
CREATE INDEX idx_user_subscriptions_plan ON dev.user_subscriptions(plan_id);
CREATE INDEX idx_user_subscriptions_status ON dev.user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_billing_cycle ON dev.user_subscriptions(billing_cycle);
CREATE INDEX idx_user_subscriptions_period_end ON dev.user_subscriptions(current_period_end);
CREATE INDEX idx_user_subscriptions_next_billing ON dev.user_subscriptions(next_billing_date);
CREATE INDEX idx_user_subscriptions_external ON dev.user_subscriptions(external_subscription_id);

CREATE INDEX idx_subscription_usage_subscription ON dev.subscription_usage(subscription_id);
CREATE INDEX idx_subscription_usage_user ON dev.subscription_usage(user_id);
CREATE INDEX idx_subscription_usage_period ON dev.subscription_usage(period_start, period_end);
CREATE INDEX idx_subscription_usage_billed ON dev.subscription_usage(is_billed);

CREATE INDEX idx_product_usage_records_user ON dev.product_usage_records(user_id);
CREATE INDEX idx_product_usage_records_org ON dev.product_usage_records(organization_id);
CREATE INDEX idx_product_usage_records_subscription ON dev.product_usage_records(subscription_id);
CREATE INDEX idx_product_usage_records_product ON dev.product_usage_records(product_id);
CREATE INDEX idx_product_usage_records_session ON dev.product_usage_records(session_id);
CREATE INDEX idx_product_usage_records_request ON dev.product_usage_records(request_id);
CREATE INDEX idx_product_usage_records_timestamp ON dev.product_usage_records(usage_timestamp DESC);
CREATE INDEX idx_product_usage_records_billing_status ON dev.product_usage_records(billing_status);

-- Composite indexes for common queries
CREATE INDEX idx_user_subscriptions_user_status ON dev.user_subscriptions(user_id, status);
CREATE INDEX idx_product_usage_records_user_product ON dev.product_usage_records(user_id, product_id, usage_timestamp DESC);

-- Additional triggers
CREATE TRIGGER trigger_update_user_subscriptions_updated_at
    BEFORE UPDATE ON dev.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_subscription_usage_updated_at
    BEFORE UPDATE ON dev.subscription_usage
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Additional permissions
GRANT ALL ON dev.user_subscriptions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.user_subscriptions TO authenticated;
GRANT ALL ON SEQUENCE dev.user_subscriptions_id_seq TO authenticated;

GRANT ALL ON dev.subscription_usage TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.subscription_usage TO authenticated;
GRANT ALL ON SEQUENCE dev.subscription_usage_id_seq TO authenticated;

GRANT ALL ON dev.product_usage_records TO postgres;
GRANT SELECT, INSERT ON dev.product_usage_records TO authenticated;
GRANT ALL ON SEQUENCE dev.product_usage_records_id_seq TO authenticated;

-- Additional comments
COMMENT ON TABLE dev.user_subscriptions IS 'User subscriptions to service plans';
COMMENT ON TABLE dev.subscription_usage IS 'Aggregated usage data by subscription period';
COMMENT ON TABLE dev.product_usage_records IS 'Detailed product usage records for billing';

-- Insert basic service plans
INSERT INTO dev.service_plans (plan_id, name, description, plan_tier, monthly_price, included_credits, target_audience) VALUES
('free-plan', 'Free Plan', 'Basic access with limited usage', 'free', 0, 1000, 'individual'),
('basic-plan', 'Basic Plan', 'Perfect for individual developers', 'basic', 20, 5000, 'individual'),
('pro-plan', 'Pro Plan', 'For growing teams and businesses', 'pro', 100, 25000, 'team'),
('enterprise-plan', 'Enterprise Plan', 'For large organizations', 'enterprise', 500, 150000, 'enterprise')
ON CONFLICT (plan_id) DO NOTHING;