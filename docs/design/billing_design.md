# Billing Design

## Purpose

This document defines the canonical billing design for the `isA` platform.

It standardizes:

- who pays
- who triggered usage
- which agent executed the work
- what is billable
- how billable usage is transported
- which services own billing control-plane logic

The design applies across `isA_Model`, `isA_Agent`, `isA_MCP`, `isA_OS`, `isA_Data`, and `isA_user`.

## Core Principles

1. One usage event has exactly one payer.
2. A single event may still be visible in user, organization, and agent reporting.
3. Billing dimensions are separate from billable products.
4. Usage ingestion is event-driven over NATS.
5. Pricing, reservations, reporting, and administration remain API-driven control-plane operations.
6. Not every microservice is a product.
7. Not every internal infrastructure cost should appear on a customer invoice.
8. Runtime billing and downstream usage billing are explicit product decisions, not implicit side effects.

## Canonical Roles

### Payer

The payer is the billing account that owes money or credits for an event.

- `billing_account_type`: `user` or `organization`
- `billing_account_id`: concrete payer identifier

### Actor

The actor is the human user who initiated the action.

- `actor_user_id`

### Executor

The executor is the agent or service that performed the work.

- `agent_id`
- `source_service`

### Context

Context is used for attribution, reporting, audit, and budget controls.

- `organization_id`
- `project_id`
- `session_id`
- `request_id`

## Canonical Billing Rule

Every billable event must answer these questions independently:

- Who pays?
- Who triggered the work?
- What product was consumed?
- What meter is used?
- Which service emitted the event?

The same event must not be charged to both the user and the organization unless those are explicitly different billable items.

## Billing Strategies

The platform supports three explicit billing strategies for agentic workloads:

- `runtime_only`: bill the allocated runtime resource and treat downstream model/tool usage as internal cost
- `downstream_usage_only`: bill downstream token/tool/storage usage and do not create a separate runtime charge
- `runtime_plus_usage`: bill both runtime occupancy and downstream usage as separate line items

These strategies should be carried as runtime metadata when needed:

- `billing_usage_policy`

Recommended defaults:

- deployed agent service: `runtime_only`
- shared managed agent runtime: `runtime_only`
- customer-facing apps such as `isA_` and `isA_Mate`: `downstream_usage_only`

## Canonical Usage Event

Usage events are published to NATS with the canonical family:

`billing.usage.recorded.>`

Recommended subject shape:

`billing.usage.recorded.<source_service>[.<resource_name>]`

Examples:

- `billing.usage.recorded.inference.gpt-4o-mini`
- `billing.usage.recorded.mcp.web-search`
- `billing.usage.recorded.storage.upload`
- `billing.usage.recorded.data.pipeline-run`

The subject is for routing and operations. Billing identity comes from the payload, not from parsing the subject.

### Canonical Payload

Required fields:

- `event_type`
- `event_id`
- `schema_version`
- `billing_account_type`
- `billing_account_id`
- `user_id`
- `actor_user_id`
- `product_id`
- `usage_amount`
- `unit_type`

Recommended optional fields:

- `organization_id`
- `agent_id`
- `subscription_id`
- `service_type`
- `operation_type`
- `source_service`
- `resource_name`
- `meter_type`
- `session_id`
- `request_id`
- `usage_details`
- `billing_surface`
- `cost_components`
- `credits_used`
- `cost_usd`
- `credit_consumption_handled`
- `timestamp`

### Example

```json
{
  "event_type": "billing.usage.recorded",
  "event_id": "evt_123",
  "schema_version": "1.0",
  "billing_account_type": "organization",
  "billing_account_id": "org_123",
  "user_id": "usr_123",
  "actor_user_id": "usr_123",
  "organization_id": "org_123",
  "agent_id": "agt_456",
  "product_id": "tool:web-search",
  "service_type": "mcp_service",
  "operation_type": "tool_execution",
  "source_service": "isa_mcp",
  "resource_name": "web-search",
  "meter_type": "tool_calls",
  "usage_amount": 1,
  "unit_type": "execution",
  "billing_surface": "abstract_service",
  "cost_components": [
    {
      "component_id": "browser_api",
      "component_type": "external_api",
      "bundled": true,
      "customer_visible": false,
      "provider": "internal"
    }
  ],
  "request_id": "req_001",
  "usage_details": {
    "tool_name": "web-search"
  },
  "timestamp": "2026-04-09T10:00:00Z"
}
```

## Billing Dimensions vs Billable Products

These are different layers and must not be conflated.

### Billing Dimensions

Used for payer resolution, attribution, audit, and reporting:

- `billing_account_type`
- `billing_account_id`
- `actor_user_id`
- `organization_id`
- `agent_id`

### Billable Identity

Used for pricing and invoicing:

- `product_id`
- `service_type`
- `meter_type`
- `operation_type`

## Product Model

### Product

A customer-facing thing that can appear on an invoice.

Examples:

- `model:text-generation`
- `agent:runtime-dedicated`
- `agent:runtime-shared`
- `tool:web-search`
- `storage:object`
- `data:pipeline-run`

Products should be abstract services rather than raw vendor or infrastructure names.

Examples:

- `python_repl_execution`, not VM instance IDs
- `web_automation`, not browser vendor names
- `phone_verification`, not SMS provider names
- `model_inference`, not raw GPU node names

### Service Type

A technical producer category. This is not necessarily what the customer sees on the invoice.

Examples:

- `model_inference`
- `agent_execution`
- `mcp_service`
- `web_service`
- `storage_service`
- `data_pipeline`

### Meter Type

The commercial measurement used for pricing.

Examples:

