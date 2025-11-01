-- Billing Service Migration: Create billing processing tables
-- Version: 001
-- Date: 2025-01-20
-- Description: 专注于使用量跟踪、费用计算和计费处理

-- 1. Create billing records table (核心计费记录)
CREATE TABLE dev.billing_records (
    id SERIAL PRIMARY KEY,
    billing_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- 关联信息
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    usage_record_id VARCHAR(255) NOT NULL, -- 关联到 product_usage_records
    
    -- 产品信息
    product_id VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    
    -- 计费详情
    usage_amount DECIMAL(20, 8) NOT NULL,
    unit_price DECIMAL(20, 10) NOT NULL,
    total_amount DECIMAL(20, 8) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    
    -- 计费方式和状态
    billing_method VARCHAR(50) NOT NULL, -- wallet_deduction, payment_charge, credit_consumption, subscription_included
    billing_status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed, refunded
    
    -- 处理信息
    processed_at TIMESTAMPTZ,
    failure_reason TEXT,
    
    -- 关联的交易记录
    wallet_transaction_id VARCHAR(255),
    payment_transaction_id VARCHAR(255),
    
    -- 元数据
    billing_metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_billing_record_user FOREIGN KEY (user_id)
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_billing_record_organization FOREIGN KEY (organization_id)
        REFERENCES dev.organizations(organization_id) ON DELETE SET NULL,
    CONSTRAINT fk_billing_record_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.user_subscriptions(subscription_id) ON DELETE SET NULL,
    CONSTRAINT fk_billing_record_usage FOREIGN KEY (usage_record_id)
        REFERENCES dev.product_usage_records(usage_id) ON DELETE CASCADE,
    CONSTRAINT fk_billing_record_wallet_transaction FOREIGN KEY (wallet_transaction_id)
        REFERENCES dev.wallet_transactions(transaction_id) ON DELETE SET NULL,
    CONSTRAINT fk_billing_record_payment_transaction FOREIGN KEY (payment_transaction_id)
        REFERENCES dev.payment_transactions(payment_id) ON DELETE SET NULL,
    CONSTRAINT billing_record_amounts_non_negative CHECK (
        usage_amount >= 0 AND unit_price >= 0 AND total_amount >= 0
    ),
    CONSTRAINT billing_record_service_type_valid CHECK (service_type IN (
        'model_inference', 'mcp_service', 'agent_execution', 'storage_minio', 
        'api_gateway', 'notification', 'other'
    )),
    CONSTRAINT billing_record_method_valid CHECK (billing_method IN (
        'wallet_deduction', 'payment_charge', 'credit_consumption', 'subscription_included'
    )),
    CONSTRAINT billing_record_status_valid CHECK (billing_status IN (
        'pending', 'processing', 'completed', 'failed', 'refunded'
    ))
);

-- 2. Create billing events table (计费事件审计)
CREATE TABLE dev.billing_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- 事件详情
    event_type VARCHAR(50) NOT NULL, -- usage_recorded, billing_processed, payment_completed, etc.
    event_source VARCHAR(100) NOT NULL, -- billing_service, webhook, manual, etc.
    
    -- 关联实体
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    billing_record_id VARCHAR(255),
    
    -- 事件数据
    event_data JSONB DEFAULT '{}'::jsonb,
    amount DECIMAL(20, 8),
    currency VARCHAR(10) DEFAULT 'CREDIT',
    
    -- 处理状态
    is_processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_billing_event_user FOREIGN KEY (user_id)
        REFERENCES dev.users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_billing_event_organization FOREIGN KEY (organization_id)
        REFERENCES dev.organizations(organization_id) ON DELETE SET NULL,
    CONSTRAINT fk_billing_event_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.user_subscriptions(subscription_id) ON DELETE SET NULL,
    CONSTRAINT fk_billing_event_billing_record FOREIGN KEY (billing_record_id)
        REFERENCES dev.billing_records(billing_id) ON DELETE SET NULL,
    CONSTRAINT billing_event_type_valid CHECK (event_type IN (
        'usage_recorded', 'billing_processed', 'payment_completed', 
        'refund_issued', 'quota_exceeded', 'billing_failed'
    )),
    CONSTRAINT billing_event_amount_non_negative CHECK (amount IS NULL OR amount >= 0)
);

