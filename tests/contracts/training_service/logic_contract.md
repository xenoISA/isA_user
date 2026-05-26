# Training Service Logic Contract

## Enrollment And Progress

- A learner can enroll in a course once.
- Lesson/activity completion updates resume state and progress percentage.
- Progress state is runtime state and must not modify `isA_Training` content.

## Cohort Operations

- Cohort assignment is idempotent for duplicate learner ids.
- Attendance is recorded as a learner timeline event.
- Completion eligibility requires attendance when a learner is assigned through a
  cohort for the target course.

## Lab Evaluation

- Lab submissions produce a score, pass flag, feedback, audit trail, and review
  status.
- Failed lab submissions are not proof eligible until a trainer override approves
  the item.

## Completion Eligibility

Eligibility is true only when course progress, entry quiz, lab status, and
attendance requirements are satisfied.
