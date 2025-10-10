-- Order Service Migration: Create orders table
-- Version: 001
-- Description: Create orders table for order management microservice

-- Drop existing table if needed (be careful in production!)
DROP TABLE IF EXISTS dev.orders CASCADE;

-- Create orders table with all required fields
CREATE TABLE dev.orders (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Order identification
    order_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    
    -- Order type and status
    order_type VARCHAR(50) NOT NULL, -- purchase, subscription, credit_purchase, premium_upgrade
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, cancelled, refunded
    
    -- Financial information
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Payment information
    payment_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed, refunded
    payment_intent_id VARCHAR(255),
    
    -- Related entities
    subscription_id VARCHAR(255),
    wallet_id VARCHAR(255),
    
    -- Order details
    items JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    
    -- Foreign key constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_orders_user_id ON dev.orders(user_id);
CREATE INDEX idx_orders_order_type ON dev.orders(order_type);
CREATE INDEX idx_orders_status ON dev.orders(status);
CREATE INDEX idx_orders_payment_status ON dev.orders(payment_status);
CREATE INDEX idx_orders_created_at ON dev.orders(created_at DESC);
CREATE INDEX idx_orders_payment_intent_id ON dev.orders(payment_intent_id);
CREATE INDEX idx_orders_subscription_id ON dev.orders(subscription_id);
CREATE INDEX idx_orders_wallet_id ON dev.orders(wallet_id);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION dev.update_orders_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_orders_updated_at
    BEFORE UPDATE ON dev.orders
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_orders_updated_at();

-- Grant permissions (adjust based on your user setup)
GRANT ALL ON dev.orders TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.orders TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE dev.orders_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.orders IS 'Order management table for tracking purchases, subscriptions, and credit purchases';
COMMENT ON COLUMN dev.orders.order_id IS 'Unique order identifier';
COMMENT ON COLUMN dev.orders.user_id IS 'User who placed the order';
COMMENT ON COLUMN dev.orders.order_type IS 'Type of order: purchase, subscription, credit_purchase, premium_upgrade';
COMMENT ON COLUMN dev.orders.status IS 'Order status: pending, processing, completed, failed, cancelled, refunded';
COMMENT ON COLUMN dev.orders.payment_intent_id IS 'Payment service intent ID';
COMMENT ON COLUMN dev.orders.subscription_id IS 'Related subscription ID if applicable';
COMMENT ON COLUMN dev.orders.wallet_id IS 'Target wallet for credit purchases';
COMMENT ON COLUMN dev.orders.items IS 'JSON array of order items';
COMMENT ON COLUMN dev.orders.metadata IS 'Additional order metadata';
COMMENT ON COLUMN dev.orders.expires_at IS 'Order expiration time for time-limited orders';