- `input_tokens`
- `output_tokens`
- `tool_calls`
- `agent_minutes`
- `compute_seconds`
- `storage_gb_months`
- `bandwidth_gb`
- `execution_count`

### Operation Type

The concrete action that occurred.

Examples:

- `chat_completion`
- `embedding`
- `tool_execution`
- `browser_session`
- `python_execution`
- `object_upload`
- `vector_query`

## Customer Billing vs Internal Cost

The platform must separate customer-billable usage from internal cost components.

### Customer-Billable Usage

These are explicit products the customer understands and can control.

Examples:

- model inference
- dedicated agent runtime occupancy
- shared agent runtime occupancy
- browser automation
- Python execution
- storage
- data exports

### Internal Cost Components

These are cost inputs for margin analysis and capacity planning. They are not automatically invoice lines.

Examples:

- VM and container runtime
- model provider token cost
- browser automation API
- proxy and IP APIs
- phone and verification APIs
- captcha APIs
- storage backend capacity
- egress and network transit
- NATS
- Redis
- Postgres
- vector database infrastructure
- API gateway
- proxy pools
- VM orchestration

### External APIs Follow the Same Rule

External APIs are treated like internal infrastructure resources:

- they are fulfillment or cost components
- they usually do not appear as customer-facing invoice lines
- they may be exposed only when intentionally productized as add-ons

Examples:

- `web_automation` may bundle browser, proxy, phone, captcha, and model-provider cost
- `python_repl_execution` may bundle VM runtime, storage, and network cost
- `digital_rag_response` may bundle vector retrieval, storage, and model tokens

### Product Billing Profile

The product catalog should make this split explicit in product metadata.

Recommended product metadata shape:

- `billing_profile.billing_surface`
- `billing_profile.invoiceable`
- `billing_profile.primary_meter`
- `billing_profile.cost_components[]`

Recommended cost-component shape:

- `component_id`
- `component_type`
- `bundled`
- `customer_visible`
- `provider`
- `meter_type`
- `unit_type`
- `notes`

Canonical component types:

- `runtime`
- `token_compute`
- `storage`
- `network`
- `external_api`

## Platform Mapping

### `isA_Agent`

- Dedicated deployed agent: bill runtime occupancy from the runtime/deployment layer
- Shared managed agent: bill runtime occupancy from the pool/runtime layer at a cheaper SKU
- A2A is transport and attribution, not the primary billing boundary

### `isA_` and `isA_Mate`

- Do not bill per query or turn by default
- Bill model tokens through `isA_Model`
- Bill MCP/tool usage only for tools intentionally exposed as billable products
- Carry canonical payer/actor/org/agent context so downstream token/tool events are attributable

Internal cost components may be recorded in telemetry or cost accounting, but they should not appear as invoice lines unless intentionally sold as products.

## Service Ownership

### `isA_user/product_service`

Owns:

- product catalog
- meters
- price calculation
- entitlements
- included usage policy

### `isA_user/billing_service`

Owns:

- canonical usage event contract
- event ingestion from NATS
- billing ledger
- idempotent processing
- reporting and billing record retrieval

### `isA_user/subscription_service`

Owns:

- payer credits
- reservations
- quota state
- reconciliation

### Producers

These services publish canonical usage events:

- `isA_Model`
- `isA_Agent`
- `isA_MCP`
- `isA_OS`
- `isA_Data`
- `isA_user/storage_service`

Producers must not own the canonical billing ledger.

## Payer Resolution

Default rule:

1. If organization billing is enabled for the request context:
   - `billing_account_type = organization`
   - `billing_account_id = organization_id`
2. Otherwise:
   - `billing_account_type = user`
   - `billing_account_id = actor_user_id`

`agent_id` is attribution by default, not the payer.

## Platform Product Guidance

### Billable by Default

- `isA_Model`
  - text generation
  - embeddings
  - image, audio, video generation when exposed

- `isA_Agent`
  - agent execution
  - agent runtime minutes
  - agent seat or plan features if sold

- `isA_MCP`
  - bill only intentionally sold tools or tool classes

- `isA_OS`
  - browser automation
  - web search
  - Python REPL execution

- `isA_Data`
  - data products
  - pipeline runs
  - exports
  - premium queries or refresh jobs

- `isA_user`
  - storage
  - bandwidth or egress if intentionally sold

### Usually Internal Only

- NATS
- Redis
- internal gateway
- pool manager
- cloud orchestration
- generic background workers

## Producer Checklist

Every producer must:

1. publish `billing.usage.recorded` events to NATS
2. provide canonical payer fields
3. provide billable identity fields
4. include stable idempotency when available
5. avoid double charging

If the producer already performed reservation or credit consumption, it must set:

- `credit_consumption_handled = true`

In that case, `billing_service` records the event without consuming credits again.

## Consumer Rules

`billing_service` must:

1. subscribe to `billing.usage.recorded.>`
2. treat payload fields as the source of truth
3. not infer payer from `organization_id` alone when canonical payer fields exist
4. preserve user, organization, and agent attribution
5. ensure idempotent processing across replicas

## Migration Guidance

Legacy publishers that still emit `usage.recorded.*` should be migrated to the canonical schema.

Backward compatibility may exist temporarily in shared helpers, but the target state is:

- canonical event type: `billing.usage.recorded`
- canonical subject family: `billing.usage.recorded.>`
- canonical payer fields present on all new producers

## Current Implementation Direction

The target production architecture is:

- NATS for usage ingestion
- APIs for pricing, reservations, reporting, and admin control-plane operations
- one payer per event
- product- and meter-based billing
- reporting by payer, user, organization, and agent from the same ledger
