-- Project Service — Star, Archive, and Owner ID (Story #442, paired with xenoISA/isA_#429)
-- Adds owner_id (sender/creator), starred_at, archived_at to project.projects.
-- Safe to apply on existing environments (idempotent).
--
-- A follow-up data migration is responsible for back-filling owner_id from
-- user_id where owner_id IS NULL or empty. For the column add we default to
-- empty string so existing rows remain valid.

-- 1. owner_id — defaults to '' so existing rows satisfy NOT NULL.
ALTER TABLE project.projects
    ADD COLUMN IF NOT EXISTS owner_id TEXT NOT NULL DEFAULT '';

-- 2. starred_at / archived_at — null by default.
ALTER TABLE project.projects
    ADD COLUMN IF NOT EXISTS starred_at TIMESTAMPTZ NULL;

ALTER TABLE project.projects
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL;

-- 3. Hot path: list-by-owner that hides archived.
--    Use a partial index so the default project list query stays cheap and
--    skips rows that have been archived.
CREATE INDEX IF NOT EXISTS idx_project_projects_owner_active
    ON project.projects (owner_id)
    WHERE archived_at IS NULL;

-- 4. Starred view: most users keep a small starred set, so partial index is
--    much cheaper than a full btree.
CREATE INDEX IF NOT EXISTS idx_project_projects_starred
    ON project.projects (starred_at)
    WHERE starred_at IS NOT NULL;

-- 5. Helper index for "include_archived=true" listings that still want
--    fast filtering by owner. Cheap to maintain because archived rows
--    are the long tail.
CREATE INDEX IF NOT EXISTS idx_project_projects_owner_id
    ON project.projects (owner_id);

COMMENT ON COLUMN project.projects.owner_id IS 'Effective owner — drives access checks and list scoping. Defaults to empty for legacy rows; back-fill from user_id.';
COMMENT ON COLUMN project.projects.starred_at IS 'Star pin timestamp. NULL = not starred. See xenoISA/isA_#429 §15.3.';
COMMENT ON COLUMN project.projects.archived_at IS 'Archive timestamp. NULL = active. Archived projects are hidden from default list and all shares are revoked. See #429 §15.6.';
