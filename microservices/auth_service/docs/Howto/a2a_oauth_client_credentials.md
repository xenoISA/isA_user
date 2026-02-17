# A2A OAuth2 Client-Credentials Quickstart

This guide validates the OAuth2 flow added for A2A interoperability.

## 1) Apply migration

```bash
export PGPASSWORD='staging_postgres_2024'
psql -h localhost -p 5432 -U postgres -d isa_platform \
  -f microservices/auth_service/migrations/006_create_oauth_clients_table.sql
```

## 2) Start auth_service

```bash
export JWT_SECRET='replace_with_strong_secret'
python -m microservices.auth_service.main
```

## 3) Create OAuth client (admin token required)

`/api/v1/auth/oauth/clients` is admin-protected. Pass a bearer token with `scope=admin` or `permissions` containing `auth.admin`.

```bash
curl -X POST http://localhost:8202/api/v1/auth/oauth/clients \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "client_name": "partner-agent",
    "organization_id": "org_partner_001",
    "allowed_scopes": ["a2a.invoke", "a2a.tasks.read", "a2a.tasks.cancel"],
    "token_ttl_seconds": 3600
  }'
```

Save `client_id` and one-time `client_secret` from the response.

## 4) Exchange client credentials for access token

```bash
curl -X POST http://localhost:8202/oauth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=a2a.invoke"
```

Expected fields:
- `access_token`
- `token_type` = `Bearer`
- `expires_in`
- `scope`

## 5) Validate token

```bash
curl -X POST http://localhost:8202/api/v1/auth/verify-token \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"${ACCESS_TOKEN}\",\"provider\":\"isa_user\"}"
```

## 6) Rotate client secret (admin)

```bash
curl -X POST http://localhost:8202/api/v1/auth/oauth/clients/${CLIENT_ID}/rotate-secret \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

## 7) Deactivate client (admin)

```bash
curl -X DELETE http://localhost:8202/api/v1/auth/oauth/clients/${CLIENT_ID} \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

## Notes for A2A Agent Card

Use this token endpoint in your Agent Card security declaration:

- `tokenUrl`: `https://<auth-domain>/oauth/token`
- scopes: `a2a.invoke`, `a2a.tasks.read`, `a2a.tasks.cancel`
