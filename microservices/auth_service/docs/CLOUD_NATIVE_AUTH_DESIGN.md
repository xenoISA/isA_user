# Cloud-Native Authentication Service Design Review

## Executive Summary

Since you're **removing Auth0** and building your own authentication system, we need to ensure the design is production-ready for a cloud-native, cross-platform environment.

## Current Design Analysis

### ✅ What's Good

1. **Separation of Concerns**
   - Authentication (auth_service) separate from Authorization (authorization_service) ✅
   - JWT-based stateless authentication ✅
   - API keys for service-to-service auth ✅
   - Device credentials for IoT/smart frames ✅

2. **Custom JWT Implementation**
   - Self-issued tokens with `issuer: "isA_user"` ✅
   - Access + Refresh token pattern ✅
   - Token fingerprinting for revocation ✅

3. **Multi-tenant Support**
   - Organizations as the primary tenant boundary ✅
   - API keys scoped to organizations ✅

### ⚠️ Critical Gaps for Production Auth Service

Since you're replacing Auth0, you need these **essential features**:

## 1. ❌ Missing: Password Authentication

**Problem**: You have JWT generation but no password storage/verification

**Need to Add**:
```sql
ALTER TABLE auth.users ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE auth.users ADD COLUMN password_salt VARCHAR(255);
ALTER TABLE auth.users ADD COLUMN password_updated_at TIMESTAMPTZ;
ALTER TABLE auth.users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE auth.users ADD COLUMN locked_until TIMESTAMPTZ;
```

**Implementation**:
- Use Argon2id for password hashing (already in requirements)
- Password policy: min 12 chars, complexity rules
- Account lockout after 5 failed attempts (15 min)
- Password expiry (90-180 days for compliance)

## 2. ❌ Missing: Email Verification & Password Reset

**Need to Add**:
```sql
CREATE TABLE auth.verification_tokens (
    token_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES auth.users(user_id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    token_type VARCHAR(20) NOT NULL, -- email_verify, password_reset, magic_link
    email VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_verification_tokens_hash ON auth.verification_tokens(token_hash, token_type)
    WHERE used_at IS NULL;
CREATE INDEX idx_verification_tokens_user ON auth.verification_tokens(user_id, token_type);
```

**Flows to Implement**:
- Email verification on signup
- Password reset flow
- Magic link authentication (passwordless)

## 3. ❌ Missing: Multi-Factor Authentication (MFA)

**Critical for Enterprise**: MFA is expected in modern auth systems

```sql
CREATE TABLE auth.mfa_factors (
    factor_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES auth.users(user_id),
    factor_type VARCHAR(20) NOT NULL, -- totp, sms, email, backup_codes
    factor_name VARCHAR(100),
    secret_encrypted TEXT, -- Encrypted TOTP secret or phone number
    backup_codes JSONB, -- Array of hashed backup codes
    is_verified BOOLEAN DEFAULT FALSE,
    is_primary BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

CREATE TABLE auth.mfa_challenges (
    challenge_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    factor_id VARCHAR(50) REFERENCES auth.mfa_factors(factor_id),
    challenge_code VARCHAR(10), -- 6-digit code
    attempts INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User-level MFA settings
ALTER TABLE auth.users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE auth.users ADD COLUMN mfa_required BOOLEAN DEFAULT FALSE; -- Org policy
```

**MFA Types to Support**:
- TOTP (Google Authenticator, Authy) - Priority 1
- Email codes - Priority 2
- SMS codes - Priority 3 (requires Twilio/similar)
- Backup codes - Must have

## 4. ⚠️ Improve: Session Management

**Current**: Basic session tracking
**Need**: Production-grade session management

