Overview & Setup
================

Requirements
------------

* Python 3.13
* PostgreSQL 14+ (local install such as Postgres.app, or the CI service container)

Install
-------

Run from the repository root (``jhu_software_concepts``):

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r module_4/requirements.txt

Environment variables
---------------------

``DATABASE_URL`` (required)
   PostgreSQL connection URL used by the Flask app, the loader, the SQL queries,
   and the SQLAlchemy ORM, e.g. ``postgresql://localhost:5432/gradcafe_module_3``.
   Tests may override it with ``create_app({"DATABASE_URL": ...})``.

``PGUSER`` / ``PGPASSWORD`` / ``PGHOST`` / ``PGPORT`` / ``PGDATABASE`` (optional)
   Used to build the URL only when ``DATABASE_URL`` is not set.

``TEST_DATABASE_URL`` (optional)
   Used by the test suite instead of ``DATABASE_URL``. The database name must contain
   ``test`` because the tests truncate the ``applicants`` table.

``PORT`` (optional)
   Port for the development server (default ``5050``).

No credentials are stored in the code; supply them through these variables.

Create the databases
--------------------

.. code-block:: bash

   createdb gradcafe_module_3   # application data
   createdb gradcafe_test       # used only by pytest

Load data and run the app
-------------------------

.. code-block:: bash

   export DATABASE_URL=postgresql://localhost:5432/gradcafe_module_3
   cd module_4/src
   python load_data.py --input llm_extend_applicant_data.json
   python app.py

Open http://127.0.0.1:5050/analysis.

Run the tests
-------------

.. code-block:: bash

   export DATABASE_URL=postgresql://localhost:5432/gradcafe_test
   python -m pytest module_4/tests -m "web or buttons or analysis or db or integration"

Run this from the repository root so ``--cov=module_4/src`` in ``pytest.ini`` resolves.
See :doc:`testing` for details.

Build these docs
----------------

.. code-block:: bash

   python -m sphinx -b html -d module_4/docs/_build/doctrees module_4/docs/source module_4/docs/_build/html
