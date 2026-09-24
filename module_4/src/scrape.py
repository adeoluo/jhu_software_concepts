from __future__ import annotations

import argparse
import json
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen

import certifi
from bs4 import BeautifulSoup

BASE_URL = "https://www.thegradcafe.com"
DEFAULT_RESULTS_PATH = "/survey"
USER_AGENT = "JHUProjectScraper/1.0"


def check_robots_txt(base_url: str = BASE_URL) -> str:
    """Fetch the public robots.txt file and return the text for review.

    This assignment requires compliance with robots.txt before scraping. The
    flow is intentionally restricted to publicly visible pages and avoids any
    bypass, login, or rate-limit evasion.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    request = Request(
        robots_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/plain, */*",
        },
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=30, context=ssl_context) as response:
        text = response.read().decode("utf-8", errors="replace")
    return text


def build_result_url(cursor: Optional[str] = None, query: Optional[str] = None) -> str:
    """Build a public GradCafe survey URL using its cursor pagination."""
    params: Dict[str, str] = {}
    if cursor:
        params["cursor"] = cursor
    if query:
        params["q"] = query
    query_string = urlencode(params)
    url = f"{BASE_URL}{DEFAULT_RESULTS_PATH}"
    return f"{url}?{query_string}" if query_string else url


def robots_allows(target_url: str, robots_text: Optional[str] = None) -> bool:
    """Return whether robots.txt permits this project's user agent."""
    parser = RobotFileParser()
    parser.set_url(urljoin(BASE_URL, "/robots.txt"))
    parser.parse((robots_text or check_robots_txt()).splitlines())
    return parser.can_fetch(USER_AGENT, target_url)


def verify_collection_allowed(target_url: str = f"{BASE_URL}{DEFAULT_RESULTS_PATH}") -> str:
    """Fetch robots.txt and stop unless the target URL is permitted."""
    robots_text = check_robots_txt()
    if not robots_allows(target_url, robots_text):
        raise PermissionError(f"robots.txt does not permit collection from {target_url}")
    return robots_text


def save_robots_evidence(
    file_path: str | Path,
    target_url: str = f"{BASE_URL}{DEFAULT_RESULTS_PATH}",
) -> None:
    """Save the checked policy, target, timestamp, and permission result."""
    robots_text = check_robots_txt()
    allowed = robots_allows(target_url, robots_text)
    evidence = (
        f"Source: {urljoin(BASE_URL, '/robots.txt')}\n"
        f"Target checked: {target_url}\n"
        f"Checked UTC: {datetime.now(timezone.utc).isoformat()}\n"
        f"Allowed for {USER_AGENT}: {allowed}\n\n"
        f"{robots_text}"
    )
    Path(file_path).write_text(evidence, encoding="utf-8")
    if not allowed:
        raise PermissionError(f"robots.txt does not permit collection from {target_url}")


