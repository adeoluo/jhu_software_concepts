# Module 4: Pytest and Sphinx

Adeolu Ogunnoiki (JHED: `aogunno1`, `aogunno1@jh.edu`)

Course: Modern Software Concepts in Python (`EN.605.256.82.FA26`)

Repository SSH URL: `git@github.com:adeoluo/jhu_software_concepts.git`

Documentation (Read the Docs): **https://REPLACE-WITH-YOUR-PROJECT.readthedocs.io/**

This module is the Module 3 Grad Cafe analysis service (Flask + PostgreSQL) with
an automated pytest suite at 100% coverage, a GitHub Actions workflow that runs the
suite against PostgreSQL, and Sphinx documentation.

## Layout

```
module_4/
├── src/                  Module 3 application code (Flask, ETL, DB, queries)
├── tests/                all pytest tests, fixtures, and fakes
├── docs/source/          Sphinx project (conf.py + .rst pages)
├── docs/_build/html/     generated HTML documentation
├── pytest.ini            markers + coverage gate
├── requirements.txt      app, test, coverage, and docs dependencies
├── coverage_summary.txt  terminal coverage report
├── actions_success.png   screenshot of a green GitHub Actions run
└── .readthedocs.yaml     Read the Docs build config
```

The workflow file is at `.github/workflows/tests.yml` in the repository root.

## Setup

Run these from the repository root (`jhu_software_concepts`):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r module_4/requirements.txt
```

## Configure PostgreSQL

The app, loader, queries, and ORM all connect through `DATABASE_URL`. No credentials
are stored in the code.

```bash
createdb gradcafe_module_3        # application data
createdb gradcafe_test            # used only by the tests
```

## Run the Flask app

```bash
export DATABASE_URL=postgresql://localhost:5432/gradcafe_module_3
cd module_4/src
python load_data.py --input llm_extend_applicant_data.json   # first time only
python app.py
```

Open http://127.0.0.1:5050/analysis.

* **Pull Data** (`POST /pull-data`) scrapes new records and loads them. It returns `{"ok": true}`, or 409 `{"busy": true}` if a pull is already running.
* **Update Analysis** (`POST /update-analysis`) refreshes the page from PostgreSQL. It returns 409 `{"busy": true}` while a pull is running.

## Run the tests

Run from the **repository root** (`jhu_software_concepts`):

```bash
export DATABASE_URL=postgresql://localhost:5432/gradcafe_test
python -m pytest module_4/tests -m "web or buttons or analysis or db or integration"
```

`pytest.ini` enforces `--cov=module_4/src --cov-fail-under=100`. That path is relative to the
repository root, so running from inside `module_4/` reports 0% coverage. From `module_4/`, use
`pytest -m "web or buttons or analysis or db or integration" --cov=src` instead.

The tests refuse to run unless the database name contains `test`, because they truncate the table.
Latest result: **82 passed, 100.00% coverage** (see `coverage_summary.txt`).

## Continuous integration

`.github/workflows/tests.yml` runs on every push and pull request to `main`. It starts a
PostgreSQL 16 service container, installs `module_4/requirements.txt`, and runs the full marked
suite with the 100% coverage gate. `actions_success.png` shows a successful run.

## Build and view the documentation

```bash
python -m sphinx -b html -d module_4/docs/_build/doctrees module_4/docs/source module_4/docs/_build/html
open module_4/docs/_build/html/index.html
```

The published version is linked at the top of this file.
