-- Migration: Add admin_roles column to accounts table
-- Issue: #189 - Add unified admin authentication with scoped JWT
-- Date: 2026-03-28

ALTER TABLE account.accounts ADD COLUMN IF NOT EXISTS admin_roles JSONB DEFAULT NULL;

-- Also add admin_roles to auth.users for login-time role check
ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS admin_roles JSONB DEFAULT NULL;

COMMENT ON COLUMN account.accounts.admin_roles IS 'Admin roles assigned to this user (JSONB array). Valid roles: super_admin, billing_admin, product_admin, support_admin, compliance_admin';
COMMENT ON COLUMN auth.users.admin_roles IS 'Admin roles assigned to this user (JSONB array). Synced from account.accounts for login-time checks';
