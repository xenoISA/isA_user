-- Task Service Migration: Add Todo and Calendar fields
-- Version: 002
-- Date: 2025-10-01
-- Description: Add due_date, reminder_time, is_completed, completed_at fields for todo and calendar tasks

-- Add missing columns to user_tasks table
ALTER TABLE dev.user_tasks
ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS reminder_time TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON dev.user_tasks(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_reminder ON dev.user_tasks(reminder_time) WHERE reminder_time IS NOT NULL;

-- Add comments
COMMENT ON COLUMN dev.user_tasks.due_date IS 'Due date for todo tasks';
COMMENT ON COLUMN dev.user_tasks.reminder_time IS 'Time to send reminder notification';
COMMENT ON COLUMN dev.user_tasks.is_completed IS 'Whether the task has been completed';
COMMENT ON COLUMN dev.user_tasks.completed_at IS 'When the task was completed';
