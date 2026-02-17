# Notification Service Domain Model

## Core Domain Concepts

### 1. Notification

A **Notification** represents a message that needs to be delivered to one or more recipients through various channels.

#### Core Attributes
- **Identity**: Unique notification_id, type, priority
- **Content**: Subject, body (text and HTML), metadata
- **Recipient**: User ID, email address, phone number
- **Delivery**: Status, timestamps, retry information
- **Configuration**: Template references, variables, scheduling

#### Business Rules
- Every notification must have at least one valid recipient
- Notifications can be scheduled for future delivery
- Failed notifications can be retried up to a maximum limit
- High-priority notifications are processed before normal priority
- Notifications can be part of a batch campaign

### 2. Notification Template

A **Notification Template** is a reusable message format with placeholder variables for dynamic content.

#### Core Attributes
- **Identity**: Unique template_id, name, type
- **Content**: Subject, body (text and HTML), variable definitions
- **Metadata**: Description, category, creation information
- **Lifecycle**: Status, version, activation/deactivation

#### Business Rules
- Templates must have unique names within their type
- Variables follow the pattern `{{variable_name}}`
- Templates can be in draft, active, or archived status
- Content changes increment the version number
- Only active templates can be used for notifications

### 3. Push Subscription

A **Push Subscription** represents a device's registration to receive push notifications.

#### Core Attributes
- **Identity**: Unique subscription_id, user association
- **Device Information**: Platform, token, device details
- **Configuration**: Topics, preferences, activation status
- **Lifecycle**: Registration time, last used, expiration

#### Business Rules
- Each user can have multiple device subscriptions
- Device tokens must be unique per platform per user
- Failed subscriptions are automatically deactivated
- Web push requires additional cryptographic keys
- Subscriptions can expire after a period of inactivity

### 4. Batch Campaign

A **Batch Campaign** represents a coordinated notification sent to multiple recipients using the same template.

#### Core Attributes
- **Identity**: Unique batch_id, name, description
- **Configuration**: Template, recipients, scheduling
- **Tracking**: Progress counters, status information
- **Metadata**: Campaign information, creator details

#### Business Rules
- Batches support 1 to 10,000 recipients
- All recipients use the same template
- Batches can be scheduled for future processing
- Progress is tracked in real-time
- Failed recipients don't stop the batch processing

## Aggregates and Entities

### 1. Notification Aggregate

```python
class Notification:
    """Root entity of the notification aggregate"""
    
    def __init__(self, notification_id: str, type: NotificationType):
        self.notification_id = notification_id
        self.type = type
        self.status = NotificationStatus.PENDING
        self.priority = NotificationPriority.NORMAL
        self.recipients = []
        self.template_id = None
        self.content = None
        self.variables = {}
        self.scheduled_at = None
        self.retry_count = 0
        self.max_retries = 3
        self.metadata = {}
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def schedule_for(self, scheduled_at: datetime) -> None:
        """Schedule notification for future delivery"""
        if scheduled_at <= datetime.now(timezone.utc):
            raise ValueError("Scheduled time must be in the future")
        self.scheduled_at = scheduled_at
        self.updated_at = datetime.now(timezone.utc)
    
    def add_recipient(self, recipient: NotificationRecipient) -> None:
        """Add a recipient to this notification"""
        if not recipient.is_valid():
            raise ValueError("Invalid recipient")
        self.recipients.append(recipient)
        self.updated_at = datetime.now(timezone.utc)
    
    def use_template(self, template_id: str, variables: dict) -> None:
        """Associate notification with a template and variables"""
        self.template_id = template_id
        self.variables = variables
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_sent(self) -> None:
        """Mark notification as sent to provider"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_delivered(self) -> None:
        """Mark notification as delivered to recipient"""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_failed(self, error_message: str) -> None:
        """Mark notification as failed"""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def can_retry(self) -> bool:
        """Check if notification can be retried"""
        return (self.status == NotificationStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def is_ready_to_send(self) -> bool:
        """Check if notification is ready for immediate sending"""
        return (self.status == NotificationStatus.PENDING and 
                (self.scheduled_at is None or 
                 self.scheduled_at <= datetime.now(timezone.utc)))

class NotificationRecipient:
    """Value object representing a notification recipient"""
    
    def __init__(self, recipient_type: str, value: str, user_id: str = None):
        self.type = recipient_type  # email, phone, user_id, push
        self.value = value
        self.user_id = user_id
    
    def is_valid(self) -> bool:
        """Validate recipient format"""
        if self.type == "email":
            return self._is_valid_email(self.value)
        elif self.type == "phone":
            return self._is_valid_phone(self.value)
        elif self.type == "user_id":
            return bool(self.value and len(self.value) > 0)
        elif self.type == "push":
            return bool(self.value and len(self.value) > 0)
        return False
    
    def _is_valid_email(self, email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _is_valid_phone(self, phone: str) -> bool:
        import re
        pattern = r'^\+?[1-9]\d{1,14}$'
        return re.match(pattern, phone) is not None
```

