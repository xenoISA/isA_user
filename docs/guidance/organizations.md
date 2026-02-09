# Organizations

Multi-tenant organizations, family sharing, and invitations.

## Overview

Social and organizational features are handled by three services:

| Service | Port | Purpose |
|---------|------|---------|
| organization_service | 8212 | Multi-tenant, hierarchies, family sharing |
| invitation_service | 8213 | Invites, sharing links |
| membership_service | 8250 | Loyalty tiers, benefits |

## Organization Service (8212)

### Create Organization

```bash
curl -X POST "http://localhost:8212/api/v1/organizations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "type": "business",
    "settings": {
      "allow_member_invites": true,
      "default_role": "member"
    }
  }'
```

Response:
```json
{
  "organization_id": "org_abc123",
  "name": "Acme Corp",
  "type": "business",
  "owner_id": "user_123",
  "created_at": "2024-01-28T10:30:00Z"
}
```

### Organization Types

| Type | Description | Features |
|------|-------------|----------|
| `personal` | Individual workspace | Single owner |
| `family` | Family sharing | Shared storage, albums |
| `team` | Small team | Up to 10 members |
| `business` | Business org | Unlimited, advanced RBAC |
| `enterprise` | Enterprise | SSO, audit, compliance |

### Get Organization

```bash
curl "http://localhost:8212/api/v1/organizations/org_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List My Organizations

```bash
curl "http://localhost:8212/api/v1/organizations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Organization

```bash
curl -X PATCH "http://localhost:8212/api/v1/organizations/org_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "settings": {
      "logo_url": "https://example.com/logo.png"
    }
  }'
```

## Family Sharing

### Create Family

```bash
curl -X POST "http://localhost:8212/api/v1/organizations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smith Family",
    "type": "family",
    "settings": {
      "shared_storage": true,
      "shared_albums": true,
      "child_accounts": true
    }
  }'
```

### Family Roles

| Role | Permissions |
|------|-------------|
| `organizer` | Full control, billing, add/remove members |
| `adult` | Full access, can manage children |
| `teen` | Limited access, parental controls |
| `child` | Restricted, parent approval needed |

### Add Family Member

```bash
curl -X POST "http://localhost:8212/api/v1/organizations/org_family123/members" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "spouse@example.com",
    "role": "adult",
    "relationship": "spouse"
  }'
```

### Shared Resources

```bash
# Share storage with family
curl -X POST "http://localhost:8212/api/v1/organizations/org_family123/resources" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "storage",
    "resource_id": "folder_photos",
    "shared_with_all": true
  }'
```

## Member Management

### Add Member

```bash
curl -X POST "http://localhost:8212/api/v1/organizations/org_abc123/members" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_456",
    "role": "editor"
  }'
```

### List Members

```bash
curl "http://localhost:8212/api/v1/organizations/org_abc123/members" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "members": [
    {
      "user_id": "user_123",
      "name": "John Doe",
      "email": "john@example.com",
      "role": "owner",
      "joined_at": "2024-01-01T00:00:00Z"
    },
    {
      "user_id": "user_456",
      "name": "Jane Smith",
      "email": "jane@example.com",
      "role": "editor",
      "joined_at": "2024-01-15T00:00:00Z"
    }
  ],
  "total": 2
}
```

### Update Member Role

```bash
curl -X PATCH "http://localhost:8212/api/v1/organizations/org_abc123/members/user_456" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

### Remove Member

```bash
curl -X DELETE "http://localhost:8212/api/v1/organizations/org_abc123/members/user_456" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Organization Hierarchy

### Create Department

```bash
curl -X POST "http://localhost:8212/api/v1/organizations/org_abc123/departments" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering",
    "parent_id": null,
    "manager_id": "user_789"
  }'
```

### Get Hierarchy

```bash
curl "http://localhost:8212/api/v1/organizations/org_abc123/hierarchy" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "organization": "Acme Corp",
  "departments": [
    {
      "id": "dept_eng",
      "name": "Engineering",
      "manager": "John Doe",
      "members": 15,
      "children": [
        {
          "id": "dept_frontend",
          "name": "Frontend",
          "members": 5
        },
        {
          "id": "dept_backend",
          "name": "Backend",
          "members": 10
        }
      ]
    }
  ]
}
```

## Invitation Service (8213)

### Create Invitation

```bash
curl -X POST "http://localhost:8213/api/v1/invitations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "organization_id": "org_abc123",
    "role": "member",
    "message": "Join our team!"
  }'
```

### Create Invite Link

```bash
curl -X POST "http://localhost:8213/api/v1/invitations/link" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org_abc123",
    "role": "member",
    "max_uses": 10,
    "expires_in_days": 7
  }'
```

Response:
```json
{
  "invite_link": "https://app.example.com/join/inv_xyz789",
  "invite_code": "inv_xyz789",
  "expires_at": "2024-02-04T10:30:00Z",
  "remaining_uses": 10
}
```

### Accept Invitation

```bash
curl -X POST "http://localhost:8213/api/v1/invitations/inv_xyz789/accept" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Pending Invitations

```bash
curl "http://localhost:8213/api/v1/invitations?organization_id=org_abc123&status=pending" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Revoke Invitation

```bash
curl -X DELETE "http://localhost:8213/api/v1/invitations/inv_xyz789" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Membership Service (8250)

### Get Membership Status

```bash
curl "http://localhost:8250/api/v1/membership/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "tier": "gold",
  "points": 15000,
  "benefits": [
    "priority_support",
    "extended_storage",
    "early_access"
  ],
  "next_tier": {
    "name": "platinum",
    "points_required": 25000
  }
}
```

### Membership Tiers

| Tier | Points | Benefits |
|------|--------|----------|
| Bronze | 0 | Base features |
| Silver | 5,000 | 10% discount, 5GB extra storage |
| Gold | 15,000 | 20% discount, priority support |
| Platinum | 25,000 | 30% discount, early access, dedicated support |

### Earn Points

Points are automatically earned through:
- Purchases (1 point per $1)
- Referrals (500 points)
- Activity streaks (100 points/week)

## Graph Relationships (Neo4j)

Organizations use Neo4j for complex relationships:

```cypher
// Find all members in org hierarchy
MATCH (o:Organization {id: 'org_abc123'})-[:HAS_MEMBER*]->(u:User)
RETURN u

// Find shared resources in family
MATCH (f:Organization {type: 'family'})-[:SHARES]->(r:Resource)
WHERE f.id = 'org_family123'
RETURN r
```

## Python SDK

```python
from isa_user import OrganizationClient, InvitationClient

orgs = OrganizationClient("http://localhost:8212")
invites = InvitationClient("http://localhost:8213")

# Create organization
org = await orgs.create(
    token=access_token,
    name="My Team",
    type="team"
)

# Add member
await orgs.add_member(
    token=access_token,
    org_id=org.organization_id,
    user_id="user_456",
    role="editor"
)

# Create invite link
link = await invites.create_link(
    token=access_token,
    org_id=org.organization_id,
    max_uses=5
)
```

## Next Steps

- [Devices](./devices) - IoT management
- [Memory](./memory) - AI cognitive memory
- [Storage](./storage) - File management
