-- Session Service: Cleanup Test Data
-- Date: 2025-10-26

-- Delete test session messages
DELETE FROM session.session_messages WHERE session_id LIKE 'test_%';

-- Delete test session memories
DELETE FROM session.session_memories WHERE session_id LIKE 'test_%';

-- Delete test sessions
DELETE FROM session.sessions WHERE session_id LIKE 'test_%';
