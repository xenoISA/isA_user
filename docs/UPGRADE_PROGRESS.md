## Payment & Order Service Upgrade Progress

**Date:** 2025-11-13
**Status:** 🔨 In Progress

---

### ✅ Completed

#### Analysis & Design
- [x] Analyzed payment_service and order_service business logic
- [x] Designed event flows (async communication)
- [x] Designed service dependencies (sync communication)
- [x] Created architecture design document: `docs/payment_order_service_architecture_design.md`

#### Product Service (Reference Implementation)
- [x] ✅ **FULLY COMPLETED** - Can be used as reference
- [x] Created `events/` folder (models.py, publishers.py, handlers.py)
- [x] Created `clients/` folder (account_client.py, organization_client.py)
- [x] Refactored product_service.py
- [x] Updated main.py
- [x] Documentation: `microservices/product_service/docs/ARCHITECTURE_UPGRADE.md`

#### Payment Service
- [x] Created `events/` folder structure
- [x] Created `events/__init__.py`
- [x] Created `events/models.py` (10 event models)
- [x] Created `events/publishers.py` (9 publisher functions)
- [x] Created `events/handlers.py` (6 event handlers + register function)

---

### 🔨 In Progress / Todo

#### Payment Service
- [ ] Create `clients/` folder
  - [ ] `clients/__init__.py`
  - [ ] `clients/account_client.py`
  - [ ] `clients/wallet_client.py`
  - [ ] `clients/billing_client.py`
  - [ ] `clients/product_client.py`
- [ ] Refactor `payment_service.py`
  - [ ] Import from `events.publishers`
  - [ ] Use publishers instead of direct event_bus.publish_event()
  - [ ] Change to dependency injection for clients
- [ ] Update `main.py`
  - [ ] Initialize service clients
  - [ ] Pass clients to PaymentService
  - [ ] Register event handlers
  - [ ] Add cleanup for clients

#### Order Service
- [ ] Create `events/` folder
  - [ ] `events/__init__.py`
  - [ ] `events/models.py` (8 event models)
  - [ ] `events/publishers.py` (5 publisher functions)
  - [ ] `events/handlers.py` ⚠️ **MIGRATE from main.py:67-108**
- [ ] Create `clients/` folder
  - [ ] `clients/__init__.py`
  - [ ] `clients/payment_client.py`
  - [ ] `clients/wallet_client.py`
  - [ ] `clients/account_client.py`
  - [ ] `clients/storage_client.py`
  - [ ] `clients/billing_client.py`
- [ ] Refactor `order_service.py`
  - [ ] Import from `events.publishers`
  - [ ] Use publishers instead of direct event_bus.publish_event()
  - [ ] Change to dependency injection for clients
- [ ] Refactor `main.py` ⚠️ **CRITICAL**
  - [ ] **REMOVE event handlers** (lines 67-108)
  - [ ] Initialize service clients
  - [ ] Pass clients to OrderService
  - [ ] Register event handlers from events/handlers.py
  - [ ] Add cleanup for clients

---

## 📋 Implementation Commands

### Payment Service - Remaining Work

```bash
# Create clients folder
cd /Users/xenodennis/Documents/Fun/isA_user/microservices/payment_service
mkdir -p clients

# Files to create:
# - clients/__init__.py
# - clients/account_client.py
# - clients/wallet_client.py
# - clients/billing_client.py
# - clients/product_client.py

# Then refactor:
# - payment_service.py (lines 32-33, 835-850, 863-878, 893-908, 919-933)
# - main.py (add client init, register handlers)
```

### Order Service - Full Implementation

```bash
# Create events and clients folders
cd /Users/xenodennis/Documents/Fun/isA_user/microservices/order_service
mkdir -p events clients

# Files to create:
# events/__init__.py
# events/models.py (8 models)
# events/publishers.py (5 publishers)
# events/handlers.py (8 handlers - MIGRATE from main.py!)
#
# clients/__init__.py
# clients/payment_client.py
# clients/wallet_client.py
# clients/account_client.py
# clients/storage_client.py
# clients/billing_client.py

# Then refactor:
# - order_service.py (lines 24-27, 121-138, 244-261, 324-342)
# - main.py (REMOVE lines 67-108, add client init, register handlers)
```

---

## 🎯 Key Decisions Made

### Events to Publish (Payment Service)
1. `payment.completed` ✅ (existing)
2. `payment.failed` ✅ (existing)
3. `payment.refunded` ⭐ (NEW - critical for refund flow)
4. `payment.intent.created` ⭐ (NEW)
5. `subscription.created` ✅ (existing)
6. `subscription.canceled` ✅ (existing)
7. `subscription.updated` ⭐ (NEW)
8. `invoice.created` ⭐ (NEW)
9. `invoice.paid` ⭐ (NEW)