### 2. Template Aggregate

```python
class NotificationTemplate:
    """Root entity of the template aggregate"""
    
    def __init__(self, template_id: str, name: str, type: TemplateType):
        self.template_id = template_id
        self.name = name
        self.type = type
        self.subject = None
        self.content = ""
        self.html_content = None
        self.variables = []
        self.status = TemplateStatus.DRAFT
        self.version = 1
        self.description = None
        self.metadata = {}
        self.created_by = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def set_content(self, subject: str = None, content: str = None, 
                   html_content: str = None) -> None:
        """Set template content and extract variables"""
        if content:
            self.content = content
            self.variables = self._extract_variables(content)
        
        if subject:
            self.subject = subject
            subject_vars = self._extract_variables(subject)
            self.variables.extend([v for v in subject_vars if v not in self.variables])
        
        if html_content:
            self.html_content = html_content
            html_vars = self._extract_variables(html_content)
            self.variables.extend([v for v in html_vars if v not in self.variables])
        
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate template for use"""
        if self.status == TemplateStatus.ARCHIVED:
            raise ValueError("Cannot activate archived template")
        self.status = TemplateStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate template (temporarily)"""
        self.status = TemplateStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def archive(self) -> None:
        """Archive template (permanently)"""
        self.status = TemplateStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)
    
    def render(self, variables: dict) -> RenderedTemplate:
        """Render template with provided variables"""
        if self.status != TemplateStatus.ACTIVE:
            raise ValueError("Cannot render inactive template")
        
        context = TemplateContext(variables)
        rendered_subject = self._replace_variables(self.subject or "", context)
        rendered_content = self._replace_variables(self.content, context)
        rendered_html = self._replace_variables(self.html_content, context)
        
        return RenderedTemplate(
            subject=rendered_subject,
            content=rendered_content,
            html_content=rendered_html,
            variables_used=context.get_used_variables()
        )
    
    def _extract_variables(self, text: str) -> List[str]:
        """Extract {{variable}} patterns from text"""
        if not text:
            return []
        
        import re
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, text)
        return list(set(matches))  # Remove duplicates
    
    def _replace_variables(self, text: str, context: TemplateContext) -> str:
        """Replace variables in text with context values"""
        if not text:
            return ""
        
        import re
        def replace_match(match):
            var_name = match.group(1)
            context.mark_used(var_name)
            return str(context.get_variable(var_name, ""))
        
        pattern = r'\{\{(\w+)\}\}'
        return re.sub(pattern, replace_match, text)

class RenderedTemplate:
    """Value object representing rendered template content"""
    
    def __init__(self, subject: str, content: str, html_content: str = None,
                 variables_used: List[str] = None):
        self.subject = subject
        self.content = content
        self.html_content = html_content
        self.variables_used = variables_used or []
    
    def is_empty(self) -> bool:
        """Check if rendered content is empty"""
        return not any([self.subject, self.content, self.html_content])

class TemplateContext:
    """Helper class for template variable replacement"""
    
    def __init__(self, variables: dict):
        self.variables = variables or {}
        self.used_variables = set()
    
    def get_variable(self, name: str, default: str = "") -> str:
        """Get variable value with default"""
        return str(self.variables.get(name, default))
    
    def mark_used(self, name: str) -> None:
        """Mark variable as used"""
        self.used_variables.add(name)
    
    def get_used_variables(self) -> List[str]:
        """Get list of used variables"""
        return list(self.used_variables)
```

