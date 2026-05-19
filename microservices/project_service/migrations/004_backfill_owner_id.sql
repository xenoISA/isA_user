-- Project Service — Backfill owner_id from user_id (#463, paired with isA_#452 epic)
-- Closes the data gap left by migration 003 which added owner_id with
-- DEFAULT '' so existing rows would satisfy NOT NULL.
--
-- Idempotent: only touches rows where owner_id is empty; safe to re-run.
-- After backfill we drop the DEFAULT '' and add a CHECK constraint so
-- future inserts MUST specify a non-empty owner.

-- 1. Backfill: copy user_id into owner_id wherever owner_id is empty.
--    project_service uses `user_id` as the creator column (see
--    project_repository.create_project: effective_owner = owner_id or user_id).
UPDATE project.projects
   SET owner_id = COALESCE(NULLIF(user_id, ''), '')
 WHERE owner_id = '' OR owner_id IS NULL;

-- 2. Drop the legacy default — new rows must specify owner_id explicitly.
ALTER TABLE project.projects
    ALTER COLUMN owner_id DROP DEFAULT;

-- 3. CHECK constraint: reject empty owner_id going forward.
--    Idempotent guard so the migration can be re-applied safely.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'chk_project_projects_owner_id_nonempty'
    ) THEN
        ALTER TABLE project.projects
            ADD CONSTRAINT chk_project_projects_owner_id_nonempty
            CHECK (owner_id <> '');
    END IF;
END$$;
