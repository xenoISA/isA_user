-- Seed test data for Task Service
-- Schema: task
-- Date: 2025-10-27

-- Insert test user tasks
INSERT INTO task.user_tasks (
    task_id, user_id, name, description, task_type, status, priority,
    config, schedule, tags, metadata, credits_per_run,
    due_date, next_run_time, created_at, updated_at
) VALUES
    ('task_test_001', 'test_user_001', 'Daily Weather Report', 'Get weather for San Francisco', 'daily_weather', 'scheduled', 'medium',
     '{"location": "San Francisco", "units": "celsius"}'::jsonb,
     '{"type": "daily", "time": "08:00"}'::jsonb,
     ARRAY['weather', 'monitoring'], '{}'::jsonb, 0.5,
     NULL, NOW() + INTERVAL '1 day', NOW(), NOW()),

    ('task_test_002', 'test_user_002', 'Buy Groceries', 'Weekly grocery shopping', 'todo', 'pending', 'high',
     '{}'::jsonb, NULL, ARRAY['personal', 'shopping'], '{}'::jsonb, 0,
     NOW() + INTERVAL '3 days', NULL, NOW(), NOW()),

    ('task_test_003', 'test_user_001', 'Team Meeting Reminder', 'Standup meeting reminder', 'reminder', 'scheduled', 'urgent',
     '{"notification_type": "push"}'::jsonb,
     '{"type": "daily", "time": "09:00"}'::jsonb,
     ARRAY['work', 'meetings'], '{}'::jsonb, 0.1,
     NULL, NOW() + INTERVAL '12 hours', NOW(), NOW())
ON CONFLICT (task_id) DO NOTHING;

-- Insert test task executions
INSERT INTO task.task_executions (
    execution_id, task_id, user_id, status, trigger_type,
    trigger_data, result, credits_consumed, duration_ms,
    started_at, completed_at, created_at
) VALUES
    ('exec_test_001', 'task_test_001', 'test_user_001', 'completed', 'scheduler',
     '{"scheduled_time": "2025-10-27T08:00:00Z"}'::jsonb,
     '{"temperature": 18, "condition": "Sunny"}'::jsonb,
     0.5, 1250, NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'),

    ('exec_test_002', 'task_test_001', 'test_user_001', 'failed', 'scheduler',
     '{"scheduled_time": "2025-10-26T08:00:00Z"}'::jsonb,
     '{}'::jsonb,
     0.5, 2100, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),

    ('exec_test_003', 'task_test_003', 'test_user_001', 'completed', 'manual',
     '{}'::jsonb,
     '{"notification_sent": true}'::jsonb,
     0.1, 850, NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours')
ON CONFLICT (execution_id) DO NOTHING;

-- Update task statistics based on executions
UPDATE task.user_tasks SET
    run_count = 2,
    success_count = 1,
    failure_count = 1,
    total_credits_consumed = 1.0,
    last_run_time = NOW() - INTERVAL '1 day',
    last_success_time = NOW() - INTERVAL '1 day'
WHERE task_id = 'task_test_001';

UPDATE task.user_tasks SET
    run_count = 1,
    success_count = 1,
    failure_count = 0,
    total_credits_consumed = 0.1,
    last_run_time = NOW() - INTERVAL '5 hours',
    last_success_time = NOW() - INTERVAL '5 hours'
WHERE task_id = 'task_test_003';

-- Verify seeded data
SELECT 'Templates:', COUNT(*) FROM task.task_templates;
SELECT 'User Tasks:', COUNT(*) FROM task.user_tasks;
SELECT 'Executions:', COUNT(*) FROM task.task_executions;
