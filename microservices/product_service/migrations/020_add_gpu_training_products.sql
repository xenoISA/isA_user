-- Product Service Migration: Add GPU training products
-- Version: 020
-- Date: 2026-04-11
-- Description: Seed invoiceable products for local GPU training and fine-tuning workloads.

INSERT INTO product.products (
    product_id, product_name, product_code, description,
    category, product_type, base_price, currency, billing_interval,
    features, quota_limits, is_active, metadata,
    product_kind, fulfillment_type, inventory_policy, requires_shipping, tax_category
) VALUES
('gpu_training_job', 'GPU Training Job', 'GPU-TRAINING-JOB',
 'Generic local GPU training runtime billed by elapsed seconds',
 'compute', 'computation', 0.0030, 'USD', 'per_second',
 '["gpu_training", "runtime_billed", "local_gpu"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "gpu_training",
    "operation_type": "gpu_training",
    "unit": "second",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "gpu_seconds",
      "cost_components": [
        {
          "component_id": "gpu_training_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_seconds",
          "unit_type": "second"
        },
        {
          "component_id": "gpu_training_allocation",
          "component_type": "compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_count",
          "unit_type": "count"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpu_training_lightning_grpo', 'Lightning GRPO Training', 'GPU-TRAINING-LIGHTNING-GRPO',
 'Local GPU Lightning GRPO training billed by elapsed seconds',
 'compute', 'computation', 0.0040, 'USD', 'per_second',
 '["gpu_training", "lightning", "grpo", "local_gpu"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "gpu_training",
    "operation_type": "lightning_grpo",
    "unit": "second",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "gpu_seconds",
      "cost_components": [
        {
          "component_id": "gpu_training_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_seconds",
          "unit_type": "second"
        },
        {
          "component_id": "gpu_training_allocation",
          "component_type": "compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_count",
          "unit_type": "count"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpu_training_finetune_lora', 'Fine-tune LoRA Training', 'GPU-TRAINING-FINETUNE-LORA',
 'Local GPU LoRA fine-tuning billed by elapsed seconds',
 'compute', 'computation', 0.0032, 'USD', 'per_second',
 '["gpu_training", "finetune", "lora", "local_gpu"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "gpu_training",
    "operation_type": "finetune_lora",
    "unit": "second",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "gpu_seconds",
      "cost_components": [
        {
          "component_id": "gpu_training_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_seconds",
          "unit_type": "second"
        },
        {
          "component_id": "gpu_training_allocation",
          "component_type": "compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_count",
          "unit_type": "count"
        }
      ]
    }
 }'::jsonb,
 'digital', 'digital', 'infinite', FALSE, 'digital_goods'),

('gpu_training_finetune_qlora', 'Fine-tune QLoRA Training', 'GPU-TRAINING-FINETUNE-QLORA',
 'Local GPU QLoRA fine-tuning billed by elapsed seconds',
 'compute', 'computation', 0.0028, 'USD', 'per_second',
 '["gpu_training", "finetune", "qlora", "local_gpu"]'::jsonb,
 '{"free_tier_seconds": 0}'::jsonb,
 TRUE,
 '{
    "provider": "internal",
    "service_type": "gpu_training",
    "operation_type": "finetune_qlora",
    "unit": "second",
    "billing_profile": {
      "billing_surface": "abstract_service",
      "invoiceable": true,
      "primary_meter": "gpu_seconds",
      "cost_components": [
        {
          "component_id": "gpu_training_runtime",
          "component_type": "runtime",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_seconds",
          "unit_type": "second"
        },
        {
          "component_id": "gpu_training_allocation",
          "component_type": "compute",
          "bundled": true,
          "customer_visible": false,
          "provider": "internal",
          "meter_type": "gpu_count",
          "unit_type": "count"
        }
      ]
    }
 }'::jsonb,
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
('pricing_gpu_training_job_default', 'gpu_training_job', 'default', 0, NULL, 0.0030, 'USD',
 '{"unit": "second", "billing_type": "usage_based", "service_type": "gpu_training"}'::jsonb),
('pricing_gpu_training_lightning_grpo_default', 'gpu_training_lightning_grpo', 'default', 0, NULL, 0.0040, 'USD',
 '{"unit": "second", "billing_type": "usage_based", "service_type": "gpu_training"}'::jsonb),
('pricing_gpu_training_finetune_lora_default', 'gpu_training_finetune_lora', 'default', 0, NULL, 0.0032, 'USD',
 '{"unit": "second", "billing_type": "usage_based", "service_type": "gpu_training"}'::jsonb),
('pricing_gpu_training_finetune_qlora_default', 'gpu_training_finetune_qlora', 'default', 0, NULL, 0.0028, 'USD',
 '{"unit": "second", "billing_type": "usage_based", "service_type": "gpu_training"}'::jsonb)
ON CONFLICT (pricing_id) DO UPDATE SET
    product_id = EXCLUDED.product_id,
    tier_name = EXCLUDED.tier_name,
    min_quantity = EXCLUDED.min_quantity,
    max_quantity = EXCLUDED.max_quantity,
    unit_price = EXCLUDED.unit_price,
    currency = EXCLUDED.currency,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