```sql
-- Enhanced session table
CREATE TABLE auth.user_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES auth.users(user_id),
    refresh_token_hash VARCHAR(64) NOT NULL UNIQUE, -- Hash of refresh token
    access_token_jti VARCHAR(50), -- JWT ID for revocation

    -- Session context
    device_info JSONB, -- {device_type, os, browser, device_id}
    ip_address VARCHAR(45),
    user_agent TEXT,
    geo_location JSONB, -- {country, city, lat, lon}

    -- Security
    is_active BOOLEAN DEFAULT TRUE,
    mfa_verified BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    invalidated_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB
);

CREATE INDEX idx_sessions_user_active ON auth.user_sessions(user_id, is_active);
CREATE INDEX idx_sessions_refresh_token ON auth.user_sessions(refresh_token_hash)
    WHERE is_active = TRUE;
CREATE INDEX idx_sessions_expires ON auth.user_sessions(expires_at)
    WHERE is_active = TRUE;
```

**Session Features**:
- Refresh token rotation (security best practice)
- Device fingerprinting
- Concurrent session limits (e.g., max 5 devices)
- "Sign out all devices" capability
- Suspicious activity detection

## 5. ❌ Missing: Audit Logging & Security Events

**Critical for Compliance**: SOC2, GDPR, HIPAA require audit trails

```sql
CREATE TABLE auth.audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- login, logout, password_change, mfa_enabled, etc.
    event_category VARCHAR(20) NOT NULL, -- authentication, authorization, account_management
    severity VARCHAR(10) NOT NULL, -- info, warning, critical

    -- Actors
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    actor_type VARCHAR(20), -- user, api_key, device, system

    -- Context
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_id VARCHAR(255),

    -- Event details
    event_data JSONB, -- Flexible event-specific data
    result VARCHAR(20) NOT NULL, -- success, failure, blocked
    failure_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    correlation_id VARCHAR(50), -- For tracing across services
    request_id VARCHAR(50)
);

-- Partitioning for performance (monthly partitions)
CREATE INDEX idx_audit_logs_user_time ON auth.audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_org_time ON auth.audit_logs(organization_id, created_at DESC);
CREATE INDEX idx_audit_logs_event_time ON auth.audit_logs(event_type, created_at DESC);
CREATE INDEX idx_audit_logs_correlation ON auth.audit_logs(correlation_id);

-- Consider table partitioning by month for large datasets
```

**Security Events to Log**:
- All authentication attempts (success/failure)
- Password changes/resets
- MFA enable/disable
- Session creation/destruction
- API key usage
- Suspicious activities (impossible travel, brute force)

## 6. ❌ Missing: Rate Limiting & Brute Force Protection

**Need to Add**:
```sql
CREATE TABLE auth.rate_limits (
    limit_key VARCHAR(255) PRIMARY KEY, -- IP, user_id, api_key, etc.
    limit_type VARCHAR(50) NOT NULL, -- login_attempt, password_reset, api_call
    attempt_count INTEGER DEFAULT 1,
    first_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    blocked_until TIMESTAMPTZ,

    -- Auto-expire old entries
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rate_limits_blocked ON auth.rate_limits(blocked_until)
    WHERE blocked_until IS NOT NULL;
```

**Rate Limits to Implement**:
- Login: 5 attempts per IP per 15 min
- Password reset: 3 attempts per email per hour
- Token refresh: 20 per hour per user
- API calls: Per organization tier (free/pro/enterprise)

## 7. ⚠️ Improve: Organization & Tenant Isolation

**Current**: Basic organizations table
**Need**: Multi-tenant security

