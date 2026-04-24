# Project Service - Domain Context

## Overview

The Project Service is the user-scoped workspace boundary for `isA_user`. It stores named projects, project-specific instructions, and the storage-backed knowledge files that should travel with that project into downstream chat and agent flows.

**Business Context**: a user can maintain multiple projects, each with its own instructions and attached knowledge base. The service must keep those project assets isolated per owner while exposing enough metadata for frontend reload, session setup, and future context injection.

**Core Value Proposition**: turn an otherwise stateless chat experience into a project-aware workflow where instructions and knowledge files can be managed once and reused consistently.

---

## Business Taxonomy

### 1. Project
**Definition**: A user-owned workspace that groups instructions and knowledge assets.

**Business Purpose**:
- Provide a durable unit of organization for chat and agent work
- Store reusable custom instructions distinct from account-level instructions
- Act as the ownership boundary for attached knowledge files

**Key Attributes**:
- Project ID
- User ID
- Optional organization ID
- Name
- Description
- Custom instructions
- Created/updated timestamps

### 2. Project Knowledge File
**Definition**: A storage-backed file association attached to a project.

**Business Purpose**:
- Persist references to documents uploaded into a project knowledge base
- Allow the frontend to reload and manage existing attachments
- Decouple file blob storage from project ownership logic

**Key Attributes**:
- File ID
- Project ID
- Filename
- File type / MIME type
- File size
- Storage path
- Created timestamp

### 3. Project Owner
**Definition**: The authenticated caller who owns a project.

**Business Purpose**:
- Enforce access boundaries for CRUD and knowledge file operations
- Ensure project metadata and attached knowledge files cannot be listed or modified cross-user

---

## Domain Scenarios

### Scenario 1: Create a project
1. User submits project name and optional description/instructions.
2. Service validates per-user project limits.
3. Service creates the project record and returns the workspace metadata.

### Scenario 2: Update project instructions
1. User opens project settings.
2. User updates project-specific instructions.
3. Service verifies ownership, persists the instruction string, and returns success.

### Scenario 3: Upload a project knowledge file
1. User selects a file in project settings.
2. Service verifies project ownership.
3. Service uploads the file bytes to `storage_service`.
4. Service persists the returned storage metadata as a project file association.
5. Frontend can now reload the project and still see the attachment.

### Scenario 4: Reload the project knowledge list
1. User reopens project settings or reloads the app.
2. Frontend requests `GET /api/v1/projects/{project_id}/files`.
3. Service verifies ownership and returns the persisted associations in newest-first order.

### Scenario 5: Remove a project knowledge file
1. User deletes an attached file from project settings.
2. Service verifies ownership and the file association.
3. Service deletes the underlying storage object.
4. Service deletes the project-file association.
5. Future project reloads no longer include the file.

---

## Domain Rules

- A project belongs to exactly one owner (`user_id`) for the current implementation.
- Knowledge files are scoped through the project, not directly through ad hoc file lists.
- File blobs live in `storage_service`; `project_service` stores only the association metadata needed to manage and reload them.
- Cross-user access to a project or its files must fail with authorization or not-found semantics, never silent success.
- Removing a project knowledge file should delete both the storage object and the project association.

---

## External Dependencies

- `storage_service`: persists file bytes and returns canonical file metadata
- PostgreSQL: stores projects and project file associations
- NATS: publishes audit-style project events when available
- Auth service helpers: resolve the authenticated caller from JWT, API key, or trusted internal service headers
