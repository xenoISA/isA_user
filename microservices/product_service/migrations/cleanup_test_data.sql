-- Product Service Test Data Cleanup
-- Purpose: Remove test products and pricing created by 999_insert_test_data_v2.sql
-- Schema: product
-- Date: 2025-11-22

-- Delete test data in reverse order (respecting foreign keys)
-- First delete pricing tiers, then products
DELETE FROM product.product_pricing
WHERE pricing_id IN (
    'pricing_gpt4_base',
    'pricing_minio_base',
    'pricing_minio_tier2',
    'pricing_api_gw_base',
    'pricing_agent_base',
    'pricing_ai_tokens_base'
);

DELETE FROM product.products
WHERE product_id IN (
    'gpt-4',
    'minio_storage',
    'api_gateway',
    'advanced_agent',
    'prod_ai_tokens'
);

-- Verify cleanup
DO $$
DECLARE
    product_count INTEGER;
    pricing_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO product_count FROM product.products;
    SELECT COUNT(*) INTO pricing_count FROM product.product_pricing;

    RAISE NOTICE '=== Product Service Test Data Cleanup Complete ===';
    RAISE NOTICE 'Remaining products: %', product_count;
    RAISE NOTICE 'Remaining pricing tiers: %', pricing_count;
END $$;
