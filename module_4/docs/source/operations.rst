Operational Notes
=================

Busy-state policy
-----------------

The application is intentionally stateful during a pull. If a request is already in progress, the routes return a `409` response with a busy indicator rather than allowing overlapping work.

This keeps the app deterministic and prevents duplicate or inconsistent writes.

Idempotency and uniqueness
--------------------------

Duplicate data should not create duplicate rows. The application and tests treat the database as a unique source of truth and verify that repeated pulls do not grow the set unexpectedly.

Troubleshooting
---------------

Common local issues:

- `DATABASE_URL` not set: exports must be defined before running the app or tests.
- Coverage under 100%: check the test selection and ensure the application stays fully covered.
- CI failures: confirm the workflow starts PostgreSQL and sets the same environment variables used locally.

These issues are usually caused by small configuration mismatches rather than logic regressions.
