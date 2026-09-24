Overview and Setup
==================

The Grad Café analytics service provides a small Flask application for viewing analysis output, pulling new data, and updating summary results. The project is designed to be deterministic and testable, with a clear separation between the web layer, application logic, and database access.

Prerequisites
-------------

- Python 3.11+
- PostgreSQL instance or a local test database
- pip-based dependency installation

Environment variables
---------------------

Set the database connection before running the app or tests:

.. code-block:: bash

   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/gradcafe"

The app reads this value through the environment and uses it to create the SQLAlchemy connection string.

Local run
---------

From the project root:

.. code-block:: bash

   cd /Users/ade/Desktop/jhu_software_concepts/module_4/src
   python app.py

Then browse to:

- http://127.0.0.1:5000/analysis

Running tests
-------------

Run the required application tests with coverage from the repository root:

.. code-block:: bash

   cd /Users/ade/Desktop/jhu_software_concepts
   pytest module_4/tests -m "web or buttons or analysis or db or integration" \
     --cov=module_4/src --cov-report=term-missing --cov-fail-under=100

This command validates the Flask rendering, button behavior, analysis formatting, and database writes using the project markers.
