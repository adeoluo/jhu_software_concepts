"""SQL/ORM analysis reports and the Module 3 PDF generators."""

from __future__ import annotations

import runpy
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import generate_limitations_pdf
import generate_query_results_pdf
import load_data
import orm_queries
import query_data

SRC = Path(query_data.__file__).resolve().parent


@pytest.fixture
def loaded(db_url, sample_records):
    load_data.load_into_database(sample_records)
    return sample_records


@pytest.mark.db
@pytest.mark.analysis
def test_sql_queries_report_formatted_answers(loaded, capsys, monkeypatch):
    results = query_data.run_queries()
    lines = list(query_data.format_results(results))

    assert set(results) == set(query_data.SQL_QUERIES) == set(query_data.QUESTION_TEXT)
    assert "Fall 2026 applicant count: 3" in lines
    assert "Percent international: 40.00%" in lines
    assert "Fall 2025 acceptance percentage: 50.00%" in lines
    assert "  Stanford University: 1" in lines and "  American: 3.60" in lines
    assert query_data.format_number(None) == "N/A"

    query_data.main()
    monkeypatch.setattr(sys, "argv", ["query_data.py"])
    runpy.run_path(str(SRC / "query_data.py"), run_name="__main__")
    assert capsys.readouterr().out.count("Percent international: 40.00%") == 2


@pytest.mark.db
@pytest.mark.analysis
def test_orm_queries_match_the_sql_answers(loaded, capsys):
    results = orm_queries.run_orm_queries()
    lines = list(orm_queries.format_results(results))
    snapshot = orm_queries.analysis_snapshot()

    assert "ORM Question 1 count: 3" in lines
    assert "ORM Question 5 acceptance percentage: 50.00%" in lines
    assert snapshot["q1"] == 3 and snapshot["q7"] == 3 and snapshot["q8"] == snapshot["q9"] == 1
    assert snapshot["q9_difference"] == 0
    assert set(snapshot) == {"q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10", "q11", "q9_difference"}

    orm_queries.main()
    runpy.run_path(str(SRC / "orm_queries.py"), run_name="__main__")
    assert capsys.readouterr().out.count("ORM Question 1 count: 3") == 2


@pytest.mark.analysis
@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "N/A"), (3.14159, "3.14"), (Decimal("39.2812"), "39.28"), (7, "7")],
)
def test_report_value_formatting_uses_two_decimals(value, expected):
    assert orm_queries.format_value(value) == expected
    assert generate_query_results_pdf.format_value(value) == expected


@pytest.mark.db
@pytest.mark.analysis
def test_query_results_pdf_is_generated(loaded, tmp_path, monkeypatch, capsys):
    results = query_data.run_queries()
    assert generate_query_results_pdf.result_lines("Question 11", results) == [
        "American average GPA: 3.60", "International average GPA: 3.85",
    ]

    generate_query_results_pdf.build_pdf(tmp_path / "direct.pdf")
    monkeypatch.setattr(sys, "argv", ["generate_query_results_pdf.py", "--output", str(tmp_path / "main.pdf")])
    generate_query_results_pdf.main()
    runpy.run_path(str(SRC / "generate_query_results_pdf.py"), run_name="__main__")

    for name in ("direct.pdf", "main.pdf"):
        assert (tmp_path / name).read_bytes().startswith(b"%PDF")
    assert capsys.readouterr().out.count("Saved") == 2


@pytest.mark.analysis
def test_limitations_pdf_is_generated(tmp_path, monkeypatch, capsys):
    generate_limitations_pdf.build_pdf(tmp_path / "direct.pdf")
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(SRC / "generate_limitations_pdf.py"), run_name="__main__")

    assert (tmp_path / "direct.pdf").read_bytes().startswith(b"%PDF")
    assert (tmp_path / "limitations.pdf").read_bytes().startswith(b"%PDF")
    assert "Saved limitations.pdf" in capsys.readouterr().out
