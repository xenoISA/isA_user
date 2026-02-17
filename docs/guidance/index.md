# isA User

Enterprise microservices platform for user management, payments, and AI-powered capabilities.

## Overview

isA User is a production-ready platform with 31 specialized microservices:

| Category | Services | Description |
|----------|----------|-------------|
| **Identity** | Auth, Account, Session, Authorization | Authentication & access control |
| **Payments** | Payment, Wallet, Billing, Credit, Subscription | Financial operations |
| **Content** | Storage, Album, Media, Document | File & media management |
| **Social** | Organization, Invitation, Membership | Multi-tenant & sharing |
| **IoT** | Device, OTA, Telemetry | Device management |
| **Intelligence** | Memory | AI-powered cognitive memory |
| **Operations** | Audit, Compliance, Notification, Task | Platform operations |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL TRAFFIC                                    │
│                        (Port 80/443)                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APISIX GATEWAY                                      │
│                    (Service Discovery via Consul)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONSUL SERVICE REGISTRY                                │
│                       (Dynamic Routing)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                     31 MICROSERVICES (8201-8250)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TIER 1: CORE IDENTITY (8201-8210)                                    │   │
│  │ Auth │ Account │ Session │ Authorization │ Audit │ Notification     │   │
│  │ Payment │ Wallet │ Storage │ Order                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TIER 2: BUSINESS DOMAIN (8211-8230)                                  │   │
│  │ Task │ Organization │ Invitation │ Vault │ Product │ Billing        │   │
│  │ Calendar │ Weather │ Album │ Device │ OTA │ Media │ Memory          │   │
│  │ Location │ Telemetry │ Compliance │ Document │ Subscription │ Credit│   │
│  │ Event                                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TIER 3: EXTENDED (8250+)                                             │   │
│  │ Membership                                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                    gRPC INFRASTRUCTURE (50051-50070)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE & INFRASTRUCTURE                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │PostgreSQL│ │  Redis  │  │  Neo4j  │  │ Qdrant  │  │  MinIO  │          │
│  │ + pgvector│ │ (Cache) │  │ (Graph) │  │(Vector) │  │  (S3)   │          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                                    │
│  │  NATS   │  │  MQTT   │  │ DuckDB  │                                    │
│  │(Events) │  │  (IoT)  │  │(Analytics)│                                   │
│  └─────────┘  └─────────┘  └─────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Directory

### Tier 1: Core Identity & Operations

| Service | Port | Description |
|---------|------|-------------|
| auth_service | 8201 | JWT, API keys, device auth |
| account_service | 8202 | User profiles, settings |
| session_service | 8203 | Session tracking, context |
| authorization_service | 8204 | RBAC, permissions |
| audit_service | 8205 | Audit trails, compliance |
| notification_service | 8206 | Push, Email, SMS |
| payment_service | 8207 | Stripe, crypto, invoices |
| wallet_service | 8208 | Virtual wallets, credits |
| storage_service | 8209 | Files, photos, sharing |
| order_service | 8210 | Order processing |

### Tier 2: Business Domain

| Service | Port | Description |
|---------|------|-------------|
| task_service | 8211 | Background jobs |
| organization_service | 8212 | Multi-tenant, family sharing |
| invitation_service | 8213 | Invites, sharing links |
| vault_service | 8214 | Encrypted secrets |
| product_service | 8215 | Product catalog |
| billing_service | 8216 | Invoicing, usage billing |
| calendar_service | 8217 | Events, scheduling |
| weather_service | 8218 | Weather data |
| album_service | 8219 | Photo albums |
| device_service | 8220 | IoT device registry |
| ota_service | 8221 | Firmware updates |
| media_service | 8222 | Transcoding, thumbnails |
| memory_service | 8223 | AI cognitive memory |
| location_service | 8224 | Geospatial queries |
| telemetry_service | 8225 | Device telemetry |
| compliance_service | 8226 | GDPR, PCI DSS |
| document_service | 8227 | Document management |
| subscription_service | 8228 | Subscription lifecycle |
| credit_service | 8229 | Credit system |
| event_service | 8230 | Event sourcing |

### Tier 3: Extended

| Service | Port | Description |
|---------|------|-------------|
| membership_service | 8250 | Loyalty, tiers |

## Key Features

### Multi-Database Strategy

| Database | Purpose |
|----------|---------|
| PostgreSQL + pgvector | Relational data, embeddings |
| Redis | Cache, sessions, pub/sub |
| Neo4j | Social graphs, org hierarchies |
| Qdrant | Vector search, semantic memory |
| DuckDB | Analytics, OLAP |
| MinIO | S3-compatible object storage |

### Event-Driven Architecture

- NATS JetStream for reliable messaging
- Event sourcing with replay
- CQRS pattern support
- Async service communication

### Security & Compliance

- JWT + API key authentication
- Fine-grained RBAC
- GDPR & PCI DSS compliance
- Comprehensive audit logging
- Encrypted secrets vault

### AI-Powered Memory

The memory_service implements cognitive architecture:
- Episodic memory (experiences)
- Semantic memory (facts)
- Procedural memory (skills)
- Working memory (active context)

## Quality Metrics

| Metric | Status |
|--------|--------|
| Services | 31 total |
| Tests per service | 130+ average |
| Integration tests passing | 25/27 |
| Documentation coverage | 100% |

## Next Steps

- [Quick Start](./quickstart) - Get started
- [Authentication](./authentication) - Auth services
- [Payments](./payments) - Payment & billing
- [Commerce](./commerce) - Orders & products
- [Storage](./storage) - Files & media
- [Organizations](./organizations) - Multi-tenant
- [Devices](./devices) - IoT management
- [Memory](./memory) - AI cognitive memory
- [Operations](./operations) - Audit, notifications, tasks
- [Utilities](./utilities) - Calendar, weather, location
- [Security](./security) - Vault & secrets
- [Architecture](./architecture) - Infrastructure
