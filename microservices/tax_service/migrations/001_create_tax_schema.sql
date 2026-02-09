-- Tax Service Schema
-- Version: 001
-- Date: 2026-02-04
-- Description: E-commerce tax calculation storage with line-item breakdown

CREATE SCHEMA IF NOT EXISTS tax;

-- Tax calculations per order
CREATE TABLE IF NOT EXISTS tax.calculations (
    id SERIAL PRIMARY KEY,
    calculation_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    -- Amounts
    subtotal DECIMAL(12,2) DEFAULT 0,
    total_tax DECIMAL(12,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    -- Tax breakdown: [{line_item_id, sku_id, tax_amount, tax_rate, jurisdiction, tax_type}]
    tax_lines JSONB DEFAULT '[]'::jsonb,
    -- Address used for tax calculation
    shipping_address JSONB,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_calculations_order ON tax.calculations(order_id);
CREATE INDEX IF NOT EXISTS idx_calculations_user ON tax.calculations(user_id);
CREATE INDEX IF NOT EXISTS idx_calculations_created ON tax.calculations(created_at);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION tax.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS calculations_updated_at ON tax.calculations;
CREATE TRIGGER calculations_updated_at
    BEFORE UPDATE ON tax.calculations
    FOR EACH ROW EXECUTE FUNCTION tax.update_updated_at();
