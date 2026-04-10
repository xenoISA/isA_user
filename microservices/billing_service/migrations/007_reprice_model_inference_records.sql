-- Billing Service Migration: reprice model inference records from usage details
-- Version: 007
-- Date: 2026-04-09
-- Description: fixes legacy model_inference rows that were priced from
--              catalog base_price instead of the real per-token rates.

WITH repriced AS (
    SELECT
        br.id,
        COALESCE((br.billing_metadata->'usage_details'->>'input_tokens')::numeric, 0) AS input_tokens,
        COALESCE((br.billing_metadata->'usage_details'->>'output_tokens')::numeric, 0) AS output_tokens,
        COALESCE((p.metadata->>'input_cost_per_1k')::numeric, 0) AS input_cost_per_1k,
        COALESCE((p.metadata->>'output_cost_per_1k')::numeric, 0) AS output_cost_per_1k,
        COALESCE(br.usage_amount, 0) AS usage_amount
    FROM billing.billing_records br
    JOIN product.products p
      ON p.product_id = br.product_id
    WHERE br.service_type = 'model_inference'
      AND COALESCE(br.billing_metadata->>'charged_upstream', 'false') = 'true'
      AND COALESCE(br.billing_metadata->>'upstream_cost_usd', '') = ''
      AND br.billing_metadata ? 'usage_details'
      AND (
            p.metadata ? 'input_cost_per_1k'
         OR p.metadata ? 'output_cost_per_1k'
      )
), recalculated AS (
    SELECT
        id,
        ROUND(
            ((input_tokens / 1000.0) * input_cost_per_1k)
          + ((output_tokens / 1000.0) * output_cost_per_1k),
            8
        ) AS total_amount,
        usage_amount::numeric AS usage_amount
    FROM repriced
)
UPDATE billing.billing_records br
SET total_amount = recalculated.total_amount,
    unit_price = CASE
        WHEN recalculated.usage_amount > 0
            THEN ROUND(
                recalculated.total_amount / recalculated.usage_amount,
                8
            )
        ELSE 0
    END,
    currency = 'USD',
    billing_metadata = COALESCE(br.billing_metadata, '{}'::jsonb)
        || jsonb_build_object('upstream_cost_usd', recalculated.total_amount::text)
        || jsonb_build_object('repriced_by', '007_reprice_model_inference_records'),
    updated_at = NOW()
FROM recalculated
WHERE br.id = recalculated.id;
