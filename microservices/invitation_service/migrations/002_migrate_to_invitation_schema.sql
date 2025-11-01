-- Invitation Service Migration: Migrate to dedicated invitation schema
-- Version: 002
-- Date: 2025-10-28
-- Description: Move tables from dev/public schema to invitation schema

-- Create invitation schema
CREATE SCHEMA IF NOT EXISTS invitation;

-- Drop existing tables/views in invitation schema if they exist
DROP TABLE IF EXISTS invitation.organization_invitations CASCADE;

-- 1. Create organization_invitations table
CREATE TABLE invitation.organization_invitations (
    id SERIAL PRIMARY KEY,
    invitation_id VARCHAR(100) UNIQUE NOT NULL,
    organization_id VARCHAR(100) NOT NULL,  -- No FK constraint - cross-service reference
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- owner, admin, member, viewer
    invited_by VARCHAR(100) NOT NULL,  -- No FK constraint - cross-service reference
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, expired, cancelled
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Organization invitations indexes
CREATE INDEX idx_invitations_organization_id ON invitation.organization_invitations(organization_id);
CREATE INDEX idx_invitations_email ON invitation.organization_invitations(email);
CREATE INDEX idx_invitations_token ON invitation.organization_invitations(invitation_token);
CREATE INDEX idx_invitations_status ON invitation.organization_invitations(status);
CREATE INDEX idx_invitations_invited_by ON invitation.organization_invitations(invited_by);
CREATE INDEX idx_invitations_expires_at ON invitation.organization_invitations(expires_at);

-- Composite indexes for common queries
CREATE INDEX idx_invitations_email_org_status ON invitation.organization_invitations(email, organization_id, status);
CREATE INDEX idx_invitations_org_status ON invitation.organization_invitations(organization_id, status);

-- ====================
-- Update Triggers
-- ====================

-- Trigger for organization_invitations
CREATE TRIGGER update_invitations_updated_at
    BEFORE UPDATE ON invitation.organization_invitations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA invitation IS 'Invitation service schema - organization invitation management';
COMMENT ON TABLE invitation.organization_invitations IS 'Organization invitations for members';
COMMENT ON COLUMN invitation.organization_invitations.invited_by IS 'User ID of the inviter. No FK constraint for cross-service independence';
COMMENT ON COLUMN invitation.organization_invitations.organization_id IS 'Organization ID. No FK constraint for cross-service independence';
COMMENT ON COLUMN invitation.organization_invitations.status IS 'Invitation status: pending, accepted, expired, cancelled';
