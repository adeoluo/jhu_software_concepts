Operational Notes
=================

Busy-state policy
-----------------

* Only one Pull Data runs at a time. ``PullState.try_start()`` sets the busy flag
  under a lock, so a second concurrent request gets ``409 {"busy": true}``.
* While a pull is running, Update Analysis returns ``409 {"busy": true}`` and keeps the
  current snapshot. The page never shows a half-loaded dataset.
* The busy flag is cleared on success and on failure. A failed pull never leaves the
  buttons locked.
* The page disables both buttons and shows **Pull in progress** while the flag is set.

Idempotency strategy and uniqueness key
---------------------------------------

* The uniqueness key is ``p_id``, the primary key. ``load_data.stable_id`` takes it from
  the Grad Cafe result URL (``/result/<id>``). If there is no URL, it uses a
  deterministic SHA-256 hash of university, program, status, date, and raw text.
* Rows are written with ``INSERT ... ON CONFLICT (p_id) DO UPDATE``, so pulling the same
  data twice leaves the row count unchanged. An overlapping row is updated in place, and
  ``COALESCE`` keeps existing values when the new record has a blank field.
* The whole batch runs in one transaction. If any row fails, nothing from that pull is kept.

Troubleshooting
---------------

``Set DATABASE_URL to a PostgreSQL test database`` when running pytest
   Export ``DATABASE_URL=postgresql://localhost:5432/gradcafe_test`` first.

``Refusing to run: ... must contain 'test'``
   This guard stops the suite from truncating your real data. Use a separate test database.

``connection refused`` / ``database "gradcafe_test" does not exist``
   Start PostgreSQL (``pg_isready``) and run ``createdb gradcafe_test``.

Coverage fails with paths like ``src/app.py`` not found
   Run pytest from the repository root, not from ``module_4/``.

CI: service container fails to start (Docker exit code 125)
   Docker health-check flags must be ``--health-cmd``, ``--health-interval``,
   ``--health-timeout``, and ``--health-retries``. An unknown flag stops the container from being created.

CI: invalid workflow file
   Quote YAML values that contain ``:`` or ``*`` and keep indentation consistent.

Pull Data stops with a challenge/blocked message
   Grad Cafe served a verification or rate-limit page. The scraper stops instead of
   bypassing it. Complete the verification in Chrome and try again later.
