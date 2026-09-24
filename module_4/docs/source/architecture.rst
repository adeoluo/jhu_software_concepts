Architecture
============

The service has three layers. Each one can be replaced by a test double, which is
how the suite runs without a network or a long scrape.

.. code-block:: text

   Browser ── GET /analysis ─────────────▶ Flask (app.py) ── query() ──▶ orm_queries ─┐
           ── POST /pull-data ───────────▶   scraper() ─▶ loader(rows) ─▶ load_data ──┼─▶ PostgreSQL
           ── POST /update-analysis ─────▶   query() (refresh cached snapshot) ──────┘   applicants

Web layer — ``app.py``
----------------------

* ``create_app(config, scraper=, loader=, query=)`` builds the Flask app. The three
  callables default to the real Module 3 functions and are injectable for tests.
* ``GET /`` and ``GET /analysis`` render ``templates/index.html`` from the latest
  analysis snapshot. Every result is labeled ``Answer:``, and percentages always
  have two decimals.
* ``POST /pull-data`` runs ``scraper()``, passes the rows to ``loader(rows)``, and
  returns ``{"ok": true, "count": N}``. It returns 409 ``{"busy": true}`` if a pull is
  already running and 500 if scraping or loading fails.
* ``POST /update-analysis`` re-runs ``query()`` and stores the new snapshot. It returns
  409 ``{"busy": true}`` and changes nothing while a pull is running.
* ``PullState`` is the thread-safe busy flag. It is exposed as
  ``app.extensions["pull_state"]`` so tests can set and observe it directly.

ETL layer — ``scrape.py``, ``auto_next_pages.py``, ``capture_chrome_html.py``, ``clean.py``, ``load_data.py``
----------------------------------------------------------------------------------------------------------------

* **Extract:** ``auto_next_pages.py`` drives a user-verified Chrome tab through the
  DevTools protocol, one page at a time. ``scrape.py`` checks ``robots.txt`` and
  parses the saved survey HTML into records. Collection stops on any
  block or challenge page instead of retrying.
* **Transform:** ``clean.py`` normalizes whitespace and status labels.
  ``load_data.record_to_row`` parses dates and scores and rejects out-of-range GRE values.
* **Load:** ``load_data.load_into_database`` creates the table if needed and upserts all
  rows in one transaction, so a failure leaves no partial writes.

Database layer — ``models.py``, ``query_data.py``, ``orm_queries.py``
---------------------------------------------------------------------

* ``models.Applicant`` maps the unchanged Module 3 ``applicants`` schema. ``p_id`` is
  the primary key.
* ``models.database_url()`` resolves the connection from ``DATABASE_URL``.
  ``models.use_database()`` lets the app or the tests point every component at a
  different database.
* ``query_data.py`` holds the raw SQL answers for Questions 1–11 and
  ``fetch_applicants()``, which returns rows as dicts keyed by the schema fields.
* ``orm_queries.py`` builds the same analyses with SQLAlchemy.
  ``analysis_snapshot()`` is what the page renders.
