Architecture
============

The application follows a lightweight three-layer design.

Web layer
---------

The Flask application handles user requests and renders the analysis page. It exposes routes such as:

- ``/analysis`` for page rendering
- ``/pull-data`` for triggering the fetch and load flow
- ``/update-analysis`` for recalculating the summary state

The HTML includes stable selectors such as ``data-testid="pull-data-btn"`` and ``data-testid="update-analysis-btn"`` so end-to-end tests can validate the exact behavior without browser automation.

Data / ETL layer
----------------

The ETL workflow is represented by the logic used to pull rows, validate them, and prepare them for analysis. In the assignment-focused implementation, the data pull and summary generation are isolated so the tests can substitute fake records and validate the results without external network access.

Database layer
--------------

The SQLAlchemy model in ``models.py`` defines the applicant table structure and keeps a consistent schema for inserts and queries. The application uses `DATABASE_URL` for persistence so it can work locally and in CI with a managed PostgreSQL service.

The practical effect is a simple but stable architecture:

1. data is pulled / prepared
2. rows are inserted into the configured database
3. queries return the values used by the analysis display
4. the web route renders the summary with consistent formatting
