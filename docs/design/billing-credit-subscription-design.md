# isA Platform - Billing, Credit & Subscription System Design

> Version: 1.0
> Date: 2025-11-28
> Status: Draft

---

## 1. Overview

### 1.1 Purpose

设计一个统一的计费、Credit 和订阅管理系统，支持：
- 多种订阅等级（Free, Pro, Max, Team, Enterprise）
- Credit 体系（订阅配额 + 购买 + 按量付费）
- 三大成本来源的计费（模型推理、存储、MCP Tools）

### 1.2 Core Concepts

| 概念 | 说明 |
|-----|------|
| **Credit** | 平台统一货币，1 Credit = $0.00001 USD (100,000 Credits = $1) |
| **Subscription** | 用户订阅等级，决定月度 Credit 配额和功能权限 |
| **Usage** | 用户对各类服务的使用量（tokens, storage, tools） |
| **Billing** | 将 Usage 转换为 Credit 消耗的计算过程 |

---

## 2. Subscription Tiers

### 2.1 Tier Definition

| Tier | Monthly Price | Annual Price | Monthly Credits | Storage | MCP Tools | Target Users |
|------|--------------|--------------|-----------------|---------|-----------|--------------|
| **Free** | $0 | $0 | 1,000,000 | 1 GB | 10/day | Trial |
| **Pro** | $20 | $200 | 30,000,000 | 20 GB | Unlimited | Individual |
| **Max** | $50 | $500 | 100,000,000 | 100 GB | Unlimited + Advanced | Power User |
| **Team** | $30/user | $300/user | 50,000,000/user | 500 GB shared | Unlimited + Collab | Small Team |
| **Enterprise** | Custom | Custom | Custom | Unlimited | All + Private Deploy | Enterprise |

> Note: 1,000,000 Credits ≈ $10 worth of usage

### 2.2 Credit Value Examples

Based on 1 Credit = $0.00001:

| Usage Type | Actual Cost | With 30% Margin | Credits |
|------------|-------------|-----------------|---------|
| GPT-4o-mini 1K input tokens | $0.00015 | $0.000195 | ~20 |
| GPT-4o-mini 1K output tokens | $0.0006 | $0.00078 | ~78 |
| GPT-4o 1K input tokens | $0.0025 | $0.00325 | ~325 |
| GPT-4o 1K output tokens | $0.01 | $0.013 | ~1,300 |
| Claude Sonnet 1K input | $0.003 | $0.0039 | ~390 |
| Claude Sonnet 1K output | $0.015 | $0.0195 | ~1,950 |
| Web Search (per request) | $0.02 | $0.026 | ~2,600 |
| Storage (per GB/month) | $0.05 | $0.065 | ~6,500 |

### 2.3 Typical Usage Scenarios

| Scenario | Estimated Monthly Credits | Suitable Tier |
|----------|--------------------------|---------------|
| Light user (10 chats/day, GPT-4o-mini) | ~500,000 | Free |
| Regular user (50 chats/day, mixed models) | ~5,000,000 | Pro |
| Heavy user (100+ chats/day, GPT-4o/Claude) | ~30,000,000 | Max |

---

## 3. Credit System

### 3.1 Credit Types

| Type | Source | Expiration | Priority |
|------|--------|------------|----------|
| **Subscription Credits** | Monthly grant from subscription | End of billing period | 1 (first) |
| **Purchased Credits** | One-time purchase | Never expires | 2 (second) |
| **Bonus Credits** | Promotions, referrals | Varies | 3 (third) |
| **Pay-as-you-go** | Credit card charge | N/A | 4 (last) |

### 3.2 Deduction Priority

