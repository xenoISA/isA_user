# Invitation Service - Design Document

## Design Overview

**Service Name**: invitation_service
**Port**: 8213
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-19

### Design Principles
1. **Token-Based Security**: Cryptographically secure invitation tokens for acceptance
2. **Permission-First**: All write operations validate inviter permissions via Organization Service
3. **Event-Driven Synchronization**: Loose coupling via NATS events for lifecycle changes
4. **Atomic Operations**: Invitation acceptance atomically updates status and adds member
5. **Graceful Degradation**: Event failures don't block API operations
6. **Expiration by Design**: 7-day default expiration with resend capability

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Mobile Apps, Web Apps, Admin Dashboard, API Gateway)     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       │ X-User-Id header for authenticated routes
                       ↓
┌─────────────────────────────────────────────────────────────┐
│               Invitation Service (Port 8213)                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health, /info)                     │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  │  - Event subscriptions (org.deleted, user.deleted)    │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │       Service Layer (invitation_service.py)           │ │
│  │  - Business logic (token gen, expiration check)       │ │
│  │  - Permission validation via Organization Service     │ │
│  │  - Invitation CRUD orchestration                      │ │
│  │  - Acceptance workflow (status + member add)          │ │
│  │  - Event publishing coordination                      │ │
│  │  - Email notification trigger                         │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │     Repository Layer (invitation_repository.py)       │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - No business logic                                  │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Layer (events/publishers.py, handlers.py)  │ │
│  │  - NATS event bus integration                         │ │
│  │  - Event model construction                           │ │
│  │  - Async non-blocking publishing                      │ │
│  │  - Event subscription handlers                        │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        │               │               │               │
        ↓               ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌──────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │ │ Organization │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│ │   Service    │
│              │ │             │ │            │ │  (HTTP)      │
│  Schema:     │ │  Subjects:  │ │  Service:  │ │              │
│  invitation  │ │  invitation.│ │  invitation│ │  Endpoints:  │
│  Table:      │ │  sent       │ │  _service  │ │  - GET /org  │
│  organization│ │  accepted   │ │            │ │  - GET /memb │
│  _invitations│ │  expired    │ │  Health:   │ │  - POST /memb│
│              │ │  cancelled  │ │  /health   │ │              │
│  Indexes:    │ │             │ │            │ │  Port: 8212  │
│  - inv_id    │ │  Subscribed:│ │            │ │              │
│  - token     │ │  org.deleted│ │            │ │              │
│  - org_id    │ │  user.delete│ │            │ │              │
│  - email     │ │             │ │            │ │              │
└──────────────┘ └─────────────┘ └────────────┘ └──────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Invitation Service                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - Invitation│    │ - Invitation│    │ - Invitation │   │
│  │   Status    │    │   Service   │    │   Repository │   │
│  │ - Org Role  │    │             │    │              │   │
│  │ - Create    │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  │ - Accept    │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  │ - Response  │    │             │    │              │   │
│  │   Models    │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑          │
│         │                  │                    │          │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_invitation_service)     │  │
│  │  - Route Handlers (8 endpoints)                      │  │
│  │  - Exception Handlers (custom errors)                │  │
│  │  - Lifespan management (event bus, consul)           │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Event Publishers & Handlers              │  │
│  │  (events/publishers.py, events/handlers.py)          │  │
│  │  Publishers:                                         │  │
│  │  - publish_invitation_sent                           │  │
│  │  - publish_invitation_accepted                       │  │
│  │  - publish_invitation_expired                        │  │
│  │  - publish_invitation_cancelled                      │  │
│  │  Handlers:                                           │  │
│  │  - handle_organization_deleted                       │  │
│  │  - handle_user_deleted                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Client Layer (clients/)               │  │
│  │  - OrganizationClient (permission checks)            │  │
│  │  - AccountClient (email verification - future)       │  │
│  │  - InvitationServiceClient (for other services)      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Factory Pattern (Future)              │  │
│  │              (factory.py, protocols.py)               │  │
│  │  - create_invitation_service (production)            │  │
│  │  - InvitationRepositoryProtocol (interface)          │  │
│  │  - Enables dependency injection for tests            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (8 endpoints)
- Health checks and service info
- Service initialization (lifespan management)
- Consul registration with route metadata
- NATS event bus setup and subscriptions
- Exception handling

