# Training Service Domain Context

`training_service` owns operational training state for offline isA training delivery.
It does not own the source course content; course catalogs and assets remain in
`isA_Training` and are loaded read-only.

The service tracks:

- learner enrollment and resume progress
- offline cohort assignment and attendance
- learner timeline events
- sandbox/lab submissions and evaluation results
- trainer review overrides
- completion proof eligibility

The domain boundary is user/organization operations. Generated course decks,
handbooks, and course-source metadata stay outside this service.
