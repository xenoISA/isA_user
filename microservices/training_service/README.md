# Training Service

Operational training runtime for the isA user platform.

`isA_Training` remains the course/content source repository. This service reads
course catalog, course JSON, question bank, and K12 seed files from
`../isA_Training/_data` by default, or from `TRAINING_CONTENT_ROOT` when set.

## Owns

- Learner enrollments and progress
- Lesson completion and submissions
- Quiz attempts and scoring
- Sandbox session and evaluation records
- Completion proof issue and verification
- Organization cohorts, dashboards, and review activity

## Does Not Own

- User identity, organization membership, or RBAC. Those come from `isA_user`
  auth, organization, and authorization services.
- Course source assets. Those remain in `isA_Training`.
- Analytics/RAG projections. Those can be published downstream to `isA_Data`.

## Local

```bash
TRAINING_CONTENT_ROOT=../isA_Training/_data \
PYTHONPATH="$PWD" \
python -m uvicorn microservices.training_service.main:app --reload --port 8262
```

## Persistence

Local/test runs default to in-memory state, or JSON when `TRAINING_STATE_PATH`
is set. Production should use the user-platform database:

```bash
TRAINING_PERSISTENCE_BACKEND=postgres
TRAINING_DATABASE_URL=postgresql://postgres:password@localhost:5432/isa_platform
```

This keeps learner state under `isA_user` ownership. `isA_Data` should consume
analytics/projection events later, not own the operational training workflow.
