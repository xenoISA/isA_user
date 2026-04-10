-- Product Service Migration: Add web crawl usage product
-- Version: 011
-- Date: 2026-04-09
-- Description: Seed a canonical SKU for crawl and web-read style content extraction.
-- Idempotent: Safe to run multiple times via INSERT ... ON CONFLICT ... DO UPDATE.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES (
    'web_crawl', 'Web Crawl', 'WEB-CRAWL',
    'Single-page or batched web crawl content extraction through isA_OS web_service',
    'web_services', 'api_service', 0.0040, 'USD', 'per_url',
    '["crawl", "extract", "content"]'::jsonb,
    '{"free_tier_urls": 250}'::jsonb,
    TRUE,
    '{"provider": "internal", "service_type": "web_service", "operation_type": "crawl", "unit": "url"}'::jsonb,
    'digital', 'digital', 'infinite', FALSE, 'digital_goods'
)
ON CONFLICT (product_id) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    product_code = EXCLUDED.product_code,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    product_type = EXCLUDED.product_type,
    base_price = EXCLUDED.base_price,
    billing_interval = EXCLUDED.billing_interval,
    features = EXCLUDED.features,
    quota_limits = EXCLUDED.quota_limits,
    is_active = EXCLUDED.is_active,
    metadata = EXCLUDED.metadata,
    product_kind = EXCLUDED.product_kind,
    fulfillment_type = EXCLUDED.fulfillment_type,
    inventory_policy = EXCLUDED.inventory_policy,
    requires_shipping = EXCLUDED.requires_shipping,
    tax_category = EXCLUDED.tax_category,
    updated_at = NOW();

INSERT INTO product.product_pricing (
    pricing_id, product_id, tier_name,
    min_quantity, max_quantity,
    unit_price, currency, metadata
) VALUES (
    'pricing_web_crawl_default', 'web_crawl', 'default', 0, NULL, 0.0040, 'USD',
    '{"unit": "url", "billing_type": "usage_based"}'::jsonb
)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
