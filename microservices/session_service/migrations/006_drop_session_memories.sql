-- Session Service Migration: Drop session_memories table
-- Version: 006
-- Date: 2025-10-27
-- Reason: Memory functionality is handled by dedicated memory_service

-- Drop session_memories table (memory is handled by memory_service)
DROP TABLE IF EXISTS session.session_memories CASCADE;

COMMENT ON SCHEMA session IS 'Session management schema (sessions and messages only)';
