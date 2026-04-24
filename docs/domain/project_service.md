# Project Service Domain Context

## Overview

The Project Service owns user-scoped project workspaces in `isA_user`. A project
is the durable container for a user's name, description, and custom
instructions that other services can later consume when assembling context for
sessions and agents.

## Core Entities

### Project
- `id`: stable project identifier
- `user_id`: owning caller
- `org_id`: optional organization scope
- `name`: display name, max 255 characters
- `description`: optional summary
- `custom_instructions`: optional long-form instructions, max 8000 characters
- `created_at` / `updated_at`: lifecycle timestamps

### Project File Reference
- `id`: file link identifier
- `project_id`: owning project
- `filename`: display name from storage
- `storage_path`: durable storage pointer
- `file_type` / `file_size`: optional metadata

## Domain Rules

1. Projects are private to their owner unless another service explicitly adds a
   collaboration model.
2. Ownership checks happen before read, update, delete, or instruction changes.
3. A user can create at most 100 projects.
4. Empty updates are invalid and must return a validation error.
5. Audit-style project events are best-effort: CRUD succeeds even if event
   publication fails.

## Bounded Context

### Internal Dependencies
- `ProjectRepository`: persistence for project records
- `ProjectService`: business rules and ownership enforcement
- `EventBusProtocol`: optional audit/event sink

### External Dependencies
- `auth_service`: caller identity resolution via shared auth dependency
- `NATS`: optional event publication for project lifecycle events
- `PostgreSQL`: project persistence through the repository layer

## Events Published
- `project.create`
- `project.read`
- `project.update`
- `project.delete`
- `project.set_instructions`

## Primary Use Cases

### UC-1: Create Project
1. Authenticated caller submits `name`, optional `description`, and optional
   `custom_instructions`.
2. Service checks the per-user project count.
3. Repository persists the project.
4. Service emits a best-effort `project.create` event.

### UC-2: Update Instructions
1. Caller requests `/api/v1/projects/{project_id}/instructions`.
2. Service verifies ownership.
3. Repository stores the new instruction text.
4. Service emits `project.set_instructions`.

### UC-3: Delete Project
1. Caller requests deletion.
2. Service verifies ownership.
3. Repository deletes the project record.
4. Service emits `project.delete`.
