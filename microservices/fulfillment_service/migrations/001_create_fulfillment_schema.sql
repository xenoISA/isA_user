-- Fulfillment Service Schema
-- Version: 001
-- Date: 2026-02-04
-- Description: E-commerce shipment tracking with full lifecycle support

CREATE SCHEMA IF NOT EXISTS fulfillment;

-- Shipments table with full lifecycle tracking
CREATE TABLE IF NOT EXISTS fulfillment.shipments (
    id SERIAL PRIMARY KEY,
    shipment_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    -- Items: [{sku_id, quantity, weight_grams}]
    items JSONB DEFAULT '[]'::jsonb,
    -- Shipping details
    shipping_address JSONB,
    carrier VARCHAR(50),
    tracking_number VARCHAR(100),
    label_url TEXT,
    estimated_delivery TIMESTAMPTZ,
    -- Status: created, label_purchased, in_transit, delivered, failed
    status VARCHAR(30) DEFAULT 'created' CHECK (status IN ('created', 'label_purchased', 'in_transit', 'delivered', 'failed')),
    -- Lifecycle timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    label_created_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    -- Cancellation info
    cancellation_reason TEXT,
    -- Extra data
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_shipments_order ON fulfillment.shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_user ON fulfillment.shipments(user_id);
CREATE INDEX IF NOT EXISTS idx_shipments_tracking ON fulfillment.shipments(tracking_number) WHERE tracking_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_shipments_status ON fulfillment.shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_carrier ON fulfillment.shipments(carrier) WHERE carrier IS NOT NULL;

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION fulfillment.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS shipments_updated_at ON fulfillment.shipments;
CREATE TRIGGER shipments_updated_at
    BEFORE UPDATE ON fulfillment.shipments
    FOR EACH ROW EXECUTE FUNCTION fulfillment.update_updated_at();
