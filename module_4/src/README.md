# Module 3: Database Queries, SQLAlchemy, and Dynamic Webpages

Adeolu Ogunnoiki (JHED: `aogunno1`, `aogunno1@jh.edu`)

Course: Modern Software Concepts in Python (`EN.605.256.82.FA26`)

Assignment: Module 3 - Database Queries Assignment

Due: September 20, 2026 at 11:59 PM

Private repository SSH URL: `git@github.com:adeoluo/jhu_software_concepts.git`

## Project Overview

This project loads cleaned Grad Cafe application entries into PostgreSQL, answers the required questions with raw SQL, repeats selected analyses with SQLAlchemy ORM expressions, and presents the results in a dynamic Flask webpage. The database contains 100,002 copied Module 2 records and one table named `applicants`.

The analysis is descriptive. Grad Cafe entries are anonymous and self-reported, so the results should not be interpreted as representative estimates for all graduate applicants. The detailed reflection is in `limitations.pdf`.

## Files

- `load_data.py`: creates the `applicants` table and loads the copied extended JSON data with psycopg.
- `query_data.py`: executable raw SQL for Questions 1-11.
- `models.py`: SQLAlchemy 2.x `Applicant` model, engine, and session factory.
- `orm_queries.py`: SQLAlchemy versions of Questions 1, 4, 5, 8, 9, and custom Question 10, plus the webpage analysis snapshot.
- `generate_query_results_pdf.py`: creates `query_results.pdf` from live SQL results.
- `generate_limitations_pdf.py`: creates `limitations.pdf`.
- `app.py`: Flask application using SQLAlchemy for database reads.
- `templates/index.html`: analysis page.
- `static/styles.css`: page styling.
- `scrape.py`, `auto_next_pages.py`, and `capture_chrome_html.py`: copied Module 2 scraper functionality used by Pull Data.
- `screenshots/`: raw SQL, SQLAlchemy, and Flask evidence images.
- `github.txt`: private repository SSH URL.

## Setup

PostgreSQL is provided locally by Postgres.app. Start the PostgreSQL 18 server before running the project. The project database is named `gradcafe_module_3` and the local PostgreSQL user is `ade`.

From this directory, create and activate the virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Set connection variables in each new Terminal session. The password is intentionally not stored in this repository:

```bash
export PGDATABASE=gradcafe_module_3
export PGUSER=ade
export PGHOST=localhost
export PGPORT=5432
unset PGPASSWORD
```

The code also accepts a complete `DATABASE_URL` environment variable. Never commit credentials, `.env` files, or database dumps.

## Load Data

The copied Module 2 extended data file is used by default. To load it explicitly:

```bash
python load_data.py --input llm_extend_applicant_data.json
```

The loader creates exactly one table, `applicants`, converts blank optional values to SQL `NULL`, parses dates and numeric fields, keeps GRE Quantitative and Verbal values only on the 130-170 scale, and updates existing primary-key rows rather than creating duplicates. Re-running the loader is safe; the verified database remains at 100,002 rows and 100,002 unique IDs.

## Raw SQL Analysis

Run all Questions 1-11:

```bash
python query_data.py
```

The two original questions are:

1. Which five universities have the most Fall 2026 applicant entries?
2. What is the average GPA for American and international applicants who provide a GPA?

Generate the required PDF from the same live database:

```bash
python generate_query_results_pdf.py --output query_results.pdf
```

## SQLAlchemy ORM

Run the required ORM analyses:

```bash
python orm_queries.py
```

`orm_queries.py` uses SQLAlchemy `select`, `where`, `func.count`, `func.avg`, `group_by`, `order_by`, and `limit` expressions. It does not use raw SQL strings or psycopg cursors. The ORM results were checked against the equivalent raw SQL results.

## Flask Application

Start Flask on a free local port. Port 5050 avoids a macOS AirTunes conflict observed on port 5000:

```bash
flask --app app run --host 127.0.0.1 --port 5050
```

Open `http://127.0.0.1:5050/` in a browser. The page reads analysis values through the SQLAlchemy `Applicant` model and displays all required results plus the two original questions.

`Update Analysis` re-queries the current PostgreSQL database and does not start a scrape. `Pull Data` starts the copied Module 2 workflow in a background process, loads newly captured records, uses a lock to prevent simultaneous pulls, and reports success, failure, blocking, and in-progress states to the user. The scraper stops when the public source presents a block or verification challenge rather than attempting to bypass it.

## SQL Versus ORM Comparison

For Question 10, raw SQL directly states the grouping, count, ordering, and limit in the database language, which makes the exact query easy to inspect and debug. SQLAlchemy expresses the same operations through Python objects and methods, reducing repeated SQL string handling and integrating naturally with the `Applicant` model used by Flask. The ORM provides useful abstraction and helps share model-based database logic across the application. Direct SQL remains more concise for this assignment's fixed analysis and provides precise control over the generated statement.

## Evidence and Reflection

The required screenshots are stored in `screenshots/`:

- `raw_sql_output.png`
- `sqlalchemy_orm_output.png`
- `flask_analysis_page.png`

Generate the written reflection with:

```bash
python generate_limitations_pdf.py
```

This creates `limitations.pdf` with two substantive paragraphs discussing selection bias, self-reporting, missingness, reliability, representativeness, and the difference between database contents and broader conclusions.

## Submission Hygiene

The final ZIP must contain the completed `module_3` folder but must exclude `.venv`, `__pycache__`, `.DS_Store`, temporary scraper data, lock files, secrets, and database dumps. `module_2.zip` is outside the module and is never part of the submission.

The Canvas submission must be a single file named `module_3.zip` containing the completed `module_3` folder. The final ZIP and the GitHub `module_3` folder must contain the same required project files and evidence.

Before submission, run syntax checks, verify both PDFs, inspect all three screenshots, compare the ZIP contents with the final GitHub `module_3` contents, and confirm that no credentials or secrets are included.