```
Usage Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Check Subscription Credits (current period, FIFO)       │
│     └─ If available → Deduct → Done                         │
│                                                             │
│  2. Check Purchased Credits (oldest first, FIFO)            │
│     └─ If available → Deduct → Done                         │
│                                                             │
│  3. Check Bonus Credits (by expiration date, FIFO)          │
│     └─ If available → Deduct → Done                         │
│                                                             │
│  4. Pay-as-you-go (if enabled)                              │
│     └─ Charge credit card → Create Credits → Deduct → Done  │
│                                                             │
│  5. Reject Request (insufficient credits)                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Credit Purchase Packages

| Package | Price | Credits | Bonus | Total Credits | Effective Rate |
|---------|-------|---------|-------|---------------|----------------|
| Starter | $5 | 500,000 | 0 | 500,000 | $0.00001/credit |
| Basic | $20 | 2,000,000 | 200,000 (10%) | 2,200,000 | $0.0000091/credit |
| Standard | $50 | 5,000,000 | 1,000,000 (20%) | 6,000,000 | $0.0000083/credit |
| Premium | $100 | 10,000,000 | 3,000,000 (30%) | 13,000,000 | $0.0000077/credit |

---

## 4. Cost Definitions

### 4.1 Model Inference

All prices include 30% margin.

#### Text Models (per 1K tokens)

| Model | Provider | Input Credits | Output Credits |
|-------|----------|---------------|----------------|
| gpt-4o-mini | OpenAI | 20 | 78 |
| gpt-4o | OpenAI | 325 | 1,300 |
| gpt-4-turbo | OpenAI | 1,300 | 3,900 |
| o1 | OpenAI | 1,950 | 7,800 |
| claude-haiku-3 | Anthropic | 33 | 163 |
| claude-haiku-4.5 | Anthropic | 130 | 650 |
| claude-sonnet-4.5 | Anthropic | 390 | 1,950 |
| claude-opus-4.5 | Anthropic | 650 | 3,250 |
| gemini-flash | Google | 10 | 40 |
| gemini-pro | Google | 163 | 650 |

#### Vision Models (per image)

| Model | Small (<512px) | Medium (<1024px) | Large (>1024px) |
|-------|----------------|------------------|-----------------|
| gpt-4o-vision | 1,000 | 2,000 | 4,000 |
| claude-vision | 800 | 1,600 | 3,200 |

#### Audio Models

| Service | Unit | Credits |
|---------|------|---------|
| Whisper (STT) | per minute | 800 |
| TTS (standard) | per 1K chars | 2,000 |
| TTS (HD) | per 1K chars | 4,000 |

#### Image Generation

| Model | Resolution | Credits |
|-------|------------|---------|
| DALL-E 3 | 1024x1024 | 5,200 |
| DALL-E 3 | 1792x1024 | 7,800 |
| Stable Diffusion | 512x512 | 2,600 |

### 4.2 Storage

| Type | Unit | Monthly Credits |
|------|------|-----------------|
| General Storage | per GB | 6,500 |
| RAG Vector Storage | per GB | 13,000 |
| High-speed Cache | per GB | 26,000 |

### 4.3 MCP Tools

| Tool Category | Unit | Credits |
|---------------|------|---------|
| Web Search | per search | 2,600 |
| Web Scraping | per page | 3,900 |
| Browser Automation | per minute | 6,500 |
| Code Interpreter | per minute | 3,900 |
| Document Parsing | per page | 1,300 |

---

## 5. Service Architecture

### 5.1 Service Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  product_service    │  "What does it cost?"
│  (product schema)   │
├─────────────────────┤
│ • subscription_tiers│  - Tier definitions (Free, Pro, Max...)
│ • cost_definitions  │  - Model/tool/storage pricing rules
│ • products          │  - Product catalog
│ • product_pricing   │  - Volume/tiered pricing
└─────────────────────┘
         │
         │ Query pricing
         ▼
┌─────────────────────┐
│subscription_service │  "What plan is the user on?"
│(subscription schema)│
├─────────────────────┤
│ • user_subscriptions│  - User subscription status
│ • subscription_     │  - Plan changes history
│   changes           │
│ • subscription_     │  - Trial management
│   trials            │
└─────────────────────┘
         │
         │ Check subscription, issue credits
         ▼
┌─────────────────────┐
│  billing_service    │  "How much did user use? Convert to credits."
│  (billing schema)   │
├─────────────────────┤
│ • billing_records   │  - Usage → Credit calculation records
│ • billing_events    │  - Billing event log
│ • usage_aggregations│  - Daily/monthly usage summaries
│ • billing_quotas    │  - Quota tracking
└─────────────────────┘
         │
         │ Deduct credits
         ▼
┌─────────────────────┐
│  wallet_service     │  "Manage credit balances and transactions"
│  (wallet schema)    │
├─────────────────────┤
│ • credit_accounts   │  - Credit balances by type
│ • wallets           │  - User wallets (for fiat/crypto)
│ • transactions      │  - All transaction history
└─────────────────────┘
         │
         │ Charge if needed
         ▼
┌─────────────────────┐
│  payment_service    │  "Handle actual money"
│  (payment schema)   │
├─────────────────────┤
│ • payment_methods   │  - Cards, bank accounts
│ • payments          │  - Payment records
│ • invoices          │  - Invoice generation
└─────────────────────┘
```