### Events to Subscribe (Payment Service) - All NEW ⭐
1. `order.created` → Auto-create payment intent
2. `wallet.balance_changed` → Retry failed payments
3. `wallet.insufficient_funds` → Pause subscriptions
4. `subscription.usage_exceeded` → Generate overage invoice
5. `user.deleted` → Cancel subscriptions + refund
6. `user.upgraded` → Auto-upgrade subscription tier

### Events to Publish (Order Service)
1. `order.created` ✅ (existing)
2. `order.canceled` ✅ (existing)
3. `order.completed` ✅ (existing)
4. `order.updated` ⭐ (NEW)
5. `order.expired` ⭐ (NEW - critical)
6. `order.payment_pending` ⭐ (NEW)
7. `order.refunded` ⭐ (NEW)

### Events to Subscribe (Order Service)
1. `payment.completed` ✅ (exists in main.py - needs migration)
2. `payment.failed` ✅ (exists in main.py - needs migration)
3. `payment.refunded` ⭐ (NEW)
4. `wallet.credits_added` ⭐ (NEW)
5. `subscription.created` ⭐ (NEW)
6. `user.deleted` ⭐ (NEW)

---

## ⚠️ Critical Notes

### Order Service Main.py Issue
**Current Problem:**
```python
# main.py:67-108
async def handle_payment_completed(event: Event):  # ❌ Wrong location
    # Handler logic here...

async def handle_payment_failed(event: Event):    # ❌ Wrong location
    # Handler logic here...
```

**Should Be:**
```python
# events/handlers.py
async def handle_payment_completed(event_data, order_service):  # ✅ Correct
    # Handler logic here...

async def handle_payment_failed(event_data, order_service):    # ✅ Correct
    # Handler logic here...

# main.py
from .events.handlers import register_event_handlers
await register_event_handlers(event_bus, order_service)  # ✅ Correct
```

### Payment Service - Direct Client Import
**Current Problem:**
```python
# payment_service.py:32-33
from microservices.account_service.client import AccountServiceClient  # ❌
from microservices.wallet_service.client import WalletServiceClient    # ❌

# payment_service.py:55-56
self.account_client = AccountServiceClient()  # ❌ Direct initialization
self.wallet_client = WalletServiceClient()    # ❌ Direct initialization
```

**Should Be:**
```python
# payment_service.py
from .clients import AccountClient, WalletClient  # ✅

def __init__(
    self,
    repository,
    stripe_secret_key,
    event_bus=None,
    account_client=None,      # ✅ Dependency injection
    wallet_client=None,        # ✅ Dependency injection
    config=None
):
    self.account_client = account_client
    self.wallet_client = wallet_client
```

---

## 📚 Reference Files

### Completed Reference: Product Service
- `microservices/product_service/events/models.py` - Event models example
- `microservices/product_service/events/publishers.py` - Publishers example
- `microservices/product_service/events/handlers.py` - Handlers example
- `microservices/product_service/clients/account_client.py` - Client example
- `microservices/product_service/product_service.py` - Refactored business logic
- `microservices/product_service/main.py` - Refactored main file

### Design Documents
- `docs/payment_order_service_architecture_design.md` - Complete architecture
- `arch.md` - Event-driven architecture standard
- `microservices/product_service/docs/ARCHITECTURE_UPGRADE.md` - Upgrade guide

---

## 🚀 Next Steps

1. **Complete Payment Service clients/** (5 files)
2. **Refactor payment_service.py** (use publishers, dependency injection)
3. **Update payment_service main.py** (init clients, register handlers)
4. **Implement Order Service events/** (4 files - migrate handlers!)
5. **Implement Order Service clients/** (6 files)
6. **Refactor order_service.py** (use publishers, dependency injection)
7. **Refactor order_service main.py** (REMOVE handlers, init clients, register)
8. **Test both services**

---

## 💡 Quick Start Commands

```bash
# Check current status
ls -la microservices/payment_service/events/
ls -la microservices/payment_service/clients/
ls -la microservices/order_service/events/
ls -la microservices/order_service/clients/

# Syntax check
python3 -m py_compile microservices/payment_service/events/*.py
python3 -m py_compile microservices/order_service/events/*.py

# View architecture design
cat docs/payment_order_service_architecture_design.md
```

---

**Status Summary:**
- Product Service: ✅ 100% Complete
- Payment Service: 🔨 40% Complete (events done, clients + refactor pending)
- Order Service: 🔨 0% Complete (all pending, handler migration critical)
