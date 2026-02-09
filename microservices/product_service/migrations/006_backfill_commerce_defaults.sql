-- Product Service Migration: Backfill commerce defaults
-- Version: 006
-- Date: 2026-02-02
-- Description: Ensure legacy products have default commerce fields

UPDATE product.products
SET
    product_kind = COALESCE(product_kind, 'digital'),
    fulfillment_type = COALESCE(fulfillment_type, 'digital'),
    inventory_policy = COALESCE(inventory_policy, 'infinite'),
    requires_shipping = COALESCE(requires_shipping, false),
    tax_category = COALESCE(tax_category, 'digital_goods')
WHERE product_kind IS NULL
   OR fulfillment_type IS NULL
   OR inventory_policy IS NULL
   OR tax_category IS NULL;
