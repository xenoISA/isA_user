# Project Service - Logic Contract

This document defines the business rules the test pyramid should enforce for `project_service`.

---

## Business Rules

### BR-001: Project ownership gates all access

Given a `project_id` and authenticated caller:

- if the project does not exist, the service returns `404`
- if the project exists but belongs to another user, the service returns `403`
- otherwise the caller may read, update, delete, and manage the project knowledge files

### BR-002: Project instructions are first-class project state

- each project may store `custom_instructions`
- instruction updates must be bounded to 8000 characters
- instruction updates require ownership of the project

### BR-003: Knowledge file upload is storage-backed

When a caller uploads a project knowledge file:

1. the service verifies project ownership
2. the file bytes are uploaded to `storage_service`
3. the returned storage metadata is persisted as a project-file association
4. the API returns a `ProjectFileResponse`

Failure modes:

- storage upload failure -> `502 storage_error`
- missing project -> `404`
- unauthorized caller -> `403`

### BR-004: Knowledge file listing is durable across reload

- `GET /api/v1/projects/{project_id}/files` returns the persisted file associations
- results are sorted newest first
- response shape is `{files, total}`
- listing requires project ownership

### BR-005: Knowledge file deletion removes both layers

When a caller deletes a project knowledge file:

1. the service verifies project ownership
2. the service verifies the file association exists on the project
3. the underlying storage object is deleted
4. the project-file association row is deleted
5. the API returns `204 No Content`

Failure modes:

- missing file association -> `404`
- storage deletion failure -> `502 storage_error`

---

## API Contract Summary

### Create project
- `POST /api/v1/projects`
- response: `201 ProjectResponse`

### List projects
- `GET /api/v1/projects`
- response: `200 {projects, total}`

### Update instructions
- `PUT /api/v1/projects/{project_id}/instructions`
- response: `200 {"message": "Instructions updated"}`

### List project files
- `GET /api/v1/projects/{project_id}/files`
- response: `200 ProjectFileListResponse`

### Upload project file
- `POST /api/v1/projects/{project_id}/files`
- request: multipart/form-data with `file`
- response: `201 ProjectFileResponse`

### Delete project file
- `DELETE /api/v1/projects/{project_id}/files/{file_id}`
- response: `204 No Content`

---

## Event Expectations

If an event bus is configured, successful project operations publish audit-style events:

- `project.create`
- `project.read`
- `project.update`
- `project.delete`
- `project.set_instructions`
- `project.upload_file`
- `project.delete_file`

Each event payload should include:

- `user_id`
- `project_id`
- `action`
- `success`
- optional `detail`
- timestamp
