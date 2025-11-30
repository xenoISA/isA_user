-- Task Service Migration: Remove user foreign keys
-- Version: 003
-- Date: 2025-10-14
-- Description: Remove foreign key constraints on user_id to allow flexible user management

-- Drop foreign key constraint from user_tasks table
ALTER TABLE dev.user_tasks
DROP CONSTRAINT IF EXISTS user_tasks_user_id_fkey;

-- Drop foreign key constraint from task_executions table
ALTER TABLE dev.task_executions
DROP CONSTRAINT IF EXISTS task_executions_user_id_fkey;

-- Add comments explaining the change
COMMENT ON COLUMN dev.user_tasks.user_id IS 'User identifier (no foreign key constraint for flexibility)';
COMMENT ON COLUMN dev.task_executions.user_id IS 'User identifier (no foreign key constraint for flexibility)';

-- Note: user_id is still validated at the application layer through the auth service
