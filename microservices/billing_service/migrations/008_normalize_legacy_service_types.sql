-- Billing Service Migration: normalize legacy service_type values
-- Version: 008
-- Date: 2026-04-09
-- Description: repairs older billing rows that were persisted before the
--              canonical service-type mapping was wired through the usage
--              event handlers. This keeps historical reporting aligned with
--              the current product catalog instead of leaving most rows under
--              service_type = 'other'.

WITH resolved_service_types AS (
    SELECT
        br.id,
        CASE
            WHEN p.product_type = 'model_inference' THEN 'model_inference'
            WHEN p.product_type = 'storage_minio' THEN 'storage_minio'
            WHEN p.product_type = 'mcp_service' THEN 'mcp_service'
            WHEN p.product_type = 'agent_runtime' THEN 'agent_runtime'
            WHEN p.product_type = 'api_gateway' THEN 'api_gateway'
            WHEN p.product_type = 'integration' AND p.product_id = 'nats_messaging' THEN 'nats_messaging'
            WHEN p.product_type = 'computation' AND p.product_id = 'python_repl_execution' THEN 'python_repl'
            WHEN p.product_type = 'computation' AND p.product_id = 'compute_general' THEN 'compute_general'
            WHEN p.product_type = 'api_service' THEN 'web_service'
            WHEN p.product_type = 'data_processing' AND p.product_id IN (
                'data_pipeline_run',
                'data_export',
                'data_etl_job',
                'data_query_execution'
            ) THEN 'data_pipeline'
            WHEN p.product_type = 'data_processing' THEN 'data_service'
            ELSE NULL
        END AS normalized_service_type
    FROM billing.billing_records br
    LEFT JOIN product.products p
        ON p.product_id = br.product_id
    WHERE br.service_type = 'other'
)
UPDATE billing.billing_records br
SET service_type = rst.normalized_service_type,
    billing_metadata = COALESCE(br.billing_metadata, '{}'::jsonb)
        || jsonb_build_object(
            'service_type_normalized_by',
            '008_normalize_legacy_service_types'
        ),
    updated_at = NOW()
FROM resolved_service_types rst
WHERE br.id = rst.id
  AND rst.normalized_service_type IS NOT NULL
  AND br.service_type = 'other';
