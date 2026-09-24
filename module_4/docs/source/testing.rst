Testing Guide
=============

This project uses pytest with a required set of markers:

- ``web``
- ``buttons``
- ``analysis``
- ``db``
- ``integration``

Run the full suite with:

.. code-block:: bash

   cd /Users/ade/Desktop/jhu_software_concepts
   pytest module_4/tests -m "web or buttons or analysis or db or integration" \
     --cov=module_4/src --cov-report=term-missing --cov-fail-under=100

Expected selectors
------------------

The HTML must contain stable selectors for UI tests, including:

- ``data-testid="pull-data-btn"``
- ``data-testid="update-analysis-btn"``

The tests use Flask's test client and assertions on actual HTML output instead of browser interaction.

Test doubles and fixtures
-------------------------

The assignment requires reliable, deterministic tests without live scraping or manual browser clicks. The suite therefore uses small injected payloads and direct assertions on route responses and database state instead of long-running external calls.

This keeps the suite fast while still verifying the required behavior.