### 3. Push Subscription Aggregate

```python
class PushSubscription:
    """Root entity of the push subscription aggregate"""
    
    def __init__(self, subscription_id: str, user_id: str, platform: PushPlatform,
                 device_token: str):
        self.subscription_id = subscription_id
        self.user_id = user_id
        self.platform = platform
        self.device_token = device_token
        self.device_id = None
        self.device_name = None
        self.device_model = None
        self.app_version = None
        self.os_version = None
        self.endpoint = None  # For web push
        self.auth_key = None   # For web push
        self.p256dh_key = None # For web push
        self.topics = []
        self.is_active = True
        self.last_used_at = None
        self.expires_at = None
        self.failure_count = 0
        self.metadata = {}
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def set_device_info(self, device_name: str = None, device_model: str = None,
                      app_version: str = None, os_version: str = None) -> None:
        """Set device information"""
        self.device_name = device_name
        self.device_model = device_model
        self.app_version = app_version
        self.os_version = os_version
        self.updated_at = datetime.now(timezone.utc)
    
    def set_web_push_keys(self, endpoint: str, auth_key: str, p256dh_key: str) -> None:
        """Set web push cryptographic keys"""
        if self.platform != PushPlatform.WEB:
            raise ValueError("Web push keys only applicable to web platform")
        self.endpoint = endpoint
        self.auth_key = auth_key
        self.p256dh_key = p256dh_key
        self.updated_at = datetime.now(timezone.utc)
    
    def add_topic(self, topic: str) -> None:
        """Add subscription topic"""
        if topic not in self.topics:
            self.topics.append(topic)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_topic(self, topic: str) -> None:
        """Remove subscription topic"""
        if topic in self.topics:
            self.topics.remove(topic)
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_used(self) -> None:
        """Mark subscription as recently used"""
        self.last_used_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_failure(self) -> None:
        """Increment failure count"""
        self.failure_count += 1
        self.updated_at = datetime.now(timezone.utc)
        
        # Auto-deactivate after 3 failures
        if self.failure_count >= 3:
            self.is_active = False
    
    def reset_failures(self) -> None:
        """Reset failure count (successful delivery)"""
        self.failure_count = 0
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if subscription is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_receive_notifications(self) -> bool:
        """Check if subscription can receive notifications"""
        return (self.is_active and 
                not self.is_expired() and 
                self.failure_count < 3)
```

## Domain Services

### 1. Notification Delivery Service

