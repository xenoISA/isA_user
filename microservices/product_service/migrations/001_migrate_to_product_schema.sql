-- Product Service Migration: Migrate to dedicated product schema
-- Version: 001
-- Date: 2025-10-28
-- Description: Move tables from dev/public schema to product schema

-- Create product schema
CREATE SCHEMA IF NOT EXISTS product;

-- Drop existing tables/views in product schema if they exist
DROP TABLE IF EXISTS product.product_pricing CASCADE;
DROP TABLE IF EXISTS product.products CASCADE;

-- 1. Create products table
CREATE TABLE product.products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(100) UNIQUE NOT NULL,

    -- Product info
    product_name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    product_type VARCHAR(50) NOT NULL,  -- subscription, usage_based, one_time, etc.

    -- Pricing
    base_price DOUBLE PRECISION NOT NULL,
    currency VARCHAR(20) DEFAULT 'USD',
    billing_interval VARCHAR(20),  -- monthly, yearly, daily, etc.

    -- Features
    features JSONB DEFAULT '[]'::jsonb,
    quota_limits JSONB DEFAULT '{}'::jsonb,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create product_pricing table (for tiered/volume pricing)
CREATE TABLE product.product_pricing (
    id SERIAL PRIMARY KEY,
    pricing_id VARCHAR(100) UNIQUE NOT NULL,
    product_id VARCHAR(100) NOT NULL,

    -- Tier info
    tier_name VARCHAR(100),
    min_quantity DOUBLE PRECISION DEFAULT 0,
    max_quantity DOUBLE PRECISION,

    -- Pricing
    unit_price DOUBLE PRECISION NOT NULL,
    currency VARCHAR(20) DEFAULT 'USD',

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Products indexes
CREATE INDEX idx_products_product_id ON product.products(product_id);
CREATE INDEX idx_products_code ON product.products(product_code);
CREATE INDEX idx_products_category ON product.products(category);
CREATE INDEX idx_products_type ON product.products(product_type);
CREATE INDEX idx_products_active ON product.products(is_active);

-- Product pricing indexes
CREATE INDEX idx_pricing_product_id ON product.product_pricing(product_id);
CREATE INDEX idx_pricing_tier ON product.product_pricing(product_id, min_quantity);

-- ====================
-- Update Triggers
-- ====================

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON product.products
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_product_pricing_updated_at
    BEFORE UPDATE ON product.product_pricing
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA product IS 'Product service schema - product catalog and pricing management';
COMMENT ON TABLE product.products IS 'Product catalog with features and quota limits';
COMMENT ON TABLE product.product_pricing IS 'Tiered and volume-based pricing for products';

COMMENT ON COLUMN product.products.features IS 'JSON array of product features';
COMMENT ON COLUMN product.products.quota_limits IS 'JSON object defining usage quotas';
