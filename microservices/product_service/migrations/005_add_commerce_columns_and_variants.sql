-- Product Service Migration: Add commerce columns and variants
-- Version: 005
-- Date: 2026-02-02
-- Description: Add digital/physical commerce fields and product variants (SKUs)

-- Add commerce columns to products table
ALTER TABLE product.products
    ADD COLUMN IF NOT EXISTS product_kind VARCHAR(20) DEFAULT 'digital',
    ADD COLUMN IF NOT EXISTS fulfillment_type VARCHAR(20) DEFAULT 'digital',
    ADD COLUMN IF NOT EXISTS inventory_policy VARCHAR(20) DEFAULT 'infinite',
    ADD COLUMN IF NOT EXISTS requires_shipping BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS tax_category VARCHAR(50) DEFAULT 'digital_goods',
    ADD COLUMN IF NOT EXISTS default_sku_id VARCHAR(100);

-- Create product variants table
CREATE TABLE IF NOT EXISTS product.product_variants (
    id SERIAL PRIMARY KEY,
    sku_id VARCHAR(100) UNIQUE NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    sku_code VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255),

    options JSONB DEFAULT '{}'::jsonb,

    price DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency VARCHAR(20) DEFAULT 'USD',
    inventory_policy VARCHAR(20) DEFAULT 'finite',

    weight_grams INTEGER,
    dimensions_cm JSONB,
    hs_code VARCHAR(50),
    origin_country VARCHAR(2),

    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product.product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_active ON product.product_variants(is_active) WHERE is_active = true;

COMMENT ON TABLE product.product_variants IS 'Product variants/SKUs for physical and digital items';
COMMENT ON COLUMN product.product_variants.options IS 'Variant options (size, color, etc.)';
