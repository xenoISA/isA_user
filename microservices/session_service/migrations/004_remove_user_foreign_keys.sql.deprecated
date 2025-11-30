-- Session Service Migration: Remove foreign key constraints to users table
-- Version: 004
-- Date: 2025-01-20
--
-- Removes database-level foreign key constraints for microservice independence.
-- User validation is now handled at application layer via account service API.

-- Remove foreign key constraint from session_messages
ALTER TABLE IF EXISTS dev.session_messages
DROP CONSTRAINT IF EXISTS session_messages_user_id_fkey;

-- Remove foreign key constraint from session_memories
ALTER TABLE IF EXISTS dev.session_memories
DROP CONSTRAINT IF EXISTS session_memories_user_id_fkey;

-- Remove foreign key constraint from sessions (if exists)
ALTER TABLE IF EXISTS dev.sessions
DROP CONSTRAINT IF EXISTS sessions_user_id_fkey;

-- Add comments explaining the architectural decision
COMMENT ON COLUMN dev.session_messages.user_id IS 'User ID (validated via account service API, not FK constraint)';
COMMENT ON COLUMN dev.session_memories.user_id IS 'User ID (validated via account service API, not FK constraint)';
COMMENT ON COLUMN dev.sessions.user_id IS 'User ID (validated via account service API, not FK constraint)';

-- Indexes remain for performance (even without FK constraints)
-- The existing indexes on user_id columns provide query performance benefits