DECISION_RE = re.compile(
    r"\b(accepted|rejected|wait\s*listed|interview(?:ed)?)\b(?:\s+on\s+([A-Z][a-z]{2}\s+\d{1,2}))?",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b")
TERM_RE = re.compile(r"\b(Fall|Spring|Summer|Winter)\s+(\d{4})\b", re.IGNORECASE)
DEGREE_LEVEL_RE = re.compile(r"\b(PhD|Masters?|MFA|MBA|PsyD|EdD|JD|MD|Other)\s*$", re.IGNORECASE)
# Alternate GRE format seen on some listings, e.g. "GRE, Quantitative: 165, Verbal: 159, Analytical Writing: 4"
GRE_QVA_RE = re.compile(
    r"GRE,?\s*Quantitative:?\s*(\d{2,3}).*?Verbal:?\s*(\d{2,3}).*?(?:Analytical Writing|AW):?\s*(\d(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


def _text(element: Any) -> str:
    """Normalize element text by stripping and collapsing inner whitespace."""
    return " ".join(element.get_text(" ", strip=True).split())


def _first_match(pattern: re.Pattern[str], text: str, group: int = 0) -> str:
    """Return the matched group text if pattern matches, else empty string."""
    match = pattern.search(text)
    return match.group(group).strip() if match else ""


def _parse_primary_row(entry: Any) -> Optional[Dict[str, Any]]:
    """Parse a main applicant row table entry into a structured dictionary."""
    cells = entry.find_all(["td", "th"], recursive=False)
    cell_text = [_text(cell) for cell in cells]
    full_text = " ".join(value for value in cell_text if value)
    decision = DECISION_RE.search(full_text)
    date_added = DATE_RE.search(full_text)
    if len(cell_text) < 4 or not decision or not date_added:
        return None

    raw_program = cell_text[1]
    degree_match = DEGREE_LEVEL_RE.search(raw_program)
    degree_level = degree_match.group(1) if degree_match else ""
    program = raw_program[:degree_match.start()].strip() if degree_match else raw_program

    record: Dict[str, Any] = {
        "raw_text": full_text,
        "program": program,
        "university": cell_text[0],
        "status": "Waitlisted" if decision.group(1).lower().replace(" ", "") == "waitlisted" else decision.group(1).title(),
        "date_added": date_added.group(0),
        "url": "",
        "comments": "",
        "decision_date": decision.group(2) or "",
        "start_term": "",
        "student_type": "",
        "gre": "",
        "gre_v": "",
        "gpa": "",
        "gre_aw": "",
        "degree_level": degree_level,
        "raw_program": raw_program,
    }
    link = entry.select_one("a[href]")
    if link:
        href = link.get("href", "")
        record["url"] = href if href.startswith("http") else urljoin(BASE_URL, href)
    return record


def _merge_detail_text(record: Dict[str, Any], detail_text: str) -> None:
    """Extract academic metrics, term, and student type from detail sub-rows."""
    term = TERM_RE.search(detail_text)
    if term:
        record["start_term"] = f"{term.group(1).title()} {term.group(2)}"

    student_type = re.search(r"\b(American|International|Other)\b", detail_text, re.IGNORECASE)
    if student_type:
        record["student_type"] = student_type.group(1).title()

    score_patterns = {
        "gre": re.compile(r"\bGRE\s*:?\s+(?!V\b|AW\b)(\d{2,4})\b", re.IGNORECASE),
        "gre_v": re.compile(r"\bGRE\s*V\s*:?\s+(\d{2,3})\b", re.IGNORECASE),
        "gre_aw": re.compile(r"\bGRE\s*AW\s*:?\s+(\d(?:\.\d{1,2})?)\b", re.IGNORECASE),
        "gpa": re.compile(r"\bGPA\s+(\d(?:\.\d{1,3})?)\b", re.IGNORECASE),
    }
    for field, pattern in score_patterns.items():
        record[field] = _first_match(pattern, detail_text, 1)


def _extract_rows_from_saved_html(html: str) -> List[Dict[str, Any]]:
    """Parse one applicant record from each GradCafe result group."""
    soup = BeautifulSoup(html, "html.parser")
    records: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for entry in soup.select("tr"):
        primary = _parse_primary_row(entry)
        if primary:
            if current:
                records.append(current)
            current = primary
            continue

        if not current:
            continue
        detail_text = _text(entry)
        if not detail_text or detail_text.lower() in {"advertisement", "total comments"}:
            continue
        current["raw_text"] = f"{current['raw_text']} {detail_text}".strip()
        quant_match = GRE_QVA_RE.search(detail_text)
        if quant_match:
            current["gre"] = current["gre"] or quant_match.group(1)
            current["gre_v"] = current["gre_v"] or quant_match.group(2)
            current["gre_aw"] = current["gre_aw"] or quant_match.group(3)
            detail_text = (detail_text[: quant_match.start()] + detail_text[quant_match.end() :]).strip(" ,")
        if TERM_RE.search(detail_text):
            _merge_detail_text(current, detail_text)
        elif detail_text and "total comments" not in detail_text.lower():
            current["comments"] = " ".join(filter(None, [current["comments"], detail_text]))

    if current:
        records.append(current)

    return records


def scrape_data_from_html_file(file_path: str | Path) -> List[Dict[str, Any]]:
    """Read a saved GradCafe HTML page and parse it into applicant records."""
    path = Path(file_path)
    html = path.read_text(encoding="utf-8", errors="replace")
    return _extract_rows_from_saved_html(html)


def scrape_data(
    html_file: str | Path,
) -> List[Dict[str, Any]]:
    """Collect records from saved browser-captured HTML as the real working approach.

    The assignment note indicates that direct urllib or Selenium scraping is often
    blocked by Cloudflare, while a hybrid browser capture approach works reliably
    for a given page. This function therefore expects a saved HTML file that was
    captured from a user-verified browser session.
    """
    verify_collection_allowed()

    return scrape_data_from_html_file(html_file)


def clean_data(data: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize extracted rows into a cleaner structure for analysis."""
    cleaned: List[Dict[str, Any]] = []
    for item in data:
        cleaned.append({
            "program": item.get("program") or "",
            "university": item.get("university") or "",
            "status": item.get("status") or "",
            "date_added": item.get("date_added") or "",
            "url": item.get("url") or "",
            "comments": item.get("comments") or "",
            "decision_date": item.get("decision_date") or "",
            "start_term": item.get("start_term") or "",
            "student_type": item.get("student_type") or "",
            "gre": item.get("gre") or "",
            "gre_v": item.get("gre_v") or "",
            "gpa": item.get("gpa") or "",
            "gre_aw": item.get("gre_aw") or "",
            "degree_level": item.get("degree_level") or "",
            "raw_program": item.get("raw_program") or item.get("program") or "",
            "raw_text": item.get("raw_text") or "",
        })
    return cleaned


def save_data(data: Iterable[Dict[str, Any]], file_path: str | Path) -> None:
    """Save a JSON object to disk atomically so a crash mid-write cannot corrupt the file."""
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(list(data), handle, ensure_ascii=False, indent=2)
    temp_path.replace(output_path)


def load_data(file_path: str | Path) -> List[Dict[str, Any]]:
    """Load JSON data from disk."""
    with Path(file_path).open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded if isinstance(loaded, list) else []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape GradCafe applicant data from captured HTML pages.")
    parser.add_argument("--html-file", type=str, default=None, help="Path to saved browser-captured GradCafe HTML.")
    parser.add_argument("--output", type=str, default="applicant_data.json", help="Path to save the JSON output.")
    parser.add_argument("--check-robots", action="store_true", help="Save robots.txt evidence and exit.")
    parser.add_argument("--robots-output", default="robots_evidence.txt", help="Path for robots.txt evidence.")
    args = parser.parse_args()

    if args.check_robots:
        save_robots_evidence(args.robots_output)
        print(f"Saved robots.txt evidence to {args.robots_output}")
        raise SystemExit(0)
    if not args.html_file:
        parser.error("--html-file is required unless --check-robots is used")

    records = scrape_data(args.html_file)
    save_data(records, args.output)
    print(f"Saved {len(records)} rows to {args.output}")