-- 3. Create usage aggregations table (使用量聚合)
CREATE TABLE dev.usage_aggregations (
    id SERIAL PRIMARY KEY,
    aggregation_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- 聚合维度
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    service_type VARCHAR(50),
    product_id VARCHAR(255),
    
    -- 时间周期
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- hourly, daily, weekly, monthly
    
    -- 聚合数据
    total_usage_count INTEGER DEFAULT 0,
    total_usage_amount DECIMAL(20, 8) DEFAULT 0,
    total_cost DECIMAL(20, 8) DEFAULT 0,
    
    -- 服务详细使用量 (JSON)
    service_breakdown JSONB DEFAULT '{}'::jsonb,
    
    -- 计费状态
    is_billed BOOLEAN DEFAULT false,
    billed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_usage_agg_user FOREIGN KEY (user_id)
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_usage_agg_organization FOREIGN KEY (organization_id)
        REFERENCES dev.organizations(organization_id) ON DELETE SET NULL,
    CONSTRAINT fk_usage_agg_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.user_subscriptions(subscription_id) ON DELETE SET NULL,
    CONSTRAINT usage_agg_counts_non_negative CHECK (
        total_usage_count >= 0 AND total_usage_amount >= 0 AND total_cost >= 0
    ),
    CONSTRAINT usage_agg_period_valid CHECK (period_start < period_end),
    CONSTRAINT usage_agg_period_type_valid CHECK (period_type IN (
        'hourly', 'daily', 'weekly', 'monthly'
    ))
);

-- 4. Create billing quotas table (计费配额)
CREATE TABLE dev.billing_quotas (
    id SERIAL PRIMARY KEY,
    quota_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- 配额所有者 (user_id 或 organization_id 或 subscription_id 其中之一)
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    
    -- 配额范围
    service_type VARCHAR(50) NOT NULL,
    product_id VARCHAR(255),
    
    -- 配额设置
    quota_limit DECIMAL(20, 8) NOT NULL,
    quota_used DECIMAL(20, 8) DEFAULT 0,
    quota_period VARCHAR(20) DEFAULT 'monthly', -- daily, weekly, monthly, yearly
    
    -- 重置设置
    reset_date TIMESTAMPTZ NOT NULL,
    last_reset_date TIMESTAMPTZ,
    auto_reset BOOLEAN DEFAULT true,
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    is_exceeded BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_billing_quota_user FOREIGN KEY (user_id)
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_billing_quota_organization FOREIGN KEY (organization_id)
        REFERENCES dev.organizations(organization_id) ON DELETE CASCADE,
    CONSTRAINT fk_billing_quota_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.user_subscriptions(subscription_id) ON DELETE CASCADE,
    CONSTRAINT billing_quota_amounts_non_negative CHECK (
        quota_limit >= 0 AND quota_used >= 0
    ),
    CONSTRAINT billing_quota_period_valid CHECK (quota_period IN (
        'daily', 'weekly', 'monthly', 'yearly'
    )),
    CONSTRAINT billing_quota_owner_check CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL AND subscription_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NOT NULL AND subscription_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NULL AND subscription_id IS NOT NULL)
    ),
    UNIQUE (user_id, organization_id, subscription_id, service_type, product_id, quota_period)
);

-- Create indexes for performance
CREATE INDEX idx_billing_records_user ON dev.billing_records(user_id);
CREATE INDEX idx_billing_records_org ON dev.billing_records(organization_id);
CREATE INDEX idx_billing_records_subscription ON dev.billing_records(subscription_id);
CREATE INDEX idx_billing_records_usage_record ON dev.billing_records(usage_record_id);
CREATE INDEX idx_billing_records_product ON dev.billing_records(product_id);
CREATE INDEX idx_billing_records_service_type ON dev.billing_records(service_type);
CREATE INDEX idx_billing_records_status ON dev.billing_records(billing_status);
CREATE INDEX idx_billing_records_method ON dev.billing_records(billing_method);
CREATE INDEX idx_billing_records_created ON dev.billing_records(created_at DESC);
CREATE INDEX idx_billing_records_processed ON dev.billing_records(processed_at DESC);

CREATE INDEX idx_billing_events_type ON dev.billing_events(event_type);
CREATE INDEX idx_billing_events_source ON dev.billing_events(event_source);
CREATE INDEX idx_billing_events_user ON dev.billing_events(user_id);
CREATE INDEX idx_billing_events_org ON dev.billing_events(organization_id);
CREATE INDEX idx_billing_events_subscription ON dev.billing_events(subscription_id);
CREATE INDEX idx_billing_events_billing_record ON dev.billing_events(billing_record_id);
CREATE INDEX idx_billing_events_created ON dev.billing_events(created_at DESC);
CREATE INDEX idx_billing_events_processed ON dev.billing_events(is_processed, processed_at);

