"""End-to-end: fake scrape -> real PostgreSQL load -> Update Analysis -> rendered page."""

from __future__ import annotations

import re

import pytest
from bs4 import BeautifulSoup

import query_data


def answers(client) -> dict[str, str]:
    soup = BeautifulSoup(client.get("/analysis").data, "html.parser")
    return {
        card.select_one("span").get_text(strip=True): card.select_one('[data-testid="answer"]').get_text(" ", strip=True)
        for card in soup.select(".metric-card")
    }


@pytest.mark.integration
def test_pull_update_render_shows_updated_formatted_analysis(make_app, sample_records):
    client = make_app(scraper=lambda: sample_records).test_client()
    assert answers(client)["Fall 2026 entries"] == "Answer: 0"

    assert client.post("/pull-data").get_json() == {"ok": True, "count": 5}
    assert len(query_data.fetch_applicants()) == 5
    assert answers(client)["Fall 2026 entries"] == "Answer: 0", "page must not change until Update Analysis"

    assert client.post("/update-analysis").status_code == 200
    page = client.get("/analysis").get_data(as_text=True)

    assert answers(client) == {
        "Fall 2026 entries": "Answer: 3",
        "International share": "Answer: 40.00%",
        "Fall 2025 acceptances": "Answer: 50.00%",
        "Accepted Fall 2026 GPA": "Answer: 3.80",
    }
    assert "Answer: 3.70" in page  # average GPA of all five records
    assert all(re.fullmatch(r"\d+\.\d{2}%", value) for value in re.findall(r"\d[\d.]*%", page))


@pytest.mark.integration
def test_multiple_overlapping_pulls_respect_the_p_id_uniqueness_policy(make_app, make_record, row_count):
    batches = iter([
        [make_record(3001), make_record(3002, gpa="")],
        [make_record(3002, gpa="3.95"), make_record(3003)],
    ])
    client = make_app(scraper=lambda: next(batches)).test_client()

    assert client.post("/pull-data").status_code == 200
    assert client.post("/pull-data").status_code == 200

    rows = {row["p_id"]: row for row in query_data.fetch_applicants()}
    assert row_count() == 3
    assert sorted(rows) == [3001, 3002, 3003]
    assert rows[3002]["gpa"] == 3.95  # overlap updated in place instead of duplicated
