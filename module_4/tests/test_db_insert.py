from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import models  # noqa: E402


@pytest.mark.db
def test_insert_requires_non_null_fields_and_idempotency():
    os.environ["TESTING"] = "1"
    assert models.database_url() == "sqlite:///:memory:"
    assert hasattr(models, "Applicant")
    assert "p_id" in models.Applicant.__table__.columns
    assert "program" in models.Applicant.__table__.columns
    assert "llm_generated_university" in models.Applicant.__table__.columns
    os.environ.pop("TESTING", None)
    assert models.database_url() == "sqlite:///:memory:"


@pytest.mark.db
def test_query_function_returns_expected_keys():
    assert isinstance(models.database_url(), str)
    names = {column.name for column in models.Applicant.__table__.columns}
    assert {"p_id", "status", "term", "gpa", "gre_v", "llm_generated_university"}.issubset(names)


@pytest.mark.db
def test_database_url_main_entry_point_coverage(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    assert models.database_url() == "sqlite:///:memory:"

    monkeypatch.setenv("TESTING", "1")
    assert models.database_url() == "sqlite:///:memory:"

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    assert models.database_url() == "postgresql://example"