```python
class NotificationDeliveryService:
    """Domain service for notification delivery logic"""
    
    def __init__(self, email_provider, push_provider, sms_provider, webhook_provider):
        self.email_provider = email_provider
        self.push_provider = push_provider
        self.sms_provider = sms_provider
        self.webhook_provider = webhook_provider
    
    async def deliver_notification(self, notification: Notification) -> DeliveryResult:
        """Deliver notification through appropriate channel"""
        try:
            if notification.type == NotificationType.EMAIL:
                return await self._deliver_email(notification)
            elif notification.type == NotificationType.PUSH:
                return await self._deliver_push(notification)
            elif notification.type == NotificationType.SMS:
                return await self._deliver_sms(notification)
            elif notification.type == NotificationType.WEBHOOK:
                return await self._deliver_webhook(notification)
            elif notification.type == NotificationType.IN_APP:
                return await self._deliver_in_app(notification)
            else:
                raise ValueError(f"Unsupported notification type: {notification.type}")
        except Exception as e:
            return DeliveryResult(
                success=False,
                error_message=str(e),
                retryable=self._is_retryable_error(e)
            )
    
    async def _deliver_email(self, notification: Notification) -> DeliveryResult:
        """Deliver email notification"""
        recipient = self._get_email_recipient(notification)
        if not recipient:
            return DeliveryResult(
                success=False,
                error_message="No valid email recipient found"
            )
        
        email_request = EmailRequest(
            to=recipient.value,
            subject=notification.subject,
            content=notification.content,
            html_content=notification.html_content,
            from_email=notification.metadata.get('from_email'),
            reply_to=notification.metadata.get('reply_to')
        )
        
        return await self.email_provider.send_email(email_request)
    
    async def _deliver_push(self, notification: Notification) -> DeliveryResult:
        """Deliver push notification"""
        user_id = notification.recipients[0].user_id
        if not user_id:
            return DeliveryResult(
                success=False,
                error_message="User ID required for push notifications"
            )
        
        # Get active subscriptions for user
        subscriptions = await self._get_user_subscriptions(user_id)
        if not subscriptions:
            return DeliveryResult(
                success=False,
                error_message="No active push subscriptions found for user"
            )
        
        push_payload = PushPayload(
            title=notification.subject or "Notification",
            body=notification.content,
            data=notification.metadata.get('push_data', {}),
            priority=self._map_priority(notification.priority)
        )
        
        results = []
        for subscription in subscriptions:
            result = await self.push_provider.send_push(
                subscription.device_token, push_payload, subscription.platform
            )
            results.append(result)
        
        # Mark successful subscriptions as used
        for subscription, result in zip(subscriptions, results):
            if result.success:
                subscription.mark_used()
                subscription.reset_failures()
            else:
                subscription.increment_failure()
        
        # Consider successful if at least one delivery succeeds
        success_count = sum(1 for r in results if r.success)
        return DeliveryResult(
            success=success_count > 0,
            delivered_count=success_count,
            total_count=len(results),
            error_message=None if success_count > 0 else "All push deliveries failed"
        )
    
    def _map_priority(self, priority: NotificationPriority) -> str:
        """Map domain priority to provider priority"""
        mapping = {
            NotificationPriority.LOW: "normal",
            NotificationPriority.NORMAL: "normal",
            NotificationPriority.HIGH: "high",
            NotificationPriority.URGENT: "high"
        }
        return mapping.get(priority, "normal")
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error is retryable"""
        non_retryable_patterns = [
            "invalid email",
            "email not found",
            "unsubscribed",
            "bounced",
            "invalid phone"
        ]
        error_msg = str(error).lower()
        return not any(pattern in error_msg for pattern in non_retryable_patterns)

class DeliveryResult:
    """Value object representing delivery result"""
    
    def __init__(self, success: bool, error_message: str = None,
                 delivered_count: int = None, total_count: int = None,
                 retryable: bool = True):
        self.success = success
        self.error_message = error_message
        self.delivered_count = delivered_count
        self.total_count = total_count
        self.retryable = retryable
```

### 2. Template Rendering Service