### 5.2 Event Flow

```
┌──────────────┐     usage.recorded      ┌──────────────┐
│ Model/Tool   │ ───────────────────────▶│   billing    │
│   Service    │                         │   service    │
└──────────────┘                         └──────┬───────┘
                                                │
                                                │ billing.calculated
                                                ▼
┌──────────────┐     credits.deducted    ┌──────────────┐
│ subscription │ ◀───────────────────────│    wallet    │
│   service    │                         │   service    │
└──────────────┘                         └──────┬───────┘
       │                                        │
       │ credits.insufficient                   │ payment.required
       ▼                                        ▼
┌──────────────┐     payment.completed   ┌──────────────┐
│ notification │ ◀───────────────────────│   payment    │
│   service    │                         │   service    │
└──────────────┘                         └──────────────┘
```

---

## 6. Database Schema

### 6.1 product schema (product_service)

```sql
-- Subscription tier definitions
CREATE TABLE product.subscription_tiers (
    id SERIAL PRIMARY KEY,
    tier_id VARCHAR(50) UNIQUE NOT NULL,          -- 'free', 'pro', 'max', 'team', 'enterprise'
    tier_name VARCHAR(100) NOT NULL,
    tier_level INT NOT NULL,                       -- 0=free, 1=pro, 2=max, etc. for comparison

    -- Pricing (USD)
    monthly_price_usd DOUBLE PRECISION NOT NULL,
    annual_price_usd DOUBLE PRECISION,

    -- Monthly Allowances
    monthly_credits BIGINT NOT NULL,               -- Credits granted each month
    storage_gb INT NOT NULL,                       -- Storage included

    -- Limits
    mcp_tools_daily_limit INT,                     -- NULL = unlimited
    max_context_tokens INT,                        -- Model context limit
    max_file_size_mb INT,                          -- File upload limit
    max_team_members INT,                          -- For team plans

    -- Features (JSON array of feature codes)
    features JSONB DEFAULT '[]'::jsonb,

    -- Display
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT TRUE,                -- Show on pricing page
    display_order INT DEFAULT 0,
    badge_text VARCHAR(50),                        -- 'Popular', 'Best Value'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost definitions for all billable services
CREATE TABLE product.cost_definitions (
    id SERIAL PRIMARY KEY,
    cost_id VARCHAR(100) UNIQUE NOT NULL,

    -- Classification
    category VARCHAR(50) NOT NULL,                 -- 'model_inference', 'storage', 'mcp_tool', 'other'
    subcategory VARCHAR(50),                       -- 'text', 'vision', 'audio', 'image_gen'
    service_name VARCHAR(100) NOT NULL,            -- 'gpt-4o-mini', 'web_search', 'storage_general'
    provider VARCHAR(50),                          -- 'openai', 'anthropic', 'google', 'internal'

    -- Pricing
    credits_per_unit BIGINT NOT NULL,              -- Credits charged per unit
    unit_type VARCHAR(50) NOT NULL,                -- 'per_1k_input_tokens', 'per_1k_output_tokens',
                                                   -- 'per_request', 'per_minute', 'per_gb_month', 'per_image'

    -- Cost Basis (internal tracking)
    base_cost_usd DOUBLE PRECISION,                -- Actual cost from provider
    margin_percent INT DEFAULT 30,                 -- Markup percentage

    -- Volume Discounts (optional)
    volume_tiers JSONB,                            -- [{"min": 0, "max": 1000000, "discount_percent": 0}, ...]

    -- Validity
    is_active BOOLEAN DEFAULT TRUE,
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,

    -- Metadata
    display_name VARCHAR(200),
    description TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_subscription_tiers_active ON product.subscription_tiers(is_active, display_order);
CREATE INDEX idx_cost_definitions_lookup ON product.cost_definitions(category, service_name, is_active);
CREATE INDEX idx_cost_definitions_provider ON product.cost_definitions(provider, is_active);
```

### 6.2 subscription schema (subscription_service) - NEW SERVICE

