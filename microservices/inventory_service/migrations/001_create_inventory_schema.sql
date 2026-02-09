-- Inventory Service Schema
-- Version: 001
-- Date: 2026-02-04
-- Description: E-commerce inventory management with stock levels and multi-item reservations

CREATE SCHEMA IF NOT EXISTS inventory;

-- Stock levels per SKU/location
CREATE TABLE IF NOT EXISTS inventory.stock_levels (
    id SERIAL PRIMARY KEY,
    sku_id VARCHAR(100) NOT NULL,
    location_id VARCHAR(100) DEFAULT 'default',
    inventory_policy VARCHAR(20) DEFAULT 'finite' CHECK (inventory_policy IN ('finite', 'infinite')),
    on_hand INTEGER DEFAULT 0 CHECK (on_hand >= 0),
    reserved INTEGER DEFAULT 0 CHECK (reserved >= 0),
    available INTEGER GENERATED ALWAYS AS (on_hand - reserved) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE (sku_id, location_id)
);

-- Inventory reservations (multi-item per order)
CREATE TABLE IF NOT EXISTS inventory.reservations (
    id SERIAL PRIMARY KEY,
    reservation_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    -- Items array: [{sku_id, quantity, unit_price}]
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'committed', 'released', 'expired')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    committed_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stock_levels_sku ON inventory.stock_levels(sku_id);
CREATE INDEX IF NOT EXISTS idx_stock_levels_location ON inventory.stock_levels(location_id);

CREATE INDEX IF NOT EXISTS idx_reservations_order ON inventory.reservations(order_id);
CREATE INDEX IF NOT EXISTS idx_reservations_user ON inventory.reservations(user_id);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON inventory.reservations(status);
CREATE INDEX IF NOT EXISTS idx_reservations_expires ON inventory.reservations(expires_at) WHERE status = 'active';

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION inventory.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS stock_levels_updated_at ON inventory.stock_levels;
CREATE TRIGGER stock_levels_updated_at
    BEFORE UPDATE ON inventory.stock_levels
    FOR EACH ROW EXECUTE FUNCTION inventory.update_updated_at();

DROP TRIGGER IF EXISTS reservations_updated_at ON inventory.reservations;
CREATE TRIGGER reservations_updated_at
    BEFORE UPDATE ON inventory.reservations
    FOR EACH ROW EXECUTE FUNCTION inventory.update_updated_at();
