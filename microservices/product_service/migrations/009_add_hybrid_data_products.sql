-- Product Service Migration: Add hybrid digital and data query products
-- Version: 009
-- Date: 2026-04-09
-- Description: Seed billable SKUs for digital knowledge storage/search/RAG and
--              the catalog and data fabric hybrid query endpoints in isA_Data.
-- Idempotent: Safe to run multiple times via INSERT ... ON CONFLICT ... DO UPDATE.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('digital_knowledge_store', 'Digital Knowledge Store', 'DATA-DIGITAL-STORE',
 'Store digital knowledge assets in the hybrid knowledge service',
 'data_products', 'data_processing', 0.0100, 'USD', 'per_request',
 '["data", "digital", "knowledge-store"]'::jsonb,
 '{"free_tier_requests": 100}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "data_service", "operation_type": "digital_knowledge_store", "unit": "request"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('digital_knowledge_search', 'Digital Knowledge Search', 'DATA-DIGITAL-SEARCH',
 'Hybrid digital knowledge search request in isA_Data',
 'data_products', 'data_processing', 0.0060, 'USD', 'per_request',
 '["data", "digital", "search", "hybrid"]'::jsonb,
 '{"free_tier_requests": 250}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "data_service", "operation_type": "digital_knowledge_search", "unit": "request"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('digital_rag_response', 'Digital RAG Response', 'DATA-DIGITAL-RAG',
 'RAG response generation against digital knowledge assets',
 'data_products', 'data_processing', 0.0120, 'USD', 'per_request',
 '["data", "digital", "rag", "response"]'::jsonb,
 '{"free_tier_requests": 100}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "data_service", "operation_type": "digital_rag_response", "unit": "request"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('data_catalog_search', 'Data Catalog Search', 'DATA-CATALOG-SEARCH',
 'Hybrid semantic and metadata catalog search request',
 'data_products', 'data_processing', 0.0040, 'USD', 'per_request',
 '["data", "catalog", "search", "hybrid"]'::jsonb,
 '{"free_tier_requests": 500}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "data_service", "operation_type": "data_catalog_search", "unit": "request"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('data_fabric_query', 'Data Fabric Query', 'DATA-FABRIC-QUERY',
 'Natural-language hybrid query execution through the data fabric',
 'data_products', 'data_processing', 0.0150, 'USD', 'per_request',
 '["data", "fabric", "query", "hybrid"]'::jsonb,
 '{"free_tier_requests": 100}'::jsonb,
 TRUE,
 '{"provider": "internal", "service_type": "data_service", "operation_type": "data_fabric_query", "unit": "request"}'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods')
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
) VALUES
('pricing_digital_knowledge_store_default', 'digital_knowledge_store', 'default', 0, NULL, 0.0100, 'USD',
 '{"unit": "request", "billing_type": "usage_based"}'::jsonb),
('pricing_digital_knowledge_search_default', 'digital_knowledge_search', 'default', 0, NULL, 0.0060, 'USD',
 '{"unit": "request", "billing_type": "usage_based"}'::jsonb),
('pricing_digital_rag_response_default', 'digital_rag_response', 'default', 0, NULL, 0.0120, 'USD',
 '{"unit": "request", "billing_type": "usage_based"}'::jsonb),
('pricing_data_catalog_search_default', 'data_catalog_search', 'default', 0, NULL, 0.0040, 'USD',
 '{"unit": "request", "billing_type": "usage_based"}'::jsonb),
('pricing_data_fabric_query_default', 'data_fabric_query', 'default', 0, NULL, 0.0150, 'USD',
 '{"unit": "request", "billing_type": "usage_based"}'::jsonb)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