```sql
CREATE SCHEMA IF NOT EXISTS subscription;

-- User subscription records
CREATE TABLE subscription.user_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Subscription Details
    tier_id VARCHAR(50) NOT NULL,                  -- FK to product.subscription_tiers
    billing_cycle VARCHAR(20) NOT NULL,            -- 'monthly', 'annual'

    -- Status
    status VARCHAR(30) NOT NULL,                   -- 'trialing', 'active', 'past_due',
                                                   -- 'cancelled', 'expired', 'paused'

    -- Billing Period
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,

    -- Lifecycle Events
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL,
    cancelled_at TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    ended_at TIMESTAMPTZ,

    -- Payment
    payment_method_id VARCHAR(255),

    -- Credit Issuance Tracking
    last_credits_issued_at TIMESTAMPTZ,
    credits_issued_this_period BIGINT DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscription change history (upgrades, downgrades, etc.)
CREATE TABLE subscription.subscription_changes (
    id SERIAL PRIMARY KEY,
    change_id VARCHAR(100) UNIQUE NOT NULL,
    subscription_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- Change Details
    change_type VARCHAR(30) NOT NULL,              -- 'upgrade', 'downgrade', 'cancel',
                                                   -- 'reactivate', 'trial_start', 'trial_end'
    from_tier_id VARCHAR(50),
    to_tier_id VARCHAR(50),
    from_billing_cycle VARCHAR(20),
    to_billing_cycle VARCHAR(20),

    -- Proration
    prorated_amount DOUBLE PRECISION,
    proration_credits BIGINT,

    -- Reason
    reason TEXT,
    initiated_by VARCHAR(50),                      -- 'user', 'admin', 'system', 'payment_failure'

    effective_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_subscriptions_user ON subscription.user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_org ON subscription.user_subscriptions(organization_id);
CREATE INDEX idx_user_subscriptions_status ON subscription.user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_period_end ON subscription.user_subscriptions(current_period_end);
CREATE INDEX idx_user_subscriptions_tier ON subscription.user_subscriptions(tier_id);
CREATE INDEX idx_subscription_changes_sub ON subscription.subscription_changes(subscription_id);
CREATE INDEX idx_subscription_changes_user ON subscription.subscription_changes(user_id);
```

### 6.3 wallet schema (wallet_service)

```sql
-- Add to existing wallet schema

-- Credit accounts (separate from main wallet for different credit types)
CREATE TABLE wallet.credit_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Credit Type
    credit_type VARCHAR(30) NOT NULL,              -- 'subscription', 'purchased', 'bonus', 'referral'

    -- Balance (in Credits, stored as BIGINT)
    balance BIGINT NOT NULL DEFAULT 0,

    -- Validity Period
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                        -- NULL = never expires

    -- Source Tracking
    source_type VARCHAR(50),                       -- 'subscription_renewal', 'purchase', 'promotion', 'referral'
    source_id VARCHAR(255),                        -- Related subscription_id, order_id, campaign_id

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT balance_non_negative CHECK (balance >= 0)
);

-- Credit transactions (more granular than wallet transactions)
CREATE TABLE wallet.credit_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,

    -- Account Reference
    credit_account_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- Transaction Details
    transaction_type VARCHAR(30) NOT NULL,         -- 'grant', 'consume', 'expire', 'refund', 'transfer'
    amount BIGINT NOT NULL,                        -- Positive for grants, positive for consumes (always positive)
    direction VARCHAR(10) NOT NULL,                -- 'in', 'out'

    -- Balance Tracking
    balance_before BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,

    -- Reference
    reference_type VARCHAR(50),                    -- 'billing_record', 'subscription', 'purchase', 'promotion'
    reference_id VARCHAR(255),

    -- Description
    description TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'completed',        -- 'pending', 'completed', 'failed', 'reversed'

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_credit_accounts_user ON wallet.credit_accounts(user_id);
CREATE INDEX idx_credit_accounts_user_type ON wallet.credit_accounts(user_id, credit_type, is_active);
CREATE INDEX idx_credit_accounts_expires ON wallet.credit_accounts(expires_at)
    WHERE expires_at IS NOT NULL AND is_active = TRUE;
CREATE INDEX idx_credit_accounts_source ON wallet.credit_accounts(source_type, source_id);

CREATE INDEX idx_credit_transactions_account ON wallet.credit_transactions(credit_account_id);
CREATE INDEX idx_credit_transactions_user ON wallet.credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_reference ON wallet.credit_transactions(reference_type, reference_id);
CREATE INDEX idx_credit_transactions_created ON wallet.credit_transactions(created_at DESC);
```

### 6.4 billing schema (billing_service)

```sql
-- Update existing billing_records table to include credit information

ALTER TABLE billing.billing_records
ADD COLUMN IF NOT EXISTS credits_charged BIGINT,
ADD COLUMN IF NOT EXISTS credit_account_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS credit_transaction_id VARCHAR(100);

-- Note: Existing tables (billing_records, billing_events, billing_quotas, usage_aggregations)
-- remain largely unchanged, just add credit-related columns
```