CREATE INDEX idx_usage_agg_user ON dev.usage_aggregations(user_id);
CREATE INDEX idx_usage_agg_org ON dev.usage_aggregations(organization_id);
CREATE INDEX idx_usage_agg_subscription ON dev.usage_aggregations(subscription_id);
CREATE INDEX idx_usage_agg_service ON dev.usage_aggregations(service_type);
CREATE INDEX idx_usage_agg_product ON dev.usage_aggregations(product_id);
CREATE INDEX idx_usage_agg_period ON dev.usage_aggregations(period_start, period_end);
CREATE INDEX idx_usage_agg_period_type ON dev.usage_aggregations(period_type);
CREATE INDEX idx_usage_agg_billed ON dev.usage_aggregations(is_billed);

CREATE INDEX idx_billing_quotas_user ON dev.billing_quotas(user_id);
CREATE INDEX idx_billing_quotas_org ON dev.billing_quotas(organization_id);
CREATE INDEX idx_billing_quotas_subscription ON dev.billing_quotas(subscription_id);
CREATE INDEX idx_billing_quotas_service ON dev.billing_quotas(service_type);
CREATE INDEX idx_billing_quotas_product ON dev.billing_quotas(product_id);
CREATE INDEX idx_billing_quotas_active ON dev.billing_quotas(is_active) WHERE is_active = true;
CREATE INDEX idx_billing_quotas_exceeded ON dev.billing_quotas(is_exceeded) WHERE is_exceeded = true;
CREATE INDEX idx_billing_quotas_reset ON dev.billing_quotas(reset_date);

-- Composite indexes for common queries
CREATE INDEX idx_billing_records_user_status ON dev.billing_records(user_id, billing_status);
CREATE INDEX idx_billing_records_service_status ON dev.billing_records(service_type, billing_status);
CREATE INDEX idx_usage_agg_user_period ON dev.usage_aggregations(user_id, period_start, period_end);
CREATE INDEX idx_billing_quotas_lookup ON dev.billing_quotas(user_id, organization_id, subscription_id, service_type);

-- Create update triggers
CREATE TRIGGER trigger_update_billing_records_updated_at
    BEFORE UPDATE ON dev.billing_records
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_usage_aggregations_updated_at
    BEFORE UPDATE ON dev.usage_aggregations
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_billing_quotas_updated_at
    BEFORE UPDATE ON dev.billing_quotas
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.billing_records TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.billing_records TO authenticated;
GRANT ALL ON SEQUENCE dev.billing_records_id_seq TO authenticated;

GRANT ALL ON dev.billing_events TO postgres;
GRANT SELECT, INSERT ON dev.billing_events TO authenticated;
GRANT ALL ON SEQUENCE dev.billing_events_id_seq TO authenticated;

GRANT ALL ON dev.usage_aggregations TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.usage_aggregations TO authenticated;
GRANT ALL ON SEQUENCE dev.usage_aggregations_id_seq TO authenticated;

GRANT ALL ON dev.billing_quotas TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.billing_quotas TO authenticated;
GRANT ALL ON SEQUENCE dev.billing_quotas_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.billing_records IS 'Core billing records linking usage to charges';
COMMENT ON TABLE dev.billing_events IS 'Audit trail for all billing-related events';
COMMENT ON TABLE dev.usage_aggregations IS 'Aggregated usage data for reporting and analytics';
COMMENT ON TABLE dev.billing_quotas IS 'Usage quotas and limits for billing control';

COMMENT ON COLUMN dev.billing_records.billing_method IS 'How the billing was processed: wallet_deduction, payment_charge, credit_consumption, subscription_included';
COMMENT ON COLUMN dev.billing_records.usage_record_id IS 'Reference to product_usage_records table';
COMMENT ON COLUMN dev.billing_events.event_data IS 'JSON data specific to the event type';
COMMENT ON COLUMN dev.usage_aggregations.service_breakdown IS 'JSON breakdown of usage by service and product';
COMMENT ON COLUMN dev.billing_quotas.quota_period IS 'Reset period: daily, weekly, monthly, yearly';

-- Insert default quotas for common services (can be overridden per user/org/subscription)
INSERT INTO dev.billing_quotas (
    quota_id, service_type, product_id, quota_limit, quota_period, reset_date
) VALUES 
('default_model_inference_quota', 'model_inference', NULL, 10000, 'monthly', NOW() + INTERVAL '1 month'),
('default_storage_quota', 'storage_minio', NULL, 1000, 'monthly', NOW() + INTERVAL '1 month'),
('default_agent_quota', 'agent_execution', NULL, 100, 'monthly', NOW() + INTERVAL '1 month'),
('default_mcp_quota', 'mcp_service', NULL, 1000, 'monthly', NOW() + INTERVAL '1 month'),
('default_api_gateway_quota', 'api_gateway', NULL, 50000, 'monthly', NOW() + INTERVAL '1 month'),
('default_notification_quota', 'notification', NULL, 5000, 'monthly', NOW() + INTERVAL '1 month')
ON CONFLICT (quota_id) DO NOTHING;