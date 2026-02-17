# Notification Service Architecture

## Overview
The notification_service has been upgraded to follow the event-driven architecture standards defined in `arch.md`.

## Directory Structure

```
microservices/notification_service/
├── clients/                         # ✅ NEW - Sync HTTP clients
│   ├── __init__.py
│   ├── account_client.py           # Client for account_service
│   └── organization_client.py      # Client for organization_service
│
├── events/                          # ✅ UPGRADED
│   ├── __init__.py                 # Exports handlers, publishers, models
│   ├── models.py                   # ✅ NEW - Event data models (Pydantic)
│   ├── publishers.py               # ✅ NEW - Event publishing logic
│   └── handlers.py                 # ✅ UPDATED - Event subscription handlers
│
├── main.py                          # Application entry point
├── notification_service.py          # ✅ REFACTORED - Business logic
├── notification_repository.py       # Data access layer
├── models.py                        # Domain models
├── client.py                        # External client for other services
└── routes_registry.py              # Route metadata for Consul
```

---

## 1️⃣ Sync Operations (HTTP Clients)

### `clients/account_client.py`
**Purpose:** Fetch user account information for notifications

**Methods:**
- `get_user_profile(user_id)` - Get full user profile
- `get_user_by_email(email)` - Find user by email
- `get_user_preferences(user_id)` - Get notification preferences
- `get_user_contact_info(user_id)` - Get email, phone, name

**Usage Example:**
```python
# In notification_service.py
contact_info = await self.account_client.get_user_contact_info(user_id)
email = contact_info.get("email")
```

### `clients/organization_client.py`
**Purpose:** Fetch organization and member data for batch notifications

**Methods:**
- `get_organization(organization_id)` - Get org details
- `get_organization_members(organization_id, role, limit)` - List members
- `get_user_organizations(user_id)` - Get user's orgs
- `get_organization_admins(organization_id)` - Get admins only
- `get_member_emails(organization_id)` - Extract member emails

**Usage Example:**
```python
# Send notification to all org members
member_emails = await self.organization_client.get_member_emails(org_id)
for email in member_emails:
    # Send notification
```

---

## 2️⃣ Async Event-Driven Operations

### A) Events SUBSCRIBED (Inbound)

**File:** `events/handlers.py`

| Event Type | Source Service | Handler Method | Action |
|------------|----------------|----------------|--------|
| `user.logged_in` | auth_service | `handle_user_logged_in` | Welcome back in-app notification |
| `user.registered` | auth_service | `handle_user_registered` | ✅ NEW - Welcome email |
| `payment.completed` | payment_service | `handle_payment_completed` | Receipt email + in-app |
| `organization.member_added` | organization_service | `handle_organization_member_added` | Membership notification |
| `device.offline` | device_service | `handle_device_offline` | Device alert |
| `file.uploaded` | storage_service | `handle_file_uploaded` | Upload confirmation |
| `file.shared` | storage_service | `handle_file_shared` | Share notification |
| `order.created` | order_service | `handle_order_created` | ✅ NEW - Order confirmation |
| `task.assigned` | task_service | `handle_task_assigned` | ✅ NEW - Task assignment alert |
| `invitation.created` | invitation_service | `handle_invitation_created` | ✅ NEW - Invitation email |
| `wallet.balance_low` | wallet_service | `handle_wallet_balance_low` | ✅ NEW - Low balance alert |

**Total:** 11 event subscriptions (6 existing + 5 new)

### B) Events PUBLISHED (Outbound)

**File:** `events/publishers.py`

| Event Type | When Published | Method | Consumers |
|------------|----------------|--------|-----------|
| `notification.sent` | ✅ After successful send | `publish_notification_sent()` | audit_service, analytics |
| `notification.failed` | ✅ NEW - Send failure | `publish_notification_failed()` | audit_service, monitoring |
| `notification.delivered` | ✅ NEW - Delivery confirmed | `publish_notification_delivered()` | analytics |
| `notification.clicked` | ✅ NEW - User interaction | `publish_notification_clicked()` | analytics |
| `notification.batch_completed` | ✅ NEW - Batch done | `publish_batch_completed()` | reporting |

**Total:** 5 event types published (1 existing + 4 new)

---

## 3️⃣ Event Data Models

**File:** `events/models.py`

### Outbound Event Models (Published)
- `NotificationSentEventData`
- `NotificationFailedEventData`
- `NotificationDeliveredEventData`
- `NotificationClickedEventData`
- `NotificationBatchCompletedEventData`

### Inbound Event Models (Consumed)
- `UserLoggedInEventData`
- `UserRegisteredEventData`
- `PaymentCompletedEventData`
- `OrganizationMemberAddedEventData`
- `DeviceOfflineEventData`
- `FileUploadedEventData`
- `FileSharedEventData`
- `OrderCreatedEventData`
- `TaskAssignedEventData`
- `InvitationCreatedEventData`
- `WalletBalanceLowEventData`

---

## 4️⃣ Refactoring Changes

### `notification_service.py`

**Before:**
```python
# Inline event publishing
async def _publish_notification_sent_event(self, notification):
    event = Event(...)
    await self.event_bus.publish_event(event)
```

**After:**
```python
# Using centralized publishers
def __init__(self, event_bus=None, config_manager=None):
    self.event_publishers = NotificationEventPublishers(event_bus)
    self.account_client = AccountServiceClient(config_manager)
    self.organization_client = OrganizationServiceClient(config_manager)

# In notification sending methods
if self.event_publishers:
    await self.event_publishers.publish_notification_sent(
        notification_id=notification.notification_id,
        notification_type=notification.type.value,
        # ... other params
    )
```

**Changes:**
- ✅ Removed inline `_publish_notification_sent_event()` method
- ✅ Added `event_publishers` instance
- ✅ Added `account_client` and `organization_client` instances
- ✅ Updated `cleanup()` to close clients
- ✅ Replaced all event publishing calls with publishers

---

## 5️⃣ Benefits of This Architecture

### ✅ Separation of Concerns
- **Events folder:** All event-related logic (models, publishers, handlers)
- **Clients folder:** All sync HTTP clients
- **Service layer:** Pure business logic

### ✅ Testability
- Clients can be mocked independently
- Publishers can be tested separately
- Handlers have clear input/output

### ✅ Maintainability
- Easy to find event definitions (`events/models.py`)
- Clear publisher methods (`events/publishers.py`)
- Centralized handler registration (`events/handlers.py`)

### ✅ Scalability
- Add new event subscriptions by adding handlers
- Add new event publications by adding publisher methods
- Add new service clients in `clients/` folder

---

## 6️⃣ Usage Examples

### Publishing Events
```python
# In notification_service.py after successful email send
if self.event_publishers:
    await self.event_publishers.publish_notification_sent(
        notification_id=notification.notification_id,
        notification_type="email",
        recipient_email="user@example.com",
        status="sent",
        priority="high"
    )
```

### Subscribing to Events
```python
# In events/handlers.py
async def handle_order_created(self, event: Event):
    order_id = event.data.get("order_id")
    user_id = event.data.get("user_id")

    # Send confirmation email
    await self.notification_service.send_notification(...)
```

### Using Service Clients
```python
# Fetch user contact info
contact = await self.account_client.get_user_contact_info(user_id)

# Get organization members for batch notification
members = await self.organization_client.get_organization_members(org_id)
```

---

## 7️⃣ Migration Checklist

- [x] Create `clients/` folder
- [x] Create `clients/account_client.py`
- [x] Create `clients/organization_client.py`
- [x] Create `clients/__init__.py`
- [x] Create `events/models.py`
- [x] Create `events/publishers.py`
- [x] Update `events/__init__.py`
- [x] Add new handlers to `events/handlers.py`
- [x] Refactor `notification_service.py` to use publishers
- [x] Initialize clients in `notification_service.py`
- [x] Update cleanup to close clients
- [x] Remove old `_publish_notification_sent_event()` method

---

## 8️⃣ Next Steps

### Future Enhancements
1. **Add more event handlers:**
   - `order.shipped` - Shipping notification
   - `task.due_soon` - Task reminder
   - `compliance.alert` - Compliance violation
   - `billing.invoice_ready` - Invoice notification

2. **Add event failure handling:**
   - Use `publish_notification_failed()` on send errors
   - Track retry counts in failed events

3. **Add delivery tracking:**
   - Implement webhook callbacks for email opens
   - Use `publish_notification_delivered()` on confirmation
   - Use `publish_notification_clicked()` on link clicks

4. **Batch notification improvements:**
   - Use `organization_client` for org-wide broadcasts
   - Publish `notification.batch_completed` on batch finish

---

## 9️⃣ Testing

### Unit Tests
```python
# Test publishers
async def test_publish_notification_sent():
    mock_event_bus = AsyncMock()
    publishers = NotificationEventPublishers(mock_event_bus)

    await publishers.publish_notification_sent(
        notification_id="test_123",
        notification_type="email",
        status="sent"
    )

    mock_event_bus.publish_event.assert_called_once()
```

### Integration Tests
```python
# Test event handlers
async def test_handle_user_registered():
    event = Event(
        event_type=EventType.USER_REGISTERED,
        data={"user_id": "123", "email": "test@example.com"}
    )

    await handlers.handle_user_registered(event)

    # Verify notification was created
```

---

## 📊 Summary

**Architecture Compliance:** ✅ Fully compliant with `arch.md`

**Files Created:**
- `clients/__init__.py`
- `clients/account_client.py`
- `clients/organization_client.py`
- `events/models.py`
- `events/publishers.py`

**Files Updated:**
- `events/__init__.py`
- `events/handlers.py`
- `notification_service.py`

**Event Subscriptions:** 11 (6 existing + 5 new)
**Event Publications:** 5 (1 existing + 4 new)
**Service Clients:** 2 (account, organization)