---

## 7. API Endpoints

### 7.1 subscription_service

```
# Subscription Management
GET    /api/v1/subscription/user/{user_id}              # Get user's subscription
POST   /api/v1/subscription/subscribe                    # Create new subscription
PUT    /api/v1/subscription/{subscription_id}/upgrade    # Upgrade plan
PUT    /api/v1/subscription/{subscription_id}/downgrade  # Downgrade plan
POST   /api/v1/subscription/{subscription_id}/cancel     # Cancel subscription
POST   /api/v1/subscription/{subscription_id}/reactivate # Reactivate cancelled

# Tiers
GET    /api/v1/subscription/tiers                        # List available tiers
GET    /api/v1/subscription/tiers/{tier_id}              # Get tier details

# Credits (issued by subscription)
POST   /api/v1/subscription/{subscription_id}/issue-credits  # Manual credit issue (admin)
GET    /api/v1/subscription/{subscription_id}/credit-history # Credit issuance history
```

### 7.2 wallet_service (Credit additions)

```
# Credit Accounts
GET    /api/v1/credits/user/{user_id}                    # Get all credit accounts
GET    /api/v1/credits/user/{user_id}/balance            # Get total available credits
GET    /api/v1/credits/user/{user_id}/breakdown          # Credits by type with expiration

# Credit Operations
POST   /api/v1/credits/consume                           # Consume credits (called by billing)
POST   /api/v1/credits/grant                             # Grant credits (purchase, bonus)
POST   /api/v1/credits/refund                            # Refund credits

# Transactions
GET    /api/v1/credits/transactions/user/{user_id}       # Credit transaction history
```

### 7.3 product_service (Pricing additions)

```
# Cost Definitions
GET    /api/v1/products/costs                            # List all cost definitions
GET    /api/v1/products/costs/{service_name}             # Get specific service cost
GET    /api/v1/products/costs/calculate                  # Calculate credits for usage

# Subscription Tiers
GET    /api/v1/products/subscription-tiers               # List subscription tiers
```

---

## 8. Event Definitions

### 8.1 NATS Subjects

```
# Subscription Events (subscription-stream)
subscription.created           # New subscription created
subscription.activated         # Trial → Active
subscription.upgraded          # Plan upgraded
subscription.downgraded        # Plan downgraded
subscription.cancelled         # Subscription cancelled
subscription.expired           # Subscription expired
subscription.renewed           # Subscription renewed
subscription.credits.issued    # Monthly credits issued

# Credit Events (wallet-stream)
credits.granted                # Credits added to account
credits.consumed               # Credits deducted
credits.expired                # Credits expired
credits.refunded               # Credits refunded
credits.insufficient           # Not enough credits (triggers notification)

# Billing Events (billing-stream)
billing.usage.recorded         # Usage recorded
billing.calculated             # Cost calculated in credits
billing.record.created         # Billing record saved
```

---

## 9. Scheduled Jobs

### 9.1 subscription_service Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| `issue_monthly_credits` | Daily 00:00 UTC | Issue credits to subscriptions starting new period |
| `expire_trials` | Daily 01:00 UTC | End expired trials |
| `check_past_due` | Daily 02:00 UTC | Mark subscriptions as past_due after grace period |
| `send_renewal_reminders` | Daily 03:00 UTC | Send reminders 7 days before renewal |

### 9.2 wallet_service Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| `expire_credits` | Daily 00:30 UTC | Mark expired credit accounts as inactive |
| `cleanup_zero_accounts` | Weekly | Archive empty, expired credit accounts |

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Create subscription_service skeleton
- [ ] Add `subscription_tiers` and `cost_definitions` tables to product_service
- [ ] Add `credit_accounts` and `credit_transactions` tables to wallet_service
- [ ] Implement basic CRUD APIs

### Phase 2: Core Logic (Week 3-4)
- [ ] Implement credit deduction priority logic in wallet_service
- [ ] Update billing_service to calculate credits (not just USD)
- [ ] Implement subscription lifecycle (create, upgrade, cancel)
- [ ] Add event publishing for all services

### Phase 3: Integration (Week 5-6)
- [ ] Connect isA_Model usage → billing_service → wallet_service flow
- [ ] Implement scheduled jobs (credit issuance, expiration)
- [ ] Add subscription → credit account linking

### Phase 4: Testing & Polish (Week 7-8)
- [ ] End-to-end testing with test_user_001
- [ ] Load testing for credit deduction
- [ ] Add monitoring and alerts
- [ ] Documentation and API docs