```python
class TemplateRenderingService:
    """Domain service for advanced template rendering"""
    
    def render_with_validation(self, template: NotificationTemplate, 
                           variables: dict) -> RenderedTemplate:
        """Render template with validation"""
        # Validate required variables
        missing_vars = self._find_missing_variables(template, variables)
        if missing_vars:
            raise TemplateValidationError(
                f"Missing required variables: {', '.join(missing_vars)}"
            )
        
        # Render template
        rendered = template.render(variables)
        
        # Validate rendered content
        if rendered.is_empty():
            raise TemplateValidationError("Rendered content is empty")
        
        return rendered
    
    def preview_template(self, template: NotificationTemplate,
                       sample_variables: dict = None) -> RenderedTemplate:
        """Preview template with sample data"""
        if not sample_variables:
            sample_variables = self._generate_sample_variables(template.variables)
        
        return template.render(sample_variables)
    
    def validate_template_syntax(self, content: str) -> ValidationResult:
        """Validate template syntax without rendering"""
        try:
            variables = self._extract_variables(content)
            # Check for malformed patterns
            malformed = self._find_malformed_patterns(content)
            if malformed:
                return ValidationResult(
                    valid=False,
                    errors=[f"Malformed variable pattern: {pattern}" 
                            for pattern in malformed]
                )
            
            return ValidationResult(valid=True, variables_found=variables)
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])
    
    def _find_missing_variables(self, template: NotificationTemplate,
                              provided_variables: dict) -> List[str]:
        """Find template variables not provided in context"""
        return [var for var in template.variables 
                if var not in provided_variables]
    
    def _generate_sample_variables(self, variables: List[str]) -> dict:
        """Generate sample variable values for preview"""
        samples = {}
        for var in variables:
            if var == "name":
                samples[var] = "John Doe"
            elif var == "email":
                samples[var] = "john.doe@example.com"
            elif var == "company":
                samples[var] = "Example Company"
            elif var == "date":
                samples[var] = datetime.now().strftime("%Y-%m-%d")
            else:
                samples[var] = f"[{var.upper()}]"
        return samples

class TemplateValidationError(Exception):
    """Exception raised for template validation errors"""
    pass

class ValidationResult:
    """Value object for validation results"""
    
    def __init__(self, valid: bool, errors: List[str] = None,
                 variables_found: List[str] = None):
        self.valid = valid
        self.errors = errors or []
        self.variables_found = variables_found or []
```

## Value Objects and Enums

### Notification Types

```python
from enum import Enum

class NotificationType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"

class NotificationStatus(Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    CANCELLED = "cancelled"

class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class TemplateStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class PushPlatform(Enum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"

class TemplateType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
```

### Value Objects

```python
class NotificationPriority:
    """Value object for notification priority with ordering"""
    
    LEVELS = {
        NotificationPriority.LOW: 1,
        NotificationPriority.NORMAL: 2,
        NotificationPriority.HIGH: 3,
        NotificationPriority.URGENT: 4
    }
    
    def __init__(self, priority: NotificationPriority):
        self.priority = priority
        self.level = self.LEVELS[priority]
    
    def is_higher_than(self, other: 'NotificationPriority') -> bool:
        """Check if this priority is higher than another"""
        return self.level > other.level
    
    def is_equal_or_higher_than(self, other: 'NotificationPriority') -> bool:
        """Check if this priority is equal or higher than another"""
        return self.level >= other.level

class DeliveryChannel:
    """Value object representing delivery channel configuration"""
    
    def __init__(self, channel_type: str, is_primary: bool = True,
                 retry_config: dict = None):
        self.channel_type = channel_type
        self.is_primary = is_primary
        self.retry_config = retry_config or {
            "max_attempts": 3,
            "backoff_factor": 2,
            "initial_delay": 60
        }
    
    def should_retry(self, attempt: int, error_type: str) -> bool:
        """Determine if delivery should be retried"""
        if attempt >= self.retry_config["max_attempts"]:
            return False
        
        # Don't retry certain error types
        non_retryable_errors = ["invalid_recipient", "unsubscribed", "bounced"]
        if error_type in non_retryable_errors:
            return False
        
        return True
    
    def get_retry_delay(self, attempt: int) -> int:
        """Calculate retry delay based on attempt number"""
        base_delay = self.retry_config["initial_delay"]
        factor = self.retry_config["backoff_factor"]
        return base_delay * (factor ** (attempt - 1))

class RecipientAddress:
    """Value object for validated recipient addresses"""
    
    def __init__(self, address_type: str, address: str, user_id: str = None):
        self.type = address_type
        self.address = address
        self.user_id = user_id
        self.is_valid = self._validate_address()
    
    def _validate_address(self) -> bool:
        """Validate address format based on type"""
        if self.type == "email":
            return self._validate_email(self.address)
        elif self.type == "phone":
            return self._validate_phone(self.address)
        elif self.type in ["user_id", "push"]:
            return bool(self.address and len(self.address.strip()) > 0)
        return False
    
    def _validate_email(self, email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_phone(self, phone: str) -> bool:
        import re
        pattern = r'^\+?[1-9]\d{1,14}$'
        return re.match(pattern, phone) is not None
```