```sql
CREATE TABLE auth.organizations (
    organization_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE, -- For subdomain: {slug}.yourapp.com

    -- Subscription
    subscription_tier VARCHAR(20) DEFAULT 'free', -- free, pro, enterprise
    subscription_status VARCHAR(20) DEFAULT 'active',
    subscription_expires_at TIMESTAMPTZ,

    -- Features & Limits
    features JSONB DEFAULT '[]', -- ['sso', 'mfa_required', 'audit_logs']
    limits JSONB, -- {max_users: 100, max_api_keys: 10}

    -- Security settings
    password_policy JSONB, -- {min_length: 12, require_mfa: true}
    session_timeout_minutes INTEGER DEFAULT 480, -- 8 hours
    allowed_ip_ranges JSONB, -- IP whitelist

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Organization members (moved from users)
CREATE TABLE auth.organization_members (
    member_id VARCHAR(50) PRIMARY KEY,
    organization_id VARCHAR(50) NOT NULL REFERENCES auth.organizations(organization_id),
    user_id VARCHAR(255) NOT NULL REFERENCES auth.users(user_id),
    role VARCHAR(50) NOT NULL, -- owner, admin, member, guest
    permissions JSONB, -- Org-specific permissions
    invited_by VARCHAR(255),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(organization_id, user_id)
);

CREATE INDEX idx_org_members_org ON auth.organization_members(organization_id, is_active);
CREATE INDEX idx_org_members_user ON auth.organization_members(user_id, is_active);
```

## 8. ❌ Missing: OAuth/OIDC Provider (For Your Apps)

**If you want other apps to integrate**: Implement OAuth2/OIDC server

```sql
CREATE TABLE auth.oauth_clients (
    client_id VARCHAR(50) PRIMARY KEY,
    client_secret_hash VARCHAR(64) NOT NULL,
    organization_id VARCHAR(50) REFERENCES auth.organizations(organization_id),

    name VARCHAR(255) NOT NULL,
    description TEXT,
    redirect_uris JSONB NOT NULL, -- Array of allowed redirect URIs
    allowed_scopes JSONB, -- ['openid', 'email', 'profile']

    grant_types JSONB DEFAULT '["authorization_code"]', -- authorization_code, refresh_token, client_credentials

    is_trusted BOOLEAN DEFAULT FALSE, -- Skip consent screen
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE auth.oauth_authorization_codes (
    code VARCHAR(100) PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL REFERENCES auth.oauth_clients(client_id),
    user_id VARCHAR(255) NOT NULL REFERENCES auth.users(user_id),
    redirect_uri TEXT NOT NULL,
    scopes JSONB,
    code_challenge VARCHAR(255), -- PKCE
    code_challenge_method VARCHAR(10), -- S256 or plain
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 9. ✅ Good: Device Authentication

**Your current device credentials design is solid!**

Minor improvements:
```sql
-- Add device trust level
ALTER TABLE auth.device_credentials ADD COLUMN trust_level VARCHAR(20) DEFAULT 'untrusted';
-- Values: untrusted, basic, trusted, verified

-- Add certificate support for high-security devices
ALTER TABLE auth.device_credentials ADD COLUMN certificate_fingerprint VARCHAR(64);
ALTER TABLE auth.device_credentials ADD COLUMN certificate_expires_at TIMESTAMPTZ;
```

## 10. ❌ Missing: Token Revocation

**Critical**: You can generate tokens but can't revoke them!

```sql
CREATE TABLE auth.revoked_tokens (
    jti VARCHAR(50) PRIMARY KEY, -- JWT ID
    token_type VARCHAR(20) NOT NULL, -- access, refresh
    user_id VARCHAR(255),
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL, -- When token would naturally expire
    revoked_by VARCHAR(255),
    reason VARCHAR(50) -- logout, password_change, compromised, admin_action
);

-- Cleanup task: DELETE WHERE expires_at < NOW() - INTERVAL '7 days'
CREATE INDEX idx_revoked_tokens_expires ON auth.revoked_tokens(expires_at);
CREATE INDEX idx_revoked_tokens_user ON auth.revoked_tokens(user_id, revoked_at);
```

**Middleware**: Check `jti` against revoked list on each request

---

## Recommended Final Schema Structure

```
auth schema:
├── Core Identity
│   ├── users (enhanced with password, MFA settings)
│   ├── user_profiles (separate for PII)
│   └── verification_tokens
│
├── Multi-Factor Auth
│   ├── mfa_factors
│   └── mfa_challenges
│
├── Session Management
│   ├── user_sessions (enhanced)
│   └── revoked_tokens
│
├── Organization & Tenancy
│   ├── organizations (enhanced)
│   ├── organization_members
│   └── organization_invitations
│
├── API & Service Auth
│   ├── api_keys (NEW - from JSONB)
│   ├── device_credentials (enhanced)
│   └── device_auth_logs
│
├── OAuth/OIDC (if needed)
│   ├── oauth_clients
│   ├── oauth_authorization_codes
│   └── oauth_access_tokens
│
└── Security & Compliance
    ├── audit_logs (partitioned)
    ├── rate_limits
    └── security_alerts
