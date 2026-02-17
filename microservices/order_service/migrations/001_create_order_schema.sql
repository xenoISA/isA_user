-- Order Service Migration: Create order schema and tables
-- Version: 001
-- Date: 2025-10-27
-- Description: Core tables for order management
-- Following PostgreSQL + gRPC migration guide

-- Create schema
CREATE SCHEMA IF NOT EXISTS "order";

-- Drop existing table if needed (be careful in production!)
DROP TABLE IF EXISTS "order".orders CASCADE;

-- Create orders table with all required fields
CREATE TABLE "order".orders (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Order identification
    order_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    organization_id VARCHAR(255),    -- No FK constraint

    -- Order type and status
    order_type VARCHAR(50) NOT NULL, -- purchase, subscription, credit_purchase, premium_upgrade, device_purchase
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, cancelled, refunded

    -- Financial information
    total_amount DOUBLE PRECISION NOT NULL,  -- Changed from DECIMAL
    currency VARCHAR(3) DEFAULT 'USD',
    discount_amount DOUBLE PRECISION DEFAULT 0,
    tax_amount DOUBLE PRECISION DEFAULT 0,
    final_amount DOUBLE PRECISION NOT NULL,

    -- Payment information
    payment_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed, refunded
    payment_intent_id VARCHAR(255),
    payment_method VARCHAR(50),  -- card, wallet, crypto, etc.

    -- Related entities (no FK constraints - cross-service references)
    subscription_id VARCHAR(255),
    wallet_id VARCHAR(255),
    invoice_id VARCHAR(255),

    -- Order details
    items JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Fulfillment
    fulfillment_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, shipped, delivered, failed
    tracking_number VARCHAR(255),
    shipping_address JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    -- Cancellation info
    cancellation_reason TEXT,
    cancelled_by VARCHAR(255)
);

-- Create indexes for performance
CREATE INDEX idx_orders_user_id ON "order".orders(user_id);
CREATE INDEX idx_orders_organization ON "order".orders(organization_id);
CREATE INDEX idx_orders_order_type ON "order".orders(order_type);
CREATE INDEX idx_orders_status ON "order".orders(status);
CREATE INDEX idx_orders_payment_status ON "order".orders(payment_status);
CREATE INDEX idx_orders_fulfillment_status ON "order".orders(fulfillment_status);
CREATE INDEX idx_orders_created_at ON "order".orders(created_at DESC);
CREATE INDEX idx_orders_payment_intent_id ON "order".orders(payment_intent_id);
CREATE INDEX idx_orders_subscription_id ON "order".orders(subscription_id);
CREATE INDEX idx_orders_wallet_id ON "order".orders(wallet_id);

-- Create composite indexes for common queries
CREATE INDEX idx_orders_user_status ON "order".orders(user_id, status);
CREATE INDEX idx_orders_user_created ON "order".orders(user_id, created_at DESC);

-- Add comments for documentation
COMMENT ON SCHEMA "order" IS 'Order service schema - order management and fulfillment';
COMMENT ON TABLE "order".orders IS 'Order management table for tracking purchases, subscriptions, and credit purchases';
COMMENT ON COLUMN "order".orders.order_id IS 'Unique order identifier';
COMMENT ON COLUMN "order".orders.user_id IS 'User who placed the order';
COMMENT ON COLUMN "order".orders.order_type IS 'Type of order: purchase, subscription, credit_purchase, premium_upgrade, device_purchase';
COMMENT ON COLUMN "order".orders.status IS 'Order status: pending, processing, completed, failed, cancelled, refunded';
COMMENT ON COLUMN "order".orders.payment_intent_id IS 'Payment service intent ID';
COMMENT ON COLUMN "order".orders.subscription_id IS 'Related subscription ID if applicable';
COMMENT ON COLUMN "order".orders.wallet_id IS 'Target wallet for credit purchases';
COMMENT ON COLUMN "order".orders.items IS 'JSON array of order items';
COMMENT ON COLUMN "order".orders.metadata IS 'Additional order metadata';
COMMENT ON COLUMN "order".orders.expires_at IS 'Order expiration time for time-limited orders';
