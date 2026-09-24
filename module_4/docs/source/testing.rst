Testing Guide
=============

Running the suite
-----------------

From the repository root, with ``DATABASE_URL`` pointing to a database whose name contains ``test``:

.. code-block:: bash

   export DATABASE_URL=postgresql://localhost:5432/gradcafe_test
   python -m pytest module_4/tests -m "web or buttons or analysis or db or integration"

``module_4/pytest.ini`` adds ``--cov=module_4/src --cov-report=term-missing
--cov-fail-under=100``. The run fails unless every line in ``src/`` is covered. The
suite finishes in a few seconds and never touches the internet.

Markers
-------

Every test has at least one marker, so the command above runs the entire suite.

===============  ============================================================
Marker           Covers
===============  ============================================================
``web``          App factory, routes, page load and HTML structure
``buttons``      ``/pull-data`` and ``/update-analysis``, busy gating, errors
``analysis``     ``Answer:`` labels, two-decimal percentages, report formatting
``db``           Schema, inserts, uniqueness, query functions, DB helpers
``integration``  Pull → update → render flows, ETL scripts driven by fakes
===============  ============================================================

Run one group with, for example, ``pytest module_4/tests -m db``. Coverage is enforced
only on full runs.

Test files
----------

* ``test_flask_page.py`` — ``create_app`` config and routes, ``GET /analysis`` components
* ``test_buttons.py`` — Pull Data / Update Analysis, 409 busy gating, loader errors
* ``test_analysis_format.py`` — ``Answer:`` labels, two-decimal percentage regex
* ``test_db_insert.py`` — inserts, duplicate pulls, no partial writes, ``fetch_applicants``
* ``test_integration_end_to_end.py`` — pull → update → render, overlapping pulls
* ``test_scrape_clean.py``, ``test_browser_capture.py``, ``test_reports.py`` — the remaining
  Module 3 code, so coverage reaches 100%

UI selectors
------------

Tests read the HTML with BeautifulSoup through these stable selectors:

* ``[data-testid="pull-data-btn"]`` — the Pull Data button
* ``[data-testid="update-analysis-btn"]`` — the Update Analysis button
* ``[data-testid="answer"]`` — every rendered analysis value (text starts with ``Answer:``)
* ``[data-testid="pull-status"]`` — the busy/status banner
* ``[data-testid="page-title"]`` — the page heading

Fixtures (``tests/conftest.py``)
--------------------------------

* ``db_url`` — creates the ``applicants`` table if needed, truncates it, and returns the test URL
* ``row_count`` — returns a function that counts rows in ``applicants``
* ``make_app`` — ``make_app(scraper=..., loader=..., query=...)`` returns a testing app bound to the test DB
* ``make_record`` / ``sample_records`` — raw records in the scraper's output shape;
  the five sample records have hand-checked answers (3 Fall 2026 entries, 40.00%
  international, 50.00% Fall 2025 acceptances)
* ``snapshot`` — a fixed analysis snapshot for page tests that don't need the DB

Test doubles
------------

* **Injected callables:** ``create_app(scraper=lambda: rows)`` replaces the network
  scrape. ``Spy`` in ``test_buttons.py`` records loader and query calls.
* **Busy state:** tests set ``app.extensions["pull_state"].running = True`` directly.
  The suite never uses ``sleep()``.
* **``tests/fakes.py``:** ``fake_urlopen`` (robots.txt / DevTools HTTP),
  ``FakeWebSocket`` (DevTools messages), ``FakeClock`` (deterministic ``time``),
  and ``FakeBrowser`` in ``test_browser_capture.py`` (page sequence for the capture loop).
