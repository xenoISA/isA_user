-- Project Service Database Schema
-- Safe to apply on existing environments.

CREATE SCHEMA IF NOT EXISTS project;

CREATE TABLE IF NOT EXISTS project.projects (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    org_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    custom_instructions TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project.project_files (
    id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    filename VARCHAR(1024) NOT NULL,
    file_type VARCHAR(255),
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_projects_user_id
    ON project.projects(user_id);

CREATE INDEX IF NOT EXISTS idx_project_projects_updated_at
    ON project.projects(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_project_files_project_id
    ON project.project_files(project_id);

CREATE INDEX IF NOT EXISTS idx_project_files_created_at
    ON project.project_files(created_at DESC);

COMMENT ON SCHEMA project IS 'Project service schema - projects, instructions, and knowledge file associations';
COMMENT ON TABLE project.projects IS 'Project workspaces owned by users or organizations';
COMMENT ON TABLE project.project_files IS 'Storage-backed file associations attached to projects';
