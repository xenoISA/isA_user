# Training Service PRD

## Goal

Provide a first-class `isA_user` microservice for offline training operations.
The current product priority is not online course playback; it is cohort
enrollment, attendance tracking, lab evaluation, testing, review, and completion
proof readiness.

## Requirements

- Load course catalogs from `isA_Training` without mutating source content.
- Persist learner progress and operational state inside `isA_user`.
- Support organization cohorts with start/end windows and delivery status.
- Record offline attendance as timeline events.
- Expose lab definitions and evaluate lab submissions.
- Allow trainer review queue inspection and overrides.
- Calculate completion eligibility from progress, quiz, lab, and attendance state.

## Non-Goals

- Duplicating the whole `isA_Training` content repository.
- Building a full online LMS playback runtime.
- Moving training state into `isA_Data`.