**Key Endpoints**:
```python
# Health & Info
GET /health                                    # Basic health check
GET /info                                      # Service capabilities
GET /api/v1/invitations/info                   # Service info (alias)

# Invitation Management
POST /api/v1/invitations/organizations/{org_id}  # Create invitation
GET  /api/v1/invitations/{invitation_token}      # Get by token (public)
POST /api/v1/invitations/accept                  # Accept invitation
GET  /api/v1/invitations/organizations/{org_id}  # List org invitations
DELETE /api/v1/invitations/{invitation_id}       # Cancel invitation
POST /api/v1/invitations/{invitation_id}/resend  # Resend invitation

# Admin Operations
POST /api/v1/invitations/admin/expire-invitations  # Bulk expire
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, invitation_service

    # Startup
    try:
        # Initialize event bus
        event_bus = await get_event_bus("invitation_service")
        logger.info("Event bus initialized successfully")

        # Initialize service with event bus
        invitation_service = InvitationService(event_bus=event_bus)
        logger.info("Invitation microservice initialized")

        # Set up event subscriptions
        if event_bus:
            invitation_repo = InvitationRepository()
            event_handler = InvitationEventHandler(invitation_repo)

            # Subscribe to organization.deleted events
            await event_bus.subscribe(
                subject="events.organization.deleted",
                callback=lambda msg: event_handler.handle_event(msg)
            )

            # Subscribe to user.deleted events
            await event_bus.subscribe(
                subject="events.user.deleted",
                callback=lambda msg: event_handler.handle_event(msg)
            )

        # Consul registration
        if config.consul_enabled:
            route_meta = get_routes_for_consul()
            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=config.service_port,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='http'
            )
            consul_registry.register()

        yield  # Service runs

    finally:
        # Shutdown
        if consul_registry:
            consul_registry.deregister()
        if event_bus:
            await event_bus.close()
        logger.info("Invitation microservice shutdown completed")
```

### 2. Service Layer (invitation_service.py)

**Class**: `InvitationService`

**Responsibilities**:
- Business logic execution
- Token generation (secrets.token_urlsafe)
- Expiration checking and management
- Permission validation via Organization Service
- Event publishing coordination
- Email sending orchestration
- Atomic acceptance workflow

