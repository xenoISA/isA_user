-- Session Service Migration: Fix UUID types to VARCHAR
-- Version: 005
-- Date: 2025-10-27

-- Change message id from UUID to VARCHAR(36)
ALTER TABLE session.session_messages ALTER COLUMN id TYPE VARCHAR(36);

-- Change memory id from UUID to VARCHAR(36)  
ALTER TABLE session.session_memories ALTER COLUMN id TYPE VARCHAR(36);

-- Comments
COMMENT ON COLUMN session.session_messages.id IS 'Message identifier (UUID string)';
COMMENT ON COLUMN session.session_memories.id IS 'Memory identifier (UUID string)';
