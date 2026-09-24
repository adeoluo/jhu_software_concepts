"""Shared fixtures: an isolated PostgreSQL test database, an app factory, and fake data."""

from __future__ import annotations

import os
from typing import Any, Callable
from urllib.parse import urlparse

import psycopg
import pytest


def _test_database_url() -> str:
    """Resolve the test database URL and refuse to run against a database not named ``*test*``."""
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.exit(
            "Set DATABASE_URL to a PostgreSQL test database, "
            "e.g. export DATABASE_URL=postgresql://localhost:5432/gradcafe_test",
            returncode=2,
        )
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    if "test" not in urlparse(url).path.lower():
        pytest.exit("Refusing to run: the tests truncate tables, so the database name must contain 'test'.", returncode=2)
    return url


TEST_DATABASE_URL = _test_database_url()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture
def db_url() -> str:
    """Empty ``applicants`` table in the test database; returns its URL."""
    import load_data

    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute(load_data.CREATE_TABLE_SQL)
        connection.execute("TRUNCATE applicants")
    return TEST_DATABASE_URL


@pytest.fixture
def row_count(db_url: str) -> Callable[[], int]:
    """Return a function that counts the rows currently in ``applicants``."""

    def count() -> int:
        with psycopg.connect(db_url) as connection:
            return connection.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]

    return count


@pytest.fixture
def make_record() -> Callable[..., dict[str, Any]]:
    """Build a raw record in the same shape the Module 3 scraper + LLM step produce."""

    def build(
        result_id: int,
        *,
        university: str = "Johns Hopkins University",
        program: str = "Computer Science",
        status: str = "Accepted",
        term: str = "Fall 2026",
        student_type: str = "International",
        gpa: str = "3.90",
        gre: str = "165",
        gre_v: str = "160",
        gre_aw: str = "4.5",
        degree: str = "Masters",
        llm_program: str | None = None,
        llm_university: str | None = None,
    ) -> dict[str, Any]:
        return {
            "url": f"https://www.thegradcafe.com/result/{result_id}",
            "program": program,
            "university": university,
            "status": status,
            "date_added": "Sep 10, 2026",
            "start_term": term,
            "student_type": student_type,
            "gpa": gpa,
            "gre": gre,
            "gre_v": gre_v,
            "gre_aw": gre_aw,
            "degree_level": degree,
            "comments": "",
            "raw_text": f"{university} {program} {status}",
            "llm-generated-program": llm_program or program,
            "llm-generated-university": llm_university or university,
        }

    return build


@pytest.fixture
def sample_records(make_record: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    """Five records with hand-computable analysis answers (see the integration test)."""
    return [
        make_record(1001),
        make_record(1002, university="Stanford University", student_type="American", gpa="3.70",
                    gre="168", gre_v="158", gre_aw="4.0", degree="PhD"),
        make_record(1003, university="MIT", program="Physics", status="Rejected", student_type="American",
                    gpa="3.50", gre="160", gre_v="155", gre_aw="3.5", degree="PhD"),
        make_record(1004, term="Fall 2025", gpa="3.80"),
        make_record(1005, term="Fall 2025", status="Rejected", student_type="American", gpa="3.60"),
    ]


@pytest.fixture
def snapshot() -> dict[str, Any]:
    """A fixed analysis snapshot for page tests that do not need the database."""
    return {
        "q1": 32600,
        "q2": 48.9234,
        "q3": {"gpa": 3.7612, "gre": 165.381, "gre_v": 158.2, "gre_aw": 4.1},
        "q4": 3.8,
        "q5": 39.2812,
        "q6": 3.85,
        "q7": 12,
        "q8": 4,
        "q9": 6,
        "q10": [("Stanford University", 120), ("MIT", 99)],
        "q11": [("american", 3.7), ("international", 3.65)],
        "q9_difference": 2,
    }


@pytest.fixture
def make_app(db_url: str) -> Callable[..., Any]:
    """Create a testing app bound to the test database; pass scraper/loader/query fakes as kwargs."""
    import app as app_module

    def build(**kwargs: Any) -> Any:
        return app_module.create_app({"TESTING": True, "DATABASE_URL": db_url}, **kwargs)

    return build