**Key Methods**:
```python
class InvitationService:
    def __init__(self, event_bus=None):
        self.repository = InvitationRepository()
        self.invitation_base_url = "https://app.iapro.ai/accept-invitation"
        self.consul = None
        self.event_bus = event_bus
        self._init_consul()

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL via Consul discovery with fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        if self.consul:
            return self.consul.get_service_address(service_name, fallback_url=fallback_url)
        return fallback_url

    # ============ Core Operations ============

    async def create_invitation(
        self,
        organization_id: str,
        inviter_user_id: str,
        email: str,
        role: OrganizationRole,
        message: Optional[str] = None
    ) -> Tuple[bool, Optional[InvitationResponse], str]:
        """
        Create organization invitation.

        Steps:
        1. Verify organization exists
        2. Verify inviter has owner/admin role
        3. Check no pending invitation exists for email/org
        4. Check user not already a member
        5. Generate secure token
        6. Create invitation with 7-day expiration
        7. Send invitation email
        8. Publish invitation.sent event

        Returns: (success, invitation, message)
        """
        try:
            # Permission checks via Organization Service
            if not await self._verify_organization_exists(organization_id, inviter_user_id):
                return False, None, "Organization not found"

            if not await self._verify_inviter_permissions(organization_id, inviter_user_id):
                return False, None, "You don't have permission to invite users"

            # Duplicate check
            existing = await self.repository.get_pending_invitation_by_email_and_organization(
                email, organization_id
            )
            if existing:
                return False, None, "A pending invitation already exists"

            # Membership check
            if await self._check_user_membership(organization_id, email):
                return False, None, "User is already a member"

            # Create invitation (token generated in repository)
            invitation = await self.repository.create_invitation(
                organization_id=organization_id,
                email=email,
                role=role,
                invited_by=inviter_user_id
            )

            if not invitation:
                return False, None, "Failed to create invitation"

            # Send email (best effort)
            email_sent = await self._send_invitation_email(invitation, message)

            # Publish event
            await publish_invitation_sent(
                self.event_bus,
                invitation_id=invitation.invitation_id,
                organization_id=organization_id,
                email=email,
                role=role.value,
                invited_by=inviter_user_id,
                email_sent=email_sent
            )

            return True, invitation, "Invitation created successfully"

        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            return False, None, f"Failed to create invitation: {str(e)}"

    async def get_invitation_by_token(
        self,
        invitation_token: str
    ) -> Tuple[bool, Optional[InvitationDetailResponse], str]:
        """
        Get invitation details by token.

        Steps:
        1. Retrieve invitation by token
        2. Check status is PENDING
        3. Check expiration (update to EXPIRED if needed)
        4. Build detail response with org/inviter info

        Returns: (success, invitation_detail, message)
        """
        try:
            invitation_info = await self.repository.get_invitation_with_organization_info(
                invitation_token
            )
            if not invitation_info:
                return False, None, "Invitation not found"

            # Check status
            if invitation_info['status'] != InvitationStatus.PENDING.value:
                return False, None, f"Invitation is {invitation_info['status']}"

            # Check expiration
            expires_at_str = invitation_info.get('expires_at')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', ''))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)

                if expires_at < datetime.now(timezone.utc):
                    # Update status to expired
                    await self.repository.update_invitation(
                        invitation_info['invitation_id'],
                        {'status': InvitationStatus.EXPIRED.value}
                    )

                    # Publish expiration event
                    await publish_invitation_expired(
                        self.event_bus,
                        invitation_id=invitation_info['invitation_id'],
                        organization_id=invitation_info['organization_id'],
                        email=invitation_info['email'],
                        expired_at=expires_at.isoformat()
                    )

                    return False, None, "Invitation has expired"

            # Build response
            invitation_detail = InvitationDetailResponse(
                invitation_id=invitation_info['invitation_id'],
                organization_id=invitation_info['organization_id'],
                organization_name=invitation_info.get('organization_name', ''),
                organization_domain=invitation_info.get('organization_domain'),
                email=invitation_info['email'],
                role=OrganizationRole(invitation_info['role']),
                status=InvitationStatus(invitation_info['status']),
                inviter_name=invitation_info.get('inviter_name'),
                inviter_email=invitation_info.get('inviter_email'),
                expires_at=expires_at if expires_at_str else None,
                created_at=datetime.fromisoformat(invitation_info['created_at'])
            )

            return True, invitation_detail, "Invitation found"

        except Exception as e:
            logger.error(f"Error getting invitation by token: {e}")
            return False, None, f"Failed to get invitation: {str(e)}"

    async def accept_invitation(
        self,
        invitation_token: str,
        user_id: str
    ) -> Tuple[bool, Optional[AcceptInvitationResponse], str]:
        """
        Accept invitation and join organization.

        Steps:
        1. Get invitation by token (validates status/expiration)
        2. Verify user email matches invitation email
        3. Update invitation status to ACCEPTED
        4. Add user to organization via Organization Service
        5. If member addition fails, rollback invitation status
        6. Publish invitation.accepted event

        Returns: (success, accept_response, message)
        """
        try:
            # Get and validate invitation
            success, invitation_detail, message = await self.get_invitation_by_token(
                invitation_token
            )
            if not success:
                return False, None, message

            # Verify email match (best effort)
            if not await self._verify_user_email_match(user_id, invitation_detail.email):
                return False, None, "Email mismatch"

            # Accept invitation (update status)
            accept_success = await self.repository.accept_invitation(invitation_token)
            if not accept_success:
                return False, None, "Failed to accept invitation"

            # Get inviter for permission context
            invitation = await self.repository.get_invitation_by_token(invitation_token)
            inviter_user_id = invitation.invited_by if invitation else "system"

            # Add user to organization
            add_member_success = await self._add_user_to_organization(
                invitation_detail.organization_id,
                user_id,
                invitation_detail.role,
                inviter_user_id
            )

            if not add_member_success:
                # Rollback invitation status
                await self.repository.update_invitation(invitation_detail.invitation_id, {
                    'status': InvitationStatus.PENDING.value,
                    'accepted_at': None
                })
                return False, None, "Failed to add user to organization"

            # Build response
            accept_response = AcceptInvitationResponse(
                invitation_id=invitation_detail.invitation_id,
                organization_id=invitation_detail.organization_id,
                organization_name=invitation_detail.organization_name,
                user_id=user_id,
                role=invitation_detail.role,
                accepted_at=datetime.now(timezone.utc)
            )

            # Publish event
            await publish_invitation_accepted(
                self.event_bus,
                invitation_id=invitation_detail.invitation_id,
                organization_id=invitation_detail.organization_id,
                user_id=user_id,
                email=invitation_detail.email,
                role=invitation_detail.role.value,
                accepted_at=accept_response.accepted_at.isoformat()
            )

            return True, accept_response, "Invitation accepted successfully"

        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            return False, None, f"Failed to accept invitation: {str(e)}"

    async def cancel_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """Cancel pending invitation"""
        try:
            invitation = await self.repository.get_invitation_by_id(invitation_id)
            if not invitation:
                return False, "Invitation not found"

            # Check permission (inviter or org admin)
            if invitation.invited_by != user_id:
                if not await self._verify_inviter_permissions(
                    invitation.organization_id, user_id
                ):
                    return False, "You don't have permission to cancel this invitation"

            # Cancel
            success = await self.repository.cancel_invitation(invitation_id)

            if success:
                await publish_invitation_cancelled(
                    self.event_bus,
                    invitation_id=invitation_id,
                    organization_id=invitation.organization_id,
                    email=invitation.email,
                    cancelled_by=user_id
                )
                return True, "Invitation cancelled successfully"
            else:
                return False, "Failed to cancel invitation"

        except Exception as e:
            logger.error(f"Error cancelling invitation: {e}")
            return False, f"Failed to cancel invitation: {str(e)}"

    async def resend_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> Tuple[bool, str]:
        """Resend invitation with extended expiration"""
        try:
            invitation = await self.repository.get_invitation_by_id(invitation_id)
            if not invitation:
                return False, "Invitation not found"

            # Check permission
            if invitation.invited_by != user_id:
                if not await self._verify_inviter_permissions(
                    invitation.organization_id, user_id
                ):
                    return False, "You don't have permission to resend"

            # Check status
            if invitation.status != InvitationStatus.PENDING:
                return False, f"Cannot resend {invitation.status.value} invitation"

            # Extend expiration by 7 days
            new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            await self.repository.update_invitation(invitation_id, {
                'expires_at': new_expires_at.isoformat()
            })

            # Resend email
            email_sent = await self._send_invitation_email(invitation)

            message = "Invitation resent successfully"
            if not email_sent:
                message += " (but email sending failed)"

            return True, message

        except Exception as e:
            logger.error(f"Error resending invitation: {e}")
            return False, f"Failed to resend invitation: {str(e)}"

    # ============ Helper Methods ============

    async def _verify_organization_exists(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """Verify organization exists via Organization Service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('organization_service', 8212)}"
                    f"/api/v1/organizations/{organization_id}",
                    headers={"X-User-Id": user_id}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error verifying organization exists: {e}")
            return False

    async def _verify_inviter_permissions(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """Verify inviter has owner/admin role"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('organization_service', 8212)}"
                    f"/api/v1/organizations/{organization_id}/members",
                    headers={"X-User-Id": user_id}
                )
                if response.status_code != 200:
                    return False

                data = response.json()
                members = data.get('members', [])

                for member in members:
                    if member['user_id'] == user_id:
                        role = member.get('role', '').lower()
                        return role in ['owner', 'admin']

                return False
        except Exception as e:
            logger.error(f"Error verifying inviter permissions: {e}")
            return False

    async def _add_user_to_organization(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole,
        inviter_user_id: str
    ) -> bool:
        """Add user to organization via Organization Service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._get_service_url('organization_service', 8212)}"
                    f"/api/v1/organizations/{organization_id}/members",
                    headers={
                        "X-User-Id": inviter_user_id,
                        "Content-Type": "application/json"
                    },
                    json={
                        "user_id": user_id,
                        "role": role.value,
                        "permissions": []
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error adding user to organization: {e}")
            return False
```