## Domain Events

### Notification Events

```python
class DomainEvent:
    """Base class for domain events"""
    
    def __init__(self, event_id: str, timestamp: datetime = None):
        self.event_id = event_id
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.event_type = self.__class__.__name__

class NotificationCreated(DomainEvent):
    """Event raised when a notification is created"""
    
    def __init__(self, event_id: str, notification: Notification):
        super().__init__(event_id)
        self.notification_id = notification.notification_id
        self.type = notification.type
        self.recipients = [r.value for r in notification.recipients]
        self.template_id = notification.template_id
        self.priority = notification.priority.value
        self.scheduled_at = notification.scheduled_at

class NotificationSent(DomainEvent):
    """Event raised when a notification is sent to provider"""
    
    def __init__(self, event_id: str, notification: Notification, 
                 delivery_result: DeliveryResult):
        super().__init__(event_id)
        self.notification_id = notification.notification_id
        self.type = notification.type
        self.recipients = [r.value for r in notification.recipients]
        self.sent_at = notification.sent_at
        self.delivery_result = delivery_result

class NotificationDelivered(DomainEvent):
    """Event raised when notification is delivered to recipient"""
    
    def __init__(self, event_id: str, notification: Notification):
        super().__init__(event_id)
        self.notification_id = notification.notification_id
        self.type = notification.type
        self.delivered_at = notification.delivered_at

class NotificationFailed(DomainEvent):
    """Event raised when notification delivery fails"""
    
    def __init__(self, event_id: str, notification: Notification, 
                 error_message: str, retryable: bool):
        super().__init__(event_id)
        self.notification_id = notification.notification_id
        self.type = notification.type
        self.error_message = error_message
        self.retryable = retryable
        self.retry_count = notification.retry_count
        self.failed_at = datetime.now(timezone.utc)

class TemplateCreated(DomainEvent):
    """Event raised when a template is created"""
    
    def __init__(self, event_id: str, template: NotificationTemplate):
        super().__init__(event_id)
        self.template_id = template.template_id
        self.name = template.name
        self.type = template.type.value
        self.variables = template.variables
        self.created_by = template.created_by

class TemplateActivated(DomainEvent):
    """Event raised when a template is activated"""
    
    def __init__(self, event_id: str, template: NotificationTemplate):
        super().__init__(event_id)
        self.template_id = template.template_id
        self.name = template.name
        self.type = template.type.value
        self.version = template.version

class PushSubscriptionRegistered(DomainEvent):
    """Event raised when push subscription is registered"""
    
    def __init__(self, event_id: str, subscription: PushSubscription):
        super().__init__(event_id)
        self.subscription_id = subscription.subscription_id
        self.user_id = subscription.user_id
        self.platform = subscription.platform.value
        self.device_name = subscription.device_name
        self.device_token = subscription.device_token

class PushSubscriptionDeactivated(DomainEvent):
    """Event raised when push subscription is deactivated"""
    
    def __init__(self, event_id: str, subscription: PushSubscription,
                 reason: str):
        super().__init__(event_id)
        self.subscription_id = subscription.subscription_id
        self.user_id = subscription.user_id
        self.platform = subscription.platform.value
        self.reason = reason
        self.failure_count = subscription.failure_count
```

## Repository Interfaces

### Domain Repository Contracts

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class NotificationRepository(ABC):
    """Repository interface for notifications"""
    
    @abstractmethod
    async def save(self, notification: Notification) -> None:
        """Save notification to repository"""
        pass
    
    @abstractmethod
    async def find_by_id(self, notification_id: str) -> Optional[Notification]:
        """Find notification by ID"""
        pass
    
    @abstractmethod
    async def find_pending_notifications(self, limit: int = 100) -> List[Notification]:
        """Find notifications pending delivery"""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: str, limit: int = 50,
                           offset: int = 0) -> List[Notification]:
        """Find notifications for specific user"""
        pass
    
    @abstractmethod
    async def update_status(self, notification_id: str, 
                          status: NotificationStatus) -> None:
        """Update notification status"""
        pass

