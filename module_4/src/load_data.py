"""Load step of the ETL pipeline: normalize scraped records and upsert them into PostgreSQL.

Rows are keyed by ``p_id`` and written with ``INSERT ... ON CONFLICT (p_id) DO UPDATE``
inside one transaction, so reloading the same data never creates duplicates and a
failed batch leaves no partial writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import psycopg

from models import database_url


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id INTEGER PRIMARY KEY,
    program TEXT,
    university TEXT,
    comments TEXT,
    date_added DATE,
    url TEXT,
    status TEXT,
    term TEXT,
    us_or_international TEXT,
    gpa DOUBLE PRECISION,
    gre DOUBLE PRECISION,
    gre_v DOUBLE PRECISION,
    gre_aw DOUBLE PRECISION,
    degree TEXT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
)
"""

INSERT_SQL = """
INSERT INTO applicants (
    p_id,
    program,
    university,
    comments,
    date_added,
    url,
    status,
    term,
    us_or_international,
    gpa,
    gre,
    gre_v,
    gre_aw,
    degree,
    llm_generated_program,
    llm_generated_university
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (p_id) DO UPDATE SET
    program = COALESCE(EXCLUDED.program, applicants.program),
    university = COALESCE(EXCLUDED.university, applicants.university),
    comments = COALESCE(EXCLUDED.comments, applicants.comments),
    date_added = COALESCE(EXCLUDED.date_added, applicants.date_added),
    url = COALESCE(EXCLUDED.url, applicants.url),
    status = COALESCE(EXCLUDED.status, applicants.status),
    term = COALESCE(EXCLUDED.term, applicants.term),
    us_or_international = COALESCE(EXCLUDED.us_or_international, applicants.us_or_international),
    gpa = COALESCE(EXCLUDED.gpa, applicants.gpa),
    gre = COALESCE(EXCLUDED.gre, applicants.gre),
    gre_v = COALESCE(EXCLUDED.gre_v, applicants.gre_v),
    gre_aw = COALESCE(EXCLUDED.gre_aw, applicants.gre_aw),
    degree = COALESCE(EXCLUDED.degree, applicants.degree),
    llm_generated_program = COALESCE(EXCLUDED.llm_generated_program, applicants.llm_generated_program),
    llm_generated_university = COALESCE(EXCLUDED.llm_generated_university, applicants.llm_generated_university)
"""

RESULT_ID_RE = re.compile(r"/result/(\d+)", re.IGNORECASE)
DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%Y-%m-%d")


def empty_to_none(value: Any) -> Any:
    """Return ``None`` for missing or blank values; strip surrounding whitespace from strings."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def parse_date(value: Any) -> date | None:
    """Parse a Grad Cafe date such as ``Sep 10, 2026``; return ``None`` if unrecognized."""
    value = empty_to_none(value)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(str(value), date_format).date()
        except ValueError:
            continue
    return None


def parse_float(value: Any) -> float | None:
    """Parse a numeric score, ignoring thousands separators; return ``None`` if not numeric."""
    value = empty_to_none(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_gre_quantitative(value: Any) -> float | None:
    """Keep only GRE Quantitative-scale values; reject totals and malformed scores."""
    score = parse_float(value)
    return score if score is not None and 130 <= score <= 170 else None


def stable_id(record: dict[str, Any]) -> int:
    """Return the uniqueness key: the ``/result/<id>`` from the URL, else a deterministic hash."""
    url = str(empty_to_none(record.get("url")) or "")
    match = RESULT_ID_RE.search(url)
    if match:
        return int(match.group(1))

    identity = "|".join(
        str(empty_to_none(record.get(field)) or "")
        for field in ("university", "program", "status", "date_added", "raw_text")
    )
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % 2_147_483_646 + 1


def record_to_row(record: dict[str, Any]) -> tuple[Any, ...]:
    """Map a scraper/LLM record to a tuple in ``applicants`` column order."""
    return (
        stable_id(record),
        empty_to_none(record.get("program")),
        empty_to_none(record.get("university")),
        empty_to_none(record.get("comments")),
        parse_date(record.get("date_added")),
        empty_to_none(record.get("url")),
        empty_to_none(record.get("status")),
        empty_to_none(record.get("start_term") or record.get("term")),
        empty_to_none(record.get("student_type") or record.get("us_or_international")),
        parse_float(record.get("gpa")),
        parse_gre_quantitative(record.get("gre")),
        parse_gre_quantitative(record.get("gre_v")),
        parse_float(record.get("gre_aw")),
        empty_to_none(record.get("degree_level") or record.get("degree")),
        empty_to_none(
            record.get("llm-generated-program")
            or record.get("llm_generated_program")
        ),
        empty_to_none(
            record.get("llm-generated-university")
            or record.get("llm_generated_university")
        ),
    )


def load_records(input_path: Path) -> list[dict[str, Any]]:
    """Read a JSON list of records, skipping non-object entries.

    :raises ValueError: if the file does not contain a JSON list.
    """
    with input_path.open("r", encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise ValueError(f"Expected a JSON list in {input_path}")
    return [record for record in records if isinstance(record, dict)]


def psycopg_connection_string() -> str:
    """Return the configured database URL in the form psycopg expects."""
    return database_url().replace("postgresql+psycopg://", "postgresql://", 1)


def load_into_database(records: Iterable[dict[str, Any]]) -> int:
    """Create the table if needed and upsert ``records`` in one transaction; return the row count."""
    rows = [record_to_row(record) for record in records]
    with psycopg.connect(psycopg_connection_string()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            cursor.executemany(INSERT_SQL, rows)
        connection.commit()
    return len(rows)


def main() -> None:
    """Command-line entry point: ``python load_data.py --input <file.json>``."""
    parser = argparse.ArgumentParser(description="Load cleaned Grad Cafe data into PostgreSQL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("llm_extend_applicant_data.json"),
        help="Path to the Module 2 extended JSON file.",
    )
    args = parser.parse_args()
    records = load_records(args.input)
    loaded = load_into_database(records)
    print(f"Processed {loaded:,} records from {args.input}")


if __name__ == "__main__":
    main()
