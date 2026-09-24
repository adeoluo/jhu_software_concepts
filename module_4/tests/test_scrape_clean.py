"""ETL: robots.txt checks, HTML parsing, and cleaning (network replaced by fakes)."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

import clean
import scrape
from fakes import ALLOW_ALL_ROBOTS, DENY_SURVEY_ROBOTS, fake_urlopen

SRC = Path(scrape.__file__).resolve().parent

SURVEY_HTML = """
<table>
  <tr><td>Recent results</td></tr>
  <tr><td>Stanford University</td><td>Computer Science PhD</td><td>Sep 10, 2026</td>
      <td>Accepted on Sep 1</td><td><a href="/result/111">See more</a></td></tr>
  <tr><td>Fall 2026 International GPA 3.90 GRE 165 GRE V 160 GRE AW 4.5</td></tr>
  <tr><td>Great interview experience</td></tr>
  <tr><td>Advertisement</td></tr>
  <tr><td></td></tr>
  <tr><td>12 Total Comments here</td></tr>
  <tr><td>MIT</td><td>Physics</td><td>Sep 11, 2026</td><td>Wait listed</td>
      <td><a href="https://www.thegradcafe.com/result/222">See more</a></td></tr>
  <tr><td>GRE, Quantitative: 166, Verbal: 158, Analytical Writing: 4.0 Spring 2027 American</td></tr>
  <tr><td>Yale University</td><td>History Masters</td><td>Sep 12, 2026</td><td>Rejected</td></tr>
</table>
"""


@pytest.fixture
def robots(monkeypatch):
    """Serve robots.txt from memory; returns a setter to switch policies."""

    def use(text: str) -> None:
        monkeypatch.setattr(scrape, "urlopen", fake_urlopen(text))
        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen(text))

    use(ALLOW_ALL_ROBOTS)
    return use


@pytest.fixture
def survey_file(tmp_path):
    path = tmp_path / "survey.html"
    path.write_text(SURVEY_HTML, encoding="utf-8")
    return path


@pytest.mark.integration
def test_robots_policy_is_fetched_and_enforced(robots, tmp_path):
    assert scrape.check_robots_txt() == ALLOW_ALL_ROBOTS
    assert scrape.robots_allows("https://www.thegradcafe.com/survey") is True
    assert scrape.verify_collection_allowed() == ALLOW_ALL_ROBOTS
    scrape.save_robots_evidence(tmp_path / "allowed.txt")
    assert "Allowed for JHUProjectScraper/1.0: True" in (tmp_path / "allowed.txt").read_text()

    robots(DENY_SURVEY_ROBOTS)
    assert scrape.robots_allows("https://www.thegradcafe.com/survey", DENY_SURVEY_ROBOTS) is False
    with pytest.raises(PermissionError):
        scrape.verify_collection_allowed()
    with pytest.raises(PermissionError):
        scrape.save_robots_evidence(tmp_path / "denied.txt")
    assert "Allowed for JHUProjectScraper/1.0: False" in (tmp_path / "denied.txt").read_text()


@pytest.mark.integration
def test_build_result_url_adds_cursor_and_query():
    assert scrape.build_result_url() == "https://www.thegradcafe.com/survey"
    assert scrape.build_result_url(cursor="abc", query="cs") == "https://www.thegradcafe.com/survey?cursor=abc&q=cs"


@pytest.mark.integration
def test_saved_survey_html_is_parsed_into_records(robots, survey_file):
    records = scrape.scrape_data(survey_file)

    assert [record["university"] for record in records] == ["Stanford University", "MIT", "Yale University"]
    stanford, mit, yale = records
    assert stanford["url"] == "https://www.thegradcafe.com/result/111"
    assert (stanford["program"], stanford["degree_level"], stanford["status"]) == ("Computer Science", "PhD", "Accepted")
    assert stanford["decision_date"] == "Sep 1"
    assert (stanford["start_term"], stanford["student_type"]) == ("Fall 2026", "International")
    assert (stanford["gpa"], stanford["gre"], stanford["gre_v"], stanford["gre_aw"]) == ("3.90", "165", "160", "4.5")
    assert stanford["comments"] == "Great interview experience"
    assert mit["url"] == "https://www.thegradcafe.com/result/222"
    assert (mit["status"], mit["start_term"], mit["student_type"]) == ("Waitlisted", "Spring 2027", "American")
    assert (yale["url"], yale["degree_level"], yale["status"]) == ("", "Masters", "Rejected")


@pytest.mark.integration
def test_scrape_clean_save_and_load_round_trip(tmp_path, survey_file):
    rows = scrape.clean_data(scrape.scrape_data_from_html_file(survey_file) + [{"program": "Math"}])
    scrape.save_data(rows, tmp_path / "out" / "rows.json")
    (tmp_path / "dict.json").write_text("{}", encoding="utf-8")

    assert scrape.load_data(tmp_path / "out" / "rows.json") == rows
    assert rows[-1]["raw_program"] == "Math" and rows[-1]["status"] == ""
    assert scrape.load_data(tmp_path / "dict.json") == []


@pytest.mark.integration
def test_scrape_command_line(robots, survey_file, tmp_path, monkeypatch, capsys):
    script = str(SRC / "scrape.py")
    output = tmp_path / "applicant_data.json"

    monkeypatch.setattr(sys, "argv", ["scrape.py", "--check-robots", "--robots-output", str(tmp_path / "r.txt")])
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(script, run_name="__main__")
    assert exited.value.code == 0

    monkeypatch.setattr(sys, "argv", ["scrape.py"])
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(script, run_name="__main__")
    assert exited.value.code == 2

    monkeypatch.setattr(sys, "argv", ["scrape.py", "--html-file", str(survey_file), "--output", str(output)])
    runpy.run_path(script, run_name="__main__")
    assert len(json.loads(output.read_text())) == 3
    assert "Saved 3 rows" in capsys.readouterr().out


@pytest.mark.integration
def test_clean_normalizes_text_and_status(tmp_path):
    rows = clean.clean_data([
        {"program": "  Computer   Science ", "status": "admitted", "university": None},
        {"raw_text": "Physics listing", "status": "Pending"},
    ])

    assert rows[0]["program"] == "Computer Science" and rows[0]["status"] == "Accepted"
    assert rows[0]["university"] == ""
    assert rows[1]["raw_program"] == "Physics listing" and rows[1]["status"] == "Pending"
    assert clean._normalize_text(None) == ""

    clean.save_data(rows, tmp_path / "c.json")
    (tmp_path / "dict.json").write_text("{}", encoding="utf-8")
    assert clean.load_data(tmp_path / "c.json") == rows
    assert clean.load_data(tmp_path / "dict.json") == []


@pytest.mark.integration
def test_clean_command_line(tmp_path, monkeypatch, capsys):
    script = str(SRC / "clean.py")
    source, output = tmp_path / "raw.json", tmp_path / "clean.json"
    source.write_text(json.dumps([{"program": "Math", "status": "rejected"}]), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["clean.py", "--input", str(source), "--output", str(output)])
    runpy.run_path(script, run_name="__main__")
    assert json.loads(output.read_text())[0]["status"] == "Rejected"
    assert "Cleaned 1 rows" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["clean.py", "--input", str(tmp_path / "missing.json")])
    with pytest.raises(FileNotFoundError):
        runpy.run_path(script, run_name="__main__")
