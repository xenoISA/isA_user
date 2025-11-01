-- Cleanup test data for Task Service
-- Schema: task
-- Date: 2025-10-27

-- Delete test task executions
DELETE FROM task.task_executions
WHERE execution_id LIKE 'exec_test_%';

-- Delete test user tasks
DELETE FROM task.user_tasks
WHERE task_id LIKE 'task_test_%';

-- Verify cleanup
SELECT 'Templates remaining:', COUNT(*) FROM task.task_templates;
SELECT 'User Tasks remaining:', COUNT(*) FROM task.user_tasks;
SELECT 'Executions remaining:', COUNT(*) FROM task.task_executions;
