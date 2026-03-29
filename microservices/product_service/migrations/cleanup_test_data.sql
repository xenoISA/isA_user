-- Product Service Test Data Cleanup
-- Purpose: Remove test products and pricing created by 999_insert_test_data_v3.sql
-- Schema: product
-- Updated: 2026-03-29

-- Delete test data in reverse order (respecting foreign keys)
-- First delete pricing tiers, then products

-- v3 pricing IDs
DELETE FROM product.product_pricing
WHERE pricing_id IN (
    'pricing_claude_sonnet4_base',
    'pricing_claude_opus4_base',
    'pricing_claude_haiku35_base',
    'pricing_gpt4o_base',
    'pricing_gpt4o_mini_base',
    'pricing_gemini2_flash_base',
    'pricing_minio_base',
    'pricing_api_gw_base',
    'pricing_agent_base'
);

-- Legacy v2 pricing IDs (in case they still exist)
DELETE FROM product.product_pricing
WHERE pricing_id IN (
    'pricing_gpt4_base',
    'pricing_minio_tier2',
    'pricing_ai_tokens_base',
    'pricing_gpt4o_mini_base',
    'pricing_claude35_sonnet_base'
);

-- v3 product IDs
DELETE FROM product.products
WHERE product_id IN (
    'claude-sonnet-4',
    'claude-opus-4',
    'claude-haiku-35',
    'gpt-4o',
    'gpt-4o-mini',
    'gemini-2-flash',
    'minio_storage',
    'api_gateway',
    'advanced_agent'
);

-- Legacy v2 product IDs
DELETE FROM product.products
WHERE product_id IN (
    'gpt-4',
    'claude-3-5-sonnet',
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
