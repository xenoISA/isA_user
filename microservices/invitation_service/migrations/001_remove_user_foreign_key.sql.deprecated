-- Migration: Remove foreign key constraint on invited_by column
-- Reason: Support eventual consistency across microservices
-- The invitation service should not have hard dependencies on the users table

-- Remove the foreign key constraint on invited_by
ALTER TABLE IF EXISTS dev.organization_invitations
DROP CONSTRAINT IF EXISTS organization_invitations_invited_by_fkey;

-- Add index for performance (optional, but recommended)
CREATE INDEX IF NOT EXISTS idx_organization_invitations_invited_by
ON dev.organization_invitations(invited_by);

-- Add comment explaining why we don't have FK
COMMENT ON COLUMN dev.organization_invitations.invited_by IS
'User ID of the inviter. No foreign key constraint to support eventual consistency across microservices.';
