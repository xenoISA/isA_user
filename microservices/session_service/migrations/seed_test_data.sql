-- Session Service: Seed Test Data
-- Date: 2025-10-26

-- Seed test sessions
INSERT INTO session.sessions (session_id, user_id, conversation_data, status, metadata, is_active, message_count, total_tokens, total_cost, session_summary, created_at, updated_at, last_activity)
VALUES
    ('test_session_001', 'test_user_001', '{"topic": "general", "context": "test"}', 'active', '{"test": true}', true, 0, 0, 0.0, '', NOW(), NOW(), NOW()),
    ('test_session_002', 'test_user_001', '{"topic": "coding", "context": "test"}', 'active', '{"test": true}', true, 0, 0, 0.0, '', NOW(), NOW(), NOW()),
    ('test_session_003', 'test_user_002', '{"topic": "general", "context": "test"}', 'ended', '{"test": true}', false, 5, 100, 0.001, 'Test session', NOW(), NOW(), NOW() - INTERVAL '1 hour')
ON CONFLICT (session_id) DO NOTHING;

-- Seed test messages
INSERT INTO session.session_messages (id, session_id, user_id, role, content, message_type, message_metadata, tokens_used, cost_usd, created_at)
VALUES
    (gen_random_uuid(), 'test_session_001', 'test_user_001', 'user', 'Hello, world!', 'chat', '{}', 5, 0.0001, NOW()),
    (gen_random_uuid(), 'test_session_001', 'test_user_001', 'assistant', 'Hi there! How can I help you?', 'chat', '{}', 10, 0.0002, NOW()),
    (gen_random_uuid(), 'test_session_002', 'test_user_001', 'user', 'Write a Python function', 'chat', '{}', 8, 0.0001, NOW()),
    (gen_random_uuid(), 'test_session_002', 'test_user_001', 'assistant', 'Sure! Here is a Python function...', 'chat', '{}', 50, 0.001, NOW())
ON CONFLICT DO NOTHING;

-- Seed test memories
INSERT INTO session.session_memories (id, session_id, user_id, conversation_summary, session_metadata, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'test_session_003', 'test_user_002', 'User discussed coding topics', '{"topics": ["coding", "python"]}', NOW(), NOW())
ON CONFLICT (session_id) DO NOTHING;
