# Training Service Design

`training_service` follows the existing `isA_user` microservice pattern:

- FastAPI app factory in `microservices/training_service/main.py`
- typed request/response schemas in `schemas.py`
- in-memory state store with pluggable persistence in `learning.py` and
  `persistence.py`
- route metadata for gateway/Consul registration in `routes_registry.py`
- PostgreSQL migration for durable state in `migrations/`

Course content is read through `CourseCatalog`, which points at the generated
`isA_Training/_data` directory by default and can be injected in tests. Runtime
state is held separately from the course source.

The lab path uses a deterministic adapter when sandbox execution is disabled and
the sandbox runner when execution is enabled. Trainer overrides update review
records and lab submission status before completion eligibility is calculated.
