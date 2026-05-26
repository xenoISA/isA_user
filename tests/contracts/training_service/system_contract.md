# Training Service System Contract

## API Surface

The service exposes `/api/v1/training` routes for health, catalog, learner
progress, cohorts, attendance, labs, review, and completion eligibility.

## Persistence

Runtime state is persisted through the training persistence adapter. The initial
implementation supports memory and JSON file persistence, with SQL schema
coverage in `migrations/001_create_training_schema.sql`.

## Integration

- Gateway and Consul route metadata come from `routes_registry.py`.
- Local dev and Helm registration use port `8262`.
- Course source data is read-only and injected through `CourseCatalog`.

## Testing

The service has focused unit tests for catalog loading, persistence round-trip,
offline cohort attendance, lab review override, and completion eligibility, plus
smoke tests for import and health contract coverage.
