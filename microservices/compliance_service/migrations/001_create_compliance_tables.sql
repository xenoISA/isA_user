-- Compliance Service Database Schema
-- 创建合规检查相关的数据表
--
-- ==========================================
-- 微服务数据库设计原则:
-- ==========================================
-- 1. NO FOREIGN KEYS to other services' tables
--    - 使用软引用(soft references)而不是外键约束
--    - user_id, organization_id等字段只存储ID值，不建立FK
--    - 这避免了跨服务的数据库依赖
--
-- 2. 每个服务拥有自己的数据库
--    - 通过API调用其他服务，而不是直接查询其他服务的数据库
--    - 例如: 通过AccountServiceClient获取用户信息
--
-- 3. 最终一致性(Eventual Consistency)
--    - 可能会有短暂的数据不一致
--    - 通过事件驱动(NATS)实现最终一致性
--
-- ==========================================
-- 1. 合规检查记录表
-- ==========================================

CREATE TABLE IF NOT EXISTS compliance_checks (
    id SERIAL PRIMARY KEY,
    check_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- 检查基本信息
    check_type VARCHAR(50) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'none',
    
    -- 关联信息
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    session_id VARCHAR(100),
    request_id VARCHAR(100),
    
    -- 内容信息
    content_id VARCHAR(100),
    content_hash VARCHAR(64),
    content_size BIGINT,
    
    -- 检查结果
    confidence_score DECIMAL(3,2) DEFAULT 0.0,
    violations JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    detected_issues TEXT[],
    
    -- 审核详情
    moderation_categories JSONB,
    detected_pii JSONB,
    
    -- 处理信息
    action_taken VARCHAR(50),
    blocked_reason TEXT,
    human_review_required BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR(100),
    review_notes TEXT,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    provider VARCHAR(50),
    
    -- 时间戳
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_compliance_checks_check_id ON compliance_checks(check_id);
CREATE INDEX idx_compliance_checks_user_id ON compliance_checks(user_id);
CREATE INDEX idx_compliance_checks_org_id ON compliance_checks(organization_id);
CREATE INDEX idx_compliance_checks_status ON compliance_checks(status);
CREATE INDEX idx_compliance_checks_risk_level ON compliance_checks(risk_level);
CREATE INDEX idx_compliance_checks_checked_at ON compliance_checks(checked_at DESC);
CREATE INDEX idx_compliance_checks_review_required ON compliance_checks(human_review_required) WHERE human_review_required = TRUE;

-- 复合索引
CREATE INDEX idx_compliance_checks_user_status ON compliance_checks(user_id, status);
CREATE INDEX idx_compliance_checks_org_status ON compliance_checks(organization_id, status);

-- ==========================================
-- 2. 合规策略表
-- ==========================================

CREATE TABLE IF NOT EXISTS compliance_policies (
    id SERIAL PRIMARY KEY,
    policy_id VARCHAR(100) UNIQUE NOT NULL,
    policy_name VARCHAR(200) NOT NULL,
    
    -- 策略范围
    organization_id VARCHAR(100),  -- NULL表示全局策略
    content_types TEXT[] NOT NULL,
    check_types TEXT[] NOT NULL,
    
    -- 策略规则
    rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    thresholds JSONB DEFAULT '{}'::jsonb,
    
    -- 行为配置
    auto_block BOOLEAN DEFAULT TRUE,
    require_human_review BOOLEAN DEFAULT FALSE,
    notification_enabled BOOLEAN DEFAULT TRUE,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- 索引
CREATE INDEX idx_compliance_policies_policy_id ON compliance_policies(policy_id);
CREATE INDEX idx_compliance_policies_org_id ON compliance_policies(organization_id);
CREATE INDEX idx_compliance_policies_active ON compliance_policies(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_compliance_policies_priority ON compliance_policies(priority DESC);

-- ==========================================
-- 3. 违规统计表（可选，用于快速查询）
-- ==========================================

CREATE TABLE IF NOT EXISTS compliance_stats (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    organization_id VARCHAR(100),
    user_id VARCHAR(100),
    
    -- 统计数据
    total_checks INTEGER DEFAULT 0,
    passed_checks INTEGER DEFAULT 0,
    failed_checks INTEGER DEFAULT 0,
    flagged_checks INTEGER DEFAULT 0,
    blocked_checks INTEGER DEFAULT 0,
    
    -- 按类型统计
    checks_by_type JSONB DEFAULT '{}'::jsonb,
    violations_by_category JSONB DEFAULT '{}'::jsonb,
    
    -- 风险统计
    high_risk_count INTEGER DEFAULT 0,
    critical_risk_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 唯一约束
    UNIQUE(date, organization_id, user_id)
);

-- 索引
CREATE INDEX idx_compliance_stats_date ON compliance_stats(date DESC);
CREATE INDEX idx_compliance_stats_org_date ON compliance_stats(organization_id, date DESC);
CREATE INDEX idx_compliance_stats_user_date ON compliance_stats(user_id, date DESC);

-- ==========================================
-- 4. 人工审核队列表（可选）
-- ==========================================

CREATE TABLE IF NOT EXISTS compliance_review_queue (
    id SERIAL PRIMARY KEY,
    check_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- 审核信息
    priority INTEGER DEFAULT 100,
    assigned_to VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, in_review, completed
    
    -- 元数据
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
    
    -- 注意: 不使用外键约束，使用软引用以避免跨服务依赖
    -- check_id references compliance_checks(check_id) logically
);

-- 索引
CREATE INDEX idx_review_queue_status ON compliance_review_queue(status);
CREATE INDEX idx_review_queue_priority ON compliance_review_queue(priority DESC);
CREATE INDEX idx_review_queue_assigned_to ON compliance_review_queue(assigned_to);
CREATE INDEX idx_review_queue_check_id ON compliance_review_queue(check_id);

-- ==========================================
-- 5. 更新触发器
-- ==========================================

-- 自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为各表添加触发器
CREATE TRIGGER update_compliance_checks_updated_at
    BEFORE UPDATE ON compliance_checks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_policies_updated_at
    BEFORE UPDATE ON compliance_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_stats_updated_at
    BEFORE UPDATE ON compliance_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- 6. 视图（用于常见查询）
-- ==========================================

-- 待审核项视图
CREATE OR REPLACE VIEW pending_reviews AS
SELECT 
    cc.check_id,
    cc.user_id,
    cc.organization_id,
    cc.check_type,
    cc.content_type,
    cc.risk_level,
    cc.violations,
    cc.checked_at,
    rq.priority,
    rq.assigned_to
FROM compliance_checks cc
LEFT JOIN compliance_review_queue rq ON cc.check_id = rq.check_id
WHERE cc.human_review_required = TRUE
  AND cc.reviewed_by IS NULL
  AND (rq.status IS NULL OR rq.status = 'pending')
ORDER BY cc.checked_at ASC;

-- 高风险违规视图
CREATE OR REPLACE VIEW high_risk_violations AS
SELECT 
    check_id,
    user_id,
    organization_id,
    check_type,
    content_type,
    risk_level,
    status,
    violations,
    checked_at
FROM compliance_checks
WHERE risk_level IN ('high', 'critical')
  AND status IN ('fail', 'blocked', 'flagged')
ORDER BY checked_at DESC;

-- 每日统计视图
CREATE OR REPLACE VIEW daily_compliance_summary AS
SELECT 
    DATE(checked_at) as date,
    organization_id,
    COUNT(*) as total_checks,
    SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) as failed,
    SUM(CASE WHEN status = 'flagged' THEN 1 ELSE 0 END) as flagged,
    SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
    SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END) as critical_incidents
FROM compliance_checks
GROUP BY DATE(checked_at), organization_id
ORDER BY date DESC, organization_id;

-- ==========================================
-- 7. 示例数据（可选）
-- ==========================================

-- 插入默认全局策略
INSERT INTO compliance_policies (
    policy_id,
    policy_name,
    organization_id,
    content_types,
    check_types,
    rules,
    thresholds,
    auto_block,
    require_human_review,
    notification_enabled,
    is_active,
    priority
) VALUES (
    'default-global-policy',
    'Default Global Compliance Policy',
    NULL,
    ARRAY['text', 'image', 'audio', 'file'],
    ARRAY['content_moderation', 'pii_detection'],
    '{"moderation": {"hate_speech_threshold": 0.5, "violence_threshold": 0.5}, "pii": {"max_pii_count": 3}}'::jsonb,
    '{"block_threshold": 0.7, "flag_threshold": 0.5}'::jsonb,
    TRUE,
    FALSE,
    TRUE,
    TRUE,
    100
) ON CONFLICT (policy_id) DO NOTHING;

-- ==========================================
-- 8. 权限设置
-- ==========================================

-- 授予适当的权限（根据实际环境调整）
-- GRANT SELECT, INSERT, UPDATE ON compliance_checks TO compliance_service_user;
-- GRANT SELECT, INSERT, UPDATE ON compliance_policies TO compliance_service_user;
-- GRANT SELECT ON pending_reviews TO compliance_service_user;
-- GRANT SELECT ON high_risk_violations TO compliance_service_user;

-- ==========================================
-- 9. 注释
-- ==========================================

COMMENT ON TABLE compliance_checks IS '合规检查记录表，存储所有内容检查的结果';
COMMENT ON TABLE compliance_policies IS '合规策略配置表，定义不同组织的合规规则';
COMMENT ON TABLE compliance_stats IS '合规统计表，用于快速查询和报表生成';
COMMENT ON TABLE compliance_review_queue IS '人工审核队列表，管理需要人工审核的项目';

COMMENT ON COLUMN compliance_checks.check_id IS '检查唯一标识符';
COMMENT ON COLUMN compliance_checks.check_type IS '检查类型：content_moderation, pii_detection, prompt_injection等';
COMMENT ON COLUMN compliance_checks.status IS '状态：pass, fail, warning, flagged, blocked, pending';
COMMENT ON COLUMN compliance_checks.risk_level IS '风险级别：none, low, medium, high, critical';
COMMENT ON COLUMN compliance_checks.confidence_score IS '置信度分数(0.0-1.0)';
COMMENT ON COLUMN compliance_checks.violations IS 'JSONB格式的违规项列表';
COMMENT ON COLUMN compliance_checks.detected_pii IS 'JSONB格式的检测到的PII信息';
COMMENT ON COLUMN compliance_checks.human_review_required IS '是否需要人工审核';

-- ==========================================
-- 完成
-- ==========================================

-- 验证表创建
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = current_schema()
      AND table_name IN ('compliance_checks', 'compliance_policies', 'compliance_stats', 'compliance_review_queue');
    
    IF table_count = 4 THEN
        RAISE NOTICE 'Compliance Service tables created successfully!';
    ELSE
        RAISE NOTICE 'Warning: Expected 4 tables, found %', table_count;
    END IF;
END $$;