```

---

## Priority Implementation Order

### Phase 1: Critical Security (Do First)
1. ✅ Password authentication (Argon2id)
2. ✅ Email verification
3. ✅ Password reset flow
4. ✅ Session management (refresh token rotation)
5. ✅ Rate limiting & brute force protection
6. ✅ Audit logging

### Phase 2: Enterprise Features (Week 2-3)
1. ✅ MFA (TOTP)
2. ✅ Token revocation
3. ✅ Enhanced organization management
4. ✅ Security alerts

### Phase 3: Advanced (Week 4+)
1. ⚪ OAuth2/OIDC server (if needed)
2. ⚪ Risk-based authentication
3. ⚪ SSO integration (SAML, etc.)
4. ⚪ Compliance features (data export, deletion)

---

## Code Architecture Recommendations

### 1. Separate Password Service
```python
class PasswordService:
    def hash_password(self, password: str) -> Dict[str, str]
    def verify_password(self, password: str, hash: str) -> bool
    def check_password_policy(self, password: str) -> List[str]
    def is_password_compromised(self, password: str) -> bool  # HaveIBeenPwned API
```

### 2. MFA Service
```python
class MFAService:
    def generate_totp_secret(self, user_id: str) -> Dict
    def verify_totp_code(self, user_id: str, code: str) -> bool
    def generate_backup_codes(self, user_id: str) -> List[str]
    def send_email_code(self, user_id: str) -> str
```

### 3. Session Service
```python
class SessionService:
    def create_session(self, user_id: str, device_info: Dict) -> Dict
    def refresh_session(self, refresh_token: str) -> Dict
    def revoke_session(self, session_id: str) -> bool
    def list_user_sessions(self, user_id: str) -> List[Dict]
```

---

## Security Best Practices Checklist

- [ ] All passwords hashed with Argon2id
- [ ] All tokens stored as SHA256 hashes
- [ ] Rate limiting on all auth endpoints
- [ ] HTTPS only (TLS 1.3)
- [ ] Secure cookie flags (HttpOnly, Secure, SameSite)
- [ ] CORS properly configured
- [ ] CSP headers set
- [ ] Input validation on all fields
- [ ] SQL injection prevention (parameterized queries) ✅
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection for web clients
- [ ] Account enumeration prevention (timing attacks)
- [ ] Audit logging for all security events
- [ ] Regular security testing (penetration tests)

---

## Compliance Considerations

### GDPR
- User data export API
- User data deletion API
- Audit log retention (7 years)
- Consent management

### SOC2
- Audit logs ✅
- Access controls ✅
- Encryption at rest & in transit
- Regular security reviews

### HIPAA (if handling health data)
- Enhanced audit logging
- PHI encryption
- Breach notification

---

## Bottom Line

**Your current design is a good start** but needs these critical additions for a production auth service:

### Must Have (Before Production)
1. ✅ Password authentication & storage
2. ✅ Email verification
3. ✅ Password reset
4. ✅ MFA (at least TOTP)
5. ✅ Audit logging
6. ✅ Rate limiting
7. ✅ Token revocation

### Should Have (Within 1 month)
- Enhanced session management
- Organization member management
- Security alerts
- Account lockout

### Nice to Have (Future)
- OAuth2 provider
- SSO integrations
- Risk-based authentication
- Biometric support

**Want me to implement the critical Phase 1 features first?** We can start with password authentication + email verification.
