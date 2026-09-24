"""PostgreSQL writes, uniqueness, the query function, and the DB helpers."""

from __future__ import annotations

import json
import runpy
import sys
from datetime import date, datetime
from pathlib import Path

import psycopg
import pytest

import load_data
import models
import orm_queries
import query_data

SRC = Path(load_data.__file__).resolve().parent
REQUIRED_FIELDS = ("p_id", "program", "university", "url", "status", "date_added", "term")
TEMPLATE_KEYS = {"q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10", "q11", "q9_difference"}


@pytest.mark.db
def test_pull_data_inserts_rows_with_required_fields(make_app, sample_records, row_count):
    assert row_count() == 0

    response = make_app(scraper=lambda: sample_records).test_client().post("/pull-data")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "count": 5}
    rows = query_data.fetch_applicants()
    assert [row["p_id"] for row in rows] == [1001, 1002, 1003, 1004, 1005]
    for row in rows:
        assert all(row[field] is not None for field in REQUIRED_FIELDS), row
    assert rows[0]["date_added"] == date(2026, 9, 10)
    assert rows[0]["gpa"] == 3.9 and rows[0]["gre"] == 165.0


@pytest.mark.db
def test_duplicate_pulls_do_not_duplicate_rows(make_app, sample_records, row_count):
    client = make_app(scraper=lambda: sample_records).test_client()

    assert client.post("/pull-data").status_code == 200
    assert client.post("/pull-data").status_code == 200

    assert row_count() == len(sample_records)


@pytest.mark.db
def test_loader_failure_returns_500_with_no_partial_writes(make_app, make_record, row_count):
    records = [make_record(2001), make_record(99_999_999_999)]  # second id overflows INTEGER

    response = make_app(scraper=lambda: records).test_client().post("/pull-data")

    assert response.status_code == 500
    assert row_count() == 0


@pytest.mark.db
def test_query_function_returns_dicts_with_module_3_keys(db_url, sample_records):
    load_data.load_into_database(sample_records)

    rows = query_data.fetch_applicants()
    limited = query_data.fetch_applicants(limit=2)

    assert len(rows) == 5 and len(limited) == 2
    assert all(isinstance(row, dict) and tuple(row) == query_data.APPLICANT_FIELDS for row in rows)
    assert rows[1]["university"] == "Stanford University"


@pytest.mark.db
def test_analysis_query_returns_the_keys_the_template_uses(db_url, sample_records):
    load_data.load_into_database(sample_records)

    snapshot = orm_queries.analysis_snapshot()

    assert set(snapshot) == TEMPLATE_KEYS
    assert set(snapshot["q3"]) == {"gpa", "gre", "gre_v", "gre_aw"}
    assert snapshot["q1"] == 3


@pytest.mark.db
def test_table_matches_module_3_schema(db_url):
    with psycopg.connect(db_url) as connection:
        columns = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'applicants' ORDER BY ordinal_position"
        ).fetchall()
        primary_key = connection.execute(
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'applicants'::regclass AND i.indisprimary"
        ).fetchall()

    assert tuple(name for (name,) in columns) == query_data.APPLICANT_FIELDS
    assert tuple(models.Applicant.__table__.columns.keys()) == query_data.APPLICANT_FIELDS
    assert primary_key == [("p_id",)]


@pytest.mark.db
def test_database_url_prefers_override_then_env_then_pg_vars(monkeypatch):
    monkeypatch.setattr(models, "_override_url", "postgresql://override/test_db")
    assert models.database_url() == "postgresql://override/test_db"

    monkeypatch.setattr(models, "_override_url", None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://env/test_db")
    assert models.database_url() == "postgresql://env/test_db"

    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("PGUSER", "grader")
    monkeypatch.setenv("PGPASSWORD", "p@ss word")
    monkeypatch.setenv("PGDATABASE", "gradcafe_test")
    assert models.database_url() == "postgresql+psycopg://grader:p%40ss+word@localhost:5432/gradcafe_test"

    monkeypatch.delenv("PGPASSWORD")
    assert models.database_url() == "postgresql+psycopg://grader@localhost:5432/gradcafe_test"

    monkeypatch.delenv("PGUSER")
    monkeypatch.delenv("USER", raising=False)
    with pytest.raises(RuntimeError, match="Set DATABASE_URL"):
        models.database_url()


@pytest.mark.db
def test_sqlalchemy_url_selects_psycopg_driver():
    assert models.sqlalchemy_url("postgresql://h/db") == "postgresql+psycopg://h/db"
    assert models.sqlalchemy_url("postgresql+psycopg://h/db") == "postgresql+psycopg://h/db"


@pytest.mark.db
def test_value_parsers_normalize_scraped_strings():
    assert load_data.empty_to_none(None) is None
    assert load_data.empty_to_none("  ") is None
    assert load_data.empty_to_none(" x ") == "x"
    assert load_data.empty_to_none(4) == 4

    assert load_data.parse_date("Sep 10, 2026") == date(2026, 9, 10)
    assert load_data.parse_date("2026-09-10") == date(2026, 9, 10)
    assert load_data.parse_date(datetime(2026, 9, 10, 8, 30)) == date(2026, 9, 10)
    assert load_data.parse_date(date(2026, 9, 10)) == date(2026, 9, 10)
    assert load_data.parse_date("not a date") is None
    assert load_data.parse_date("") is None

    assert load_data.parse_float("3,000.5") == 3000.5
    assert load_data.parse_float(3) == 3.0
    assert load_data.parse_float("n/a") is None
    assert load_data.parse_float(None) is None

    assert load_data.parse_gre_quantitative("165") == 165.0
    assert load_data.parse_gre_quantitative("330") is None
    assert load_data.parse_gre_quantitative(None) is None


@pytest.mark.db
def test_stable_id_uses_result_url_or_a_deterministic_hash():
    assert load_data.stable_id({"url": "https://www.thegradcafe.com/result/42"}) == 42
    no_url = {"university": "MIT", "program": "Physics", "status": "Accepted"}
    assert load_data.stable_id(no_url) == load_data.stable_id(dict(no_url))
    assert 1 <= load_data.stable_id(no_url) < 2_147_483_647


@pytest.mark.db
def test_record_to_row_accepts_both_scraper_and_schema_key_names():
    row = load_data.record_to_row({
        "url": "/result/7", "term": "Spring 2026", "us_or_international": "American", "degree": "PhD",
        "llm_generated_program": "Chemistry", "llm_generated_university": "Yale University",
    })
    assert row[0] == 7
    assert row[7:9] == ("Spring 2026", "American")
    assert row[13:] == ("PhD", "Chemistry", "Yale University")


@pytest.mark.db
def test_load_records_reads_json_lists_only(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps([{"url": "/result/1"}, "skip-me"]), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    assert load_data.load_records(good) == [{"url": "/result/1"}]
    with pytest.raises(ValueError, match="Expected a JSON list"):
        load_data.load_records(bad)


@pytest.mark.db
def test_load_data_command_line_loads_json_file(tmp_path, monkeypatch, capsys, sample_records, row_count):
    source = tmp_path / "records.json"
    source.write_text(json.dumps(sample_records), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["load_data.py", "--input", str(source)])

    load_data.main()
    runpy.run_path(str(SRC / "load_data.py"), run_name="__main__")

    assert capsys.readouterr().out.count("Processed 5 records") == 2
    assert row_count() == 5