**Custom Exceptions**:
```python
class InvitationServiceError(Exception):
    """Base exception for invitation service"""
    pass
```

### 3. Repository Layer (invitation_repository.py)

**Class**: `InvitationRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Token generation (secrets.token_urlsafe)
- Query construction (parameterized)
- Result parsing
- No business logic

**Key Methods**:
```python
class InvitationRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("invitation_service")

        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )

        self.db = AsyncPostgresClient(host=host, port=port, user_id="invitation_service")
        self.schema = "invitation"
        self.invitations_table = "organization_invitations"

    async def create_invitation(
        self,
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: str
    ) -> Optional[InvitationResponse]:
        """Create invitation with generated token and 7-day expiration"""
        try:
            invitation_id = str(uuid.uuid4())
            invitation_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.invitations_table} (
                    invitation_id, organization_id, email, role, invited_by,
                    invitation_token, status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
            '''

            params = [
                invitation_id, organization_id, email, role.value, invited_by,
                invitation_token, InvitationStatus.PENDING.value,
                expires_at, now, now
            ]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return InvitationResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating invitation: {e}", exc_info=True)
            return None

    async def get_invitation_by_token(
        self,
        invitation_token: str
    ) -> Optional[InvitationResponse]:
        """Get invitation by secure token"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.invitations_table}
                WHERE invitation_token = $1
            '''

            async with self.db:
                results = await self.db.query(query, [invitation_token], schema=self.schema)

            if results and len(results) > 0:
                return InvitationResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting invitation by token: {e}")
            return None

    async def accept_invitation(self, invitation_token: str) -> bool:
        """Accept invitation - update status to ACCEPTED"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, accepted_at = $2, updated_at = $3
                WHERE invitation_token = $4 AND status = $5
            '''

            params = [
                InvitationStatus.ACCEPTED.value,
                now, now,
                invitation_token,
                InvitationStatus.PENDING.value
            ]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            return False

    async def cancel_invitation(self, invitation_id: str) -> bool:
        """Cancel invitation - update status to CANCELLED"""
        return await self.update_invitation(invitation_id, {
            'status': InvitationStatus.CANCELLED.value
        })

    async def expire_old_invitations(self) -> int:
        """Bulk expire old pending invitations"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, updated_at = $2
                WHERE status = $3 AND expires_at < $4
            '''

            params = [
                InvitationStatus.EXPIRED.value,
                now,
                InvitationStatus.PENDING.value,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count if count is not None else 0

        except Exception as e:
            logger.error(f"Error expiring old invitations: {e}")
            return 0

    # ============ Event Handler Methods ============

    async def cancel_organization_invitations(self, organization_id: str) -> int:
        """Cancel all pending invitations for deleted organization"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = $2 AND status = $3
            '''

            async with self.db:
                count = await self.db.execute(
                    query,
                    [InvitationStatus.CANCELLED.value, organization_id,
                     InvitationStatus.PENDING.value],
                    schema=self.schema
                )

            logger.info(f"Cancelled {count} invitations for organization {organization_id}")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error cancelling organization invitations: {e}")
            return 0

    async def cancel_invitations_by_inviter(self, user_id: str) -> int:
        """Cancel all pending invitations sent by deleted user"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE invited_by = $2 AND status = $3
            '''

            async with self.db:
                count = await self.db.execute(
                    query,
                    [InvitationStatus.CANCELLED.value, user_id,
                     InvitationStatus.PENDING.value],
                    schema=self.schema
                )

            logger.info(f"Cancelled {count} invitations sent by user {user_id}")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error cancelling invitations by inviter: {e}")
            return 0
```

### 4. Event Handler Layer (events/handlers.py)

**Class**: `InvitationEventHandler`

**Responsibilities**:
- Handle incoming events from NATS
- Process organization.deleted events
- Process user.deleted events
- Cleanup orphaned invitations

```python
class InvitationEventHandler:
    """
    Handles events subscribed by Invitation Service

    Subscribes to:
    - organization.deleted: Cancel pending invitations for deleted org
    - user.deleted: Cancel invitations sent by deleted user
    """

    def __init__(self, invitation_repository):
        self.invitation_repo = invitation_repository

    async def handle_organization_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle organization.deleted event"""
        organization_id = event_data.get('organization_id')
        if not organization_id:
            logger.warning("organization.deleted event missing organization_id")
            return False

        cancelled_count = await self.invitation_repo.cancel_organization_invitations(
            organization_id
        )
        logger.info(f"Cancelled {cancelled_count} invitations for org {organization_id}")
        return True

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle user.deleted event"""
        user_id = event_data.get('user_id')
        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return False

        cancelled_count = await self.invitation_repo.cancel_invitations_by_inviter(user_id)
        logger.info(f"Cancelled {cancelled_count} invitations sent by user {user_id}")
        return True

    async def handle_event(self, event: Event) -> bool:
        """Route event to appropriate handler"""
        event_type = event.type

        if event_type == "organization.deleted":
            return await self.handle_organization_deleted(event.data)
        elif event_type == EventType.USER_DELETED.value:
            return await self.handle_user_deleted(event.data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return False

    def get_subscriptions(self) -> list:
        """Get list of event types this handler subscribes to"""
        return [
            "organization.deleted",
            EventType.USER_DELETED.value,
        ]
```

---

## Database Schema Design

### PostgreSQL Schema: `invitation`

#### Table: invitation.organization_invitations

```sql
-- Create invitation schema
CREATE SCHEMA IF NOT EXISTS invitation;

-- Create organization invitations table
CREATE TABLE IF NOT EXISTS invitation.organization_invitations (
    -- Primary Key
    invitation_id VARCHAR(50) PRIMARY KEY,

    -- Organization Reference
    organization_id VARCHAR(50) NOT NULL,

    -- Invitation Details
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    invited_by VARCHAR(50) NOT NULL,

    -- Token for acceptance (cryptographically secure)
    invitation_token VARCHAR(100) NOT NULL UNIQUE,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- Timestamps
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT invitation_role_check CHECK (
        role IN ('owner', 'admin', 'member', 'viewer', 'guest')
    ),
    CONSTRAINT invitation_status_check CHECK (
        status IN ('pending', 'accepted', 'expired', 'cancelled')
    )
);

-- Indexes for query performance
CREATE INDEX idx_invitations_organization
    ON invitation.organization_invitations(organization_id);
CREATE INDEX idx_invitations_email
    ON invitation.organization_invitations(email);
CREATE INDEX idx_invitations_token
    ON invitation.organization_invitations(invitation_token);
CREATE INDEX idx_invitations_status
    ON invitation.organization_invitations(status);
CREATE INDEX idx_invitations_invited_by
    ON invitation.organization_invitations(invited_by);
CREATE INDEX idx_invitations_expires_at
    ON invitation.organization_invitations(expires_at)
    WHERE status = 'pending';
CREATE INDEX idx_invitations_created_at
    ON invitation.organization_invitations(created_at DESC);

-- Unique constraint: one pending invitation per email/org
CREATE UNIQUE INDEX idx_invitations_unique_pending
    ON invitation.organization_invitations(organization_id, LOWER(email))
    WHERE status = 'pending';

-- Comments
COMMENT ON TABLE invitation.organization_invitations IS
    'Organization membership invitations with token-based acceptance';
COMMENT ON COLUMN invitation.organization_invitations.invitation_id IS
    'Unique invitation identifier (UUID)';
COMMENT ON COLUMN invitation.organization_invitations.organization_id IS
    'Target organization for membership';
COMMENT ON COLUMN invitation.organization_invitations.email IS
    'Email address of invited person';
COMMENT ON COLUMN invitation.organization_invitations.role IS
    'Role assigned upon acceptance (owner/admin/member/viewer/guest)';
COMMENT ON COLUMN invitation.organization_invitations.invited_by IS
    'User ID of inviter';
COMMENT ON COLUMN invitation.organization_invitations.invitation_token IS
    'Secure URL-safe token for acceptance (32 bytes)';
COMMENT ON COLUMN invitation.organization_invitations.status IS
    'Invitation status (pending/accepted/expired/cancelled)';
COMMENT ON COLUMN invitation.organization_invitations.expires_at IS
    'Expiration timestamp (default 7 days from creation)';
COMMENT ON COLUMN invitation.organization_invitations.accepted_at IS
    'When invitation was accepted (null if not accepted)';
```

### Index Strategy

1. **Primary Key** (`invitation_id`): Clustered index for fast lookups by ID
2. **Token Index** (`idx_invitations_token`): Unique B-tree for token-based lookups (acceptance flow)
3. **Organization Index** (`idx_invitations_organization`): List invitations per org
4. **Email Index** (`idx_invitations_email`): Find invitations by email
5. **Status Index** (`idx_invitations_status`): Filter by status
6. **Inviter Index** (`idx_invitations_invited_by`): Find invitations by inviter (for user.deleted)
7. **Expiration Index** (`idx_invitations_expires_at`): Bulk expiration query optimization
8. **Created Index** (`idx_invitations_created_at`): Sorting by creation date
9. **Unique Pending** (`idx_invitations_unique_pending`): Prevent duplicate pending invitations

### Status State Machine

```
                    ┌──────────────┐
                    │   PENDING    │
                    │   (initial)  │
                    └──────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌───────────┐
    │ ACCEPTED │   │ EXPIRED  │   │ CANCELLED │
    │ (final)  │   │ (final)  │   │  (final)  │
    └──────────┘   └──────────┘   └───────────┘

Valid Transitions:
- PENDING → ACCEPTED: User accepts invitation
- PENDING → EXPIRED: Time expires (7 days) or bulk job
- PENDING → CANCELLED: Admin/inviter cancels

Invalid Transitions (enforced by application):
- ACCEPTED → any: Already accepted
- EXPIRED → any: Already expired
- CANCELLED → any: Already cancelled
```

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
invitation.sent          # New invitation created
invitation.accepted      # Invitation accepted, member added
invitation.expired       # Invitation expired (on access)
invitation.cancelled     # Invitation cancelled
```

### Event Models (events/models.py)

```python
class InvitationSentEvent(BaseModel):
    """Event: invitation.sent"""
    invitation_id: str
    organization_id: str
    email: str
    role: str
    invited_by: str
    email_sent: bool
    timestamp: str
    metadata: Optional[Dict[str, Any]] = {}

class InvitationAcceptedEvent(BaseModel):
    """Event: invitation.accepted"""
    invitation_id: str
    organization_id: str
    user_id: str
    email: str
    role: str
    accepted_at: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = {}

class InvitationExpiredEvent(BaseModel):
    """Event: invitation.expired"""
    invitation_id: str
    organization_id: str
    email: str
    expired_at: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = {}

class InvitationCancelledEvent(BaseModel):
    """Event: invitation.cancelled"""
    invitation_id: str
    organization_id: str
    email: str
    cancelled_by: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = {}
```

### Event Subscriptions

| Event | Source | Handler |
|-------|--------|---------|
| `organization.deleted` | organization_service | `handle_organization_deleted()` |
| `user.deleted` | account_service | `handle_user_deleted()` |

### Event Flow Diagram

```
┌─────────────────┐
│   Org Admin     │ (Creates Invitation)
└────────┬────────┘
         │ POST /api/v1/invitations/organizations/{org_id}
         ↓
┌──────────────────────────┐
│   Invitation Service     │
│                          │
│  1. Verify Permissions   │───→ Organization Service (HTTP)
│  2. Check Duplicates     │───→ PostgreSQL
│  3. Generate Token       │     (secrets.token_urlsafe)
│  4. Create Invitation    │───→ PostgreSQL (INSERT)
│  5. Send Email           │───→ (Email Service - future)
│  6. Publish Event        │
└──────────────────────────┘
         │ Event: invitation.sent
         ↓
┌─────────────────────────┐
│      NATS Bus           │
│ Subject: invitation.sent│
└──────────┬──────────────┘
           │
           ├──→ Audit Service (log invitation)
           └──→ Analytics Service (track metrics)

┌─────────────────┐
│    Invitee      │ (Clicks Email Link)
└────────┬────────┘
         │ GET /api/v1/invitations/{token}
         ↓
┌──────────────────────────┐
│   Invitation Service     │
│                          │
│  1. Lookup by Token      │───→ PostgreSQL (SELECT)
│  2. Check Status/Expiry  │
│  3. Return Details       │
└──────────────────────────┘
         │
         ↓
┌─────────────────┐
│    Invitee      │ (Accepts Invitation)
└────────┬────────┘
         │ POST /api/v1/invitations/accept
         ↓
┌──────────────────────────┐
│   Invitation Service     │
│                          │
│  1. Validate Token       │───→ PostgreSQL
│  2. Update to ACCEPTED   │───→ PostgreSQL (UPDATE)
│  3. Add Member to Org    │───→ Organization Service (HTTP POST)
│  4. Publish Event        │
└──────────────────────────┘
         │ Event: invitation.accepted
         ↓
┌───────────────────────────┐
│        NATS Bus           │
│ Subject: invitation.accept│
└───────────┬───────────────┘
            │
            ├──→ Audit Service (log acceptance)
            ├──→ Analytics Service (track conversion)
            └──→ Notification Service (welcome email)
```

---

## Data Flow Diagrams

### 1. Create Invitation Flow

```
Org Admin requests: POST /api/v1/invitations/organizations/{org_id}
    │ Headers: X-User-Id: admin_123
    │ Body: {email: "new@example.com", role: "member"}
    ↓
┌─────────────────────────────────────────┐
│  InvitationService.create_invitation    │
│                                         │
│  Step 1: Verify Organization Exists     │
│    _verify_organization_exists()     ───┼──→ Organization Service
│                                     ←───┤    GET /api/v1/organizations/{id}
│    If 404 → Return error               │    Response: 200 OK
│                                         │
│  Step 2: Verify Inviter Permissions     │
│    _verify_inviter_permissions()     ───┼──→ Organization Service
│                                     ←───┤    GET /api/v1/organizations/{id}/members
│    Check role in ['owner', 'admin']    │    Response: {members: [...]}
│    If not admin → Return error         │
│                                         │
│  Step 3: Check No Duplicate Pending     │
│    repo.get_pending_invitation...   ────┼──→ PostgreSQL
│                                     ←───┤    SELECT WHERE email AND org AND status='pending'
│    If exists → Return error            │    Result: None (OK)
│                                         │
│  Step 4: Check Not Already Member       │
│    _check_user_membership()          ───┼──→ (Future: verify via org service)
│                                     ←───┤
│                                         │
│  Step 5: Create Invitation              │
│    repo.create_invitation()          ───┼──→ PostgreSQL
│      - Generate UUID                   │    INSERT INTO invitation.organization_invitations
│      - Generate token (32 bytes)       │    RETURNING *
│      - Set 7-day expiration        ←───┤    Result: InvitationResponse
│                                         │
│  Step 6: Send Email                     │
│    _send_invitation_email()          ───┼──→ (Email Service - logged only)
│    (Best effort, doesn't block)        │
│                                         │
│  Step 7: Publish Event                  │
│    publish_invitation_sent()         ───┼──→ NATS: invitation.sent
│                                         │    {invitation_id, org_id, email, role, invited_by}
└─────────────────────────────────────────┘
    │
    │ Return 201 Created
    │ {invitation_id, invitation_token, email, role, status, expires_at}
    ↓
Org Admin receives confirmation
```

### 2. Accept Invitation Flow

```
Invitee requests: POST /api/v1/invitations/accept
    │ Headers: X-User-Id: new_user_456
    │ Body: {invitation_token: "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG"}
    ↓
┌─────────────────────────────────────────┐
│  InvitationService.accept_invitation    │
│                                         │
│  Step 1: Get Invitation by Token        │
│    get_invitation_by_token()         ───┼──→ PostgreSQL
│      - Lookup by token                 │    SELECT * WHERE invitation_token = $1
│      - Check status == PENDING     ←───┤    Result: InvitationResponse
│      - Check not expired               │
│    If invalid → Return error           │
│                                         │
│  Step 2: Verify Email Match             │
│    _verify_user_email_match()        ───┼──→ (Future: Account Service)
│    (Best effort verification)          │
│                                         │
│  Step 3: Accept Invitation              │
│    repo.accept_invitation()          ───┼──→ PostgreSQL
│                                         │    UPDATE SET status='accepted', accepted_at=NOW()
│                                     ←───┤    WHERE invitation_token=$1 AND status='pending'
│                                         │
│  Step 4: Add User to Organization       │
│    _add_user_to_organization()       ───┼──→ Organization Service
│      - Use inviter's permission        │    POST /api/v1/organizations/{id}/members
│                                     ←───┤    Body: {user_id, role, permissions: []}
│    If failed → Rollback invitation     │    Response: 200 OK
│                                         │
│  Step 5: Publish Event                  │
│    publish_invitation_accepted()     ───┼──→ NATS: invitation.accepted
│                                         │    {invitation_id, org_id, user_id, email, role}
└─────────────────────────────────────────┘
    │
    │ Return 200 OK
    │ {invitation_id, organization_id, organization_name, user_id, role, accepted_at}
    ↓
Invitee is now organization member
```

### 3. Handle Organization Deleted Event

```
Organization Service publishes: organization.deleted
    │ {organization_id: "org_xyz789"}
    ↓
┌─────────────────────────────────────────┐
│        NATS Event Bus                    │
│  Subject: events.organization.deleted   │
└───────────────────┬─────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────┐
│  InvitationEventHandler.handle_event    │
│                                         │
│  Route to handler based on event_type   │
│  event_type == "organization.deleted"   │
│                                         │
│  handle_organization_deleted(event.data)│
│    organization_id = "org_xyz789"       │
│                                         │
│  Cancel pending invitations          ───┼──→ PostgreSQL
│    repo.cancel_organization_invitations │    UPDATE SET status='cancelled'
│                                     ←───┤    WHERE org_id=$1 AND status='pending'
│    Result: 5 invitations cancelled      │
│                                         │
│  Log: "Cancelled 5 invitations for org" │
│  Return: True (success)                 │
└─────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server
- **httpx**: Async HTTP client for cross-service calls
- **secrets**: Cryptographically secure token generation

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `invitation`
- **Table**: `organization_invitations`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Published Subjects**: `invitation.sent`, `invitation.accepted`, `invitation.expired`, `invitation.cancelled`
- **Subscribed Subjects**: `events.organization.deleted`, `events.user.deleted`

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration, capabilities

### Cross-Service Integration
- **Organization Service** (Port 8212): Permission validation, member management
- **Account Service** (Port 8201): Email verification (future)

### Observability
- **Structured Logging**: JSON format via core.logger
- **Health Endpoints**: `/health`, `/info`

---

## Security Considerations

### Token Security
- **Token Generation**: `secrets.token_urlsafe(32)` - 32 bytes of cryptographically random data
- **Token Storage**: Stored with UNIQUE constraint, indexed for fast lookup
- **Token Exposure**: Token only exposed in creation response and email link
- **Single Use**: Token cannot be reused after acceptance

### Permission Validation
- **Organization Verification**: Check organization exists before creating invitation
- **Role Verification**: Only owner/admin can invite (checked via Organization Service)
- **Cancellation Permission**: Only inviter or org admin can cancel

### Input Validation
- **Pydantic Models**: All requests validated
- **Email Validation**: Format validation (contains '@')
- **Email Normalization**: Lowercase conversion
- **SQL Injection**: Parameterized queries via gRPC

### Access Control
- **Authenticated Routes**: Create, accept, cancel, resend, list require X-User-Id
- **Public Routes**: Get invitation by token (token IS the authentication)
- **Admin Routes**: Bulk expire (internal use only)

### Data Privacy
- **Email Masking**: Future enhancement for list views
- **Token Redaction**: Consider not returning token in list responses
- **Audit Trail**: All status changes tracked with timestamps

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on token, org_id, email, status, invited_by
- **Partial Index**: `idx_invitations_expires_at` only for PENDING status
- **Unique Partial Index**: Prevents duplicate pending invitations efficiently
- **Connection Pooling**: gRPC client pools connections

### Query Optimization
- **Token Lookup**: O(1) via unique index
- **Org Invitations**: Index scan on organization_id
- **Bulk Expiration**: Partial index on expires_at for PENDING only
- **Pagination**: LIMIT/OFFSET with created_at DESC ordering

### API Optimization
- **Async Operations**: All I/O is async
- **Cross-Service Calls**: httpx.AsyncClient for non-blocking HTTP
- **Event Publishing**: Fire-and-forget pattern (non-blocking)

### Caching (Future)
- **Invitation Cache**: Short TTL for frequently accessed invitations
- **Permission Cache**: Cache org membership checks for repeat invitations

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation (get, accept, cancel, resend)
- `201 Created`: New invitation created
- `400 Bad Request`: Validation error, duplicate invitation, expired/cancelled
- `401 Unauthorized`: Missing X-User-Id header
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Invitation/organization not found
- `500 Internal Server Error`: Database error, unexpected error
- `503 Service Unavailable`: Database/dependency unavailable

### Error Response Format
```json
{
  "detail": "A pending invitation already exists for this email"
}
```

### Error Scenarios

| Scenario | Status | Response |
|----------|--------|----------|
| Invalid email format | 400 | "Invalid email format" |
| Duplicate pending invitation | 400 | "A pending invitation already exists" |
| User already member | 400 | "User is already a member" |
| Organization not found | 400 | "Organization not found" |
| No invite permission | 400 | "You don't have permission to invite" |
| Invitation not found | 404 | "Invitation not found" |
| Invitation expired | 400 | "Invitation has expired" |
| Invitation cancelled | 400 | "Invitation is cancelled" |
| Email mismatch | 400 | "Email mismatch" |
| Member addition failed | 400 | "Failed to add user to organization" |

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | HTTP port | 8213 |
| `SERVICE_HOST` | Bind host | 0.0.0.0 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS connection | nats://localhost:4222 |
| `CONSUL_HOST` | Consul host | localhost |
| `CONSUL_PORT` | Consul port | 8500 |
| `CONSUL_ENABLED` | Enable Consul registration | true |
| `LOG_LEVEL` | Logging level | INFO |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "invitation_service",
  "port": 8213,
  "version": "1.0.0"
}
```

### Service Info

```json
GET /info
{
  "service": "invitation_service",
  "version": "1.0.0",
  "description": "Organization invitation management microservice",
  "capabilities": {
    "invitation_creation": true,
    "email_sending": true,
    "invitation_acceptance": true,
    "invitation_management": true,
    "organization_integration": true
  },
  "endpoints": {
    "health": "/health",
    "create_invitation": "/api/v1/organizations/{org_id}/invitations",
    "get_invitation": "/api/v1/invitations/{token}",
    "accept_invitation": "/api/v1/invitations/accept",
    "organization_invitations": "/api/v1/organizations/{org_id}/invitations"
  }
}
```

### Kubernetes Deployment (Example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: invitation-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: invitation-service
  template:
    metadata:
      labels:
        app: invitation-service
    spec:
      containers:
      - name: invitation-service
        image: isa/invitation-service:1.0.0
        ports:
        - containerPort: 8213
        env:
        - name: SERVICE_PORT
          value: "8213"
        - name: POSTGRES_HOST
          value: "isa-postgres-grpc"
        - name: NATS_URL
          value: "nats://isa-nats:4222"
        livenessProbe:
          httpGet:
            path: /health
            port: 8213
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8213
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation for all models
- **Logic Contract**: Business rule documentation and validation
- **Component Tests**: Factory, builder, validation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **Cross-Service**: Organization Service client mocks

### API Testing
- **Endpoint Contracts**: All 8 endpoints tested
- **Error Handling**: Validation, not found, permission errors
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Full Flow**: Create → View → Accept invitation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Maintained By**: Invitation Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/invitation_service.md
- PRD: docs/prd/invitation_service.md
- Data Contract: tests/contracts/invitation_service/data_contract.py
- Logic Contract: tests/contracts/invitation_service/logic_contract.md
- System Contract: tests/contracts/invitation_service/system_contract.md