---

## 11. Configuration

### 11.1 Environment Variables

```bash
# subscription_service
SUBSCRIPTION_GRACE_PERIOD_DAYS=3        # Days after payment failure before past_due
SUBSCRIPTION_TRIAL_DAYS=14              # Default trial period

# Credit System
CREDIT_TO_USD_RATE=0.00001              # 1 Credit = $0.00001
DEFAULT_MARGIN_PERCENT=30               # Default markup on costs

# Scheduled Jobs
CRON_MONTHLY_CREDITS="0 0 * * *"        # When to issue credits
CRON_EXPIRE_CREDITS="30 0 * * *"        # When to expire credits
```

### 11.2 Feature Flags

```json
{
  "enable_pay_as_you_go": true,
  "enable_credit_purchase": true,
  "enable_trial_period": true,
  "enable_annual_billing": true,
  "enable_team_subscriptions": false
}
```

---

## 12. Open Questions

1. **Proration Logic**: How to handle mid-cycle upgrades/downgrades?
   - Option A: Immediate credit adjustment
   - Option B: Effective next billing cycle

2. **Credit Rollover**: Should unused subscription credits roll over?
   - Current design: No rollover (expires at period end)

3. **Team Credit Sharing**: How should team credits be shared among members?
   - Option A: Pooled credits
   - Option B: Per-member allocation

4. **Overage Handling**: What happens when Pay-as-you-go is disabled and credits run out?
   - Current design: Reject requests with `credits.insufficient` event

---

## Appendix A: Migration Checklist

- [ ] Create subscription schema
- [ ] Run product_service migration (add tables)
- [ ] Run wallet_service migration (add tables)
- [ ] Run billing_service migration (alter tables)
- [ ] Seed subscription_tiers data
- [ ] Seed cost_definitions data
- [ ] Deploy subscription_service
- [ ] Update billing_service with credit calculation
- [ ] Update wallet_service with credit deduction logic
- [ ] Test end-to-end flow

---

## Appendix B: Test Data

```sql
-- Insert test subscription tiers
INSERT INTO product.subscription_tiers (tier_id, tier_name, tier_level, monthly_price_usd, annual_price_usd, monthly_credits, storage_gb, features)
VALUES
    ('free', 'Free', 0, 0, 0, 1000000, 1, '["basic_models"]'),
    ('pro', 'Pro', 1, 20, 200, 30000000, 20, '["all_models", "priority_support", "api_access"]'),
    ('max', 'Max', 2, 50, 500, 100000000, 100, '["all_models", "priority_support", "api_access", "advanced_tools", "higher_limits"]');

-- Insert test cost definitions
INSERT INTO product.cost_definitions (cost_id, category, service_name, provider, credits_per_unit, unit_type, base_cost_usd, margin_percent)
VALUES
    ('model_gpt4o_mini_input', 'model_inference', 'gpt-4o-mini', 'openai', 20, 'per_1k_input_tokens', 0.00015, 30),
    ('model_gpt4o_mini_output', 'model_inference', 'gpt-4o-mini', 'openai', 78, 'per_1k_output_tokens', 0.0006, 30),
    ('model_gpt4o_input', 'model_inference', 'gpt-4o', 'openai', 325, 'per_1k_input_tokens', 0.0025, 30),
    ('model_gpt4o_output', 'model_inference', 'gpt-4o', 'openai', 1300, 'per_1k_output_tokens', 0.01, 30),
    ('tool_web_search', 'mcp_tool', 'web_search', 'internal', 2600, 'per_request', 0.02, 30),
    ('storage_general', 'storage', 'storage_general', 'internal', 6500, 'per_gb_month', 0.05, 30);

-- Create test subscription for test_user_001
INSERT INTO subscription.user_subscriptions (subscription_id, user_id, tier_id, billing_cycle, status, current_period_start, current_period_end, started_at, credits_issued_this_period)
VALUES ('sub_test_001', 'test_user_001', 'pro', 'monthly', 'active', NOW(), NOW() + INTERVAL '30 days', NOW(), 30000000);

-- Create credit account for test_user_001
INSERT INTO wallet.credit_accounts (account_id, user_id, credit_type, balance, valid_from, expires_at, source_type, source_id)
VALUES ('credit_test_001', 'test_user_001', 'subscription', 30000000, NOW(), NOW() + INTERVAL '30 days', 'subscription_renewal', 'sub_test_001');
```
