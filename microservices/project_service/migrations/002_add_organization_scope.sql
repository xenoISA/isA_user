-- Project Service Organization Scope
-- Safe to apply on existing environments.

ALTER TABLE project.projects
    ADD COLUMN IF NOT EXISTS org_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_project_projects_org_id
    ON project.projects(org_id);