class TemplateRepository(ABC):
    """Repository interface for templates"""
    
    @abstractmethod
    async def save(self, template: NotificationTemplate) -> None:
        """Save template to repository"""
        pass
    
    @abstractmethod
    async def find_by_id(self, template_id: str) -> Optional[NotificationTemplate]:
        """Find template by ID"""
        pass
    
    @abstractmethod
    async def find_by_type_and_name(self, type: TemplateType, 
                                 name: str) -> Optional[NotificationTemplate]:
        """Find template by type and name"""
        pass
    
    @abstractmethod
    async def find_active_by_type(self, type: TemplateType) -> List[NotificationTemplate]:
        """Find all active templates of specific type"""
        pass
    
    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[NotificationTemplate]:
        """Find all templates"""
        pass

class PushSubscriptionRepository(ABC):
    """Repository interface for push subscriptions"""
    
    @abstractmethod
    async def save(self, subscription: PushSubscription) -> None:
        """Save subscription to repository"""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> List[PushSubscription]:
        """Find all subscriptions for user"""
        pass
    
    @abstractmethod
    async def find_active_by_user_id(self, user_id: str) -> List[PushSubscription]:
        """Find active subscriptions for user"""
        pass
    
    @abstractmethod
    async def find_by_token_and_platform(self, device_token: str, 
                                    platform: PushPlatform) -> Optional[PushSubscription]:
        """Find subscription by token and platform"""
        pass
    
    @abstractmethod
    async def update_status(self, subscription_id: str, 
                          is_active: bool) -> None:
        """Update subscription active status"""
        pass

class DomainEventRepository(ABC):
    """Repository interface for domain events"""
    
    @abstractmethod
    async def save_events(self, events: List[DomainEvent]) -> None:
        """Save domain events to repository"""
        pass
    
    @abstractmethod
    async def find_unpublished_events(self, limit: int = 100) -> List[DomainEvent]:
        """Find unpublished events"""
        pass
    
    @abstractmethod
    async def mark_as_published(self, event_ids: List[str]) -> None:
        """Mark events as published"""
        pass
```

## Domain Services Integration

### Event Publishing

```python
class DomainEventPublisher:
    """Service for publishing domain events"""
    
    def __init__(self, event_repository: DomainEventRepository,
                 message_bus):
        self.event_repository = event_repository
        self.message_bus = message_bus
    
    async def publish_events(self, aggregate_root) -> None:
        """Publish all domain events from aggregate"""
        events = aggregate_root.get_uncommitted_events()
        if not events:
            return
        
        # Save events to repository
        await self.event_repository.save_events(events)
        
        # Publish to message bus
        for event in events:
            await self._publish_event(event)
        
        # Mark events as published
        event_ids = [event.event_id for event in events]
        await self.event_repository.mark_as_published(event_ids)
        
        # Clear events from aggregate
        aggregate_root.clear_events()
    
    async def _publish_event(self, event: DomainEvent) -> None:
        """Publish individual event to message bus"""
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "source": "notification_service",
            "data": self._extract_event_data(event)
        }
        
        subject = f"notification.{event.event_type.lower()}"
        await self.message_bus.publish(subject, event_data)
    
    def _extract_event_data(self, event: DomainEvent) -> dict:
        """Extract event data based on event type"""
        if isinstance(event, NotificationCreated):
            return {
                "notification_id": event.notification_id,
                "type": event.type,
                "recipients": event.recipients,
                "template_id": event.template_id,
                "priority": event.priority
            }
        elif isinstance(event, TemplateCreated):
            return {
                "template_id": event.template_id,
                "name": event.name,
                "type": event.type,
                "variables": event.variables,
                "created_by": event.created_by
            }
        # Add more event types as needed
        return {}
```

---

**Version**: 1.0.0  
**Last Updated**: 2025-12-15  
**Author**: Notification Service Team
