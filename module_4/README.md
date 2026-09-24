# Module 4: Pytest and Sphinx

This project contains the pytest suite and Sphinx documentation for the Grad Café analytics application. The app is intentionally kept testable through a Flask factory and uses dependency injection patterns so tests can validate behavior without live network access.

## Overview

The application exposes a lightweight Flask interface for:

- rendering the analysis page
- handling "Pull Data" and "Update Analysis" requests
- tracking busy-state behavior
- formatting analysis summaries consistently
- connecting to PostgreSQL via `DATABASE_URL`

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
cd /Users/ade/Desktop/jhu_software_concepts
python -m pip install --upgrade pip
python -m pip install -r module_4/requirements.txt
```

3. Configure the database connection:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/gradcafe"
```

This can also be set in your shell profile or environment manager for convenience.

## Run the application

From the repo root:

```bash
cd /Users/ade/Desktop/jhu_software_concepts/module_4/src
python app.py
```

Then open:

- http://127.0.0.1:5000/analysis

## Run the tests

Run the full marked suite with coverage:

```bash
cd /Users/ade/Desktop/jhu_software_concepts
pytest module_4/tests -m "web or buttons or analysis or db or integration" \
  --cov=module_4/src --cov-report=term-missing --cov-fail-under=100
```

This is the required assignment command and it must pass with 100% coverage for the code under `module_4/src`.

## Sphinx docs

The local Sphinx source lives in `module_4/docs/source` and can be built with:

```bash
cd /Users/ade/Desktop/jhu_software_concepts
sphinx-build -b html module_4/docs/source module_4/docs/_build/html
```

Then open the generated landing page:

```bash
open module_4/docs/_build/html/index.html
```

For a Read the Docs deployment, connect the GitHub repo to Read the Docs and point it at the built Sphinx project.

## Architecture summary

The project follows a simple layered design:

- Web layer: Flask routes and rendered HTML templates / response objects
- ETL / data layer: data loading, scraping, and analysis logic
- Database layer: SQLAlchemy model and PostgreSQL-backed persistence

This separation keeps the app easy to test and the data operations deterministic.

## Testing notes

The test suite uses stable selectors such as:

- `data-testid="pull-data-btn"`
- `data-testid="update-analysis-btn"`

The Flask test client is used for all HTTP assertions and state checks, avoiding manual UI interaction.

## Operational notes

- The busy-state flag is observable and injected into the routes so tests can validate `409` responses without arbitrary sleeps.
- Idempotency is preserved by ensuring duplicate data does not create duplicate rows.
- The app expects `DATABASE_URL` to be set for non-test deployments and allows test overrides for isolated validation.

## References

- [module_4/docs/source/index.rst](module_4/docs/source/index.rst)
- [module_4/tests](module_4/tests)
- [module_4/src/app.py](module_4/src/app.py)
- [module_4/src/models.py](module_4/src/models.py)
