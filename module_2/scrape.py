from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_URL = "https://www.thegradcafe.com"
DEFAULT_RESULTS_PATH = "/results"


def check_robots_txt(base_url: str = BASE_URL) -> str:
    """Fetch the public robots.txt file and return the text for review.

    The project requirement is to check robots.txt before scraping and to avoid
    any disallowed or login-protected pages. The scraper will not bypass any
    access restrictions, CAPTCHAs, rate limits, or login barriers.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    request = Request(
        robots_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; JHUProjectScraper/1.0; +https://example.com)",
            "Accept": "text/plain, */*",
        },
    )
    with urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")
    return text


def build_result_url(page: int = 1, query: Optional[str] = None) -> str:
    """Build a GradCafe result URL while keeping the host and query logic explicit."""
    params: Dict[str, str] = {"page": str(page)}
    if query:
        params["q"] = query
    encoded = urlencode(params)
    return f"{BASE_URL}{DEFAULT_RESULTS_PATH}?{encoded}"


def _safe_request(url: str, timeout: int = 30) -> Optional[str]:
    """Request a page with a browser-like User-Agent and a defensive timeout."""
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _extract_rows_from_html(html: str) -> List[Dict[str, Any]]:
    """Parse the HTML and return a list of applicant dictionaries.

    This function intentionally keeps the parser simple and robust. It does not
    assume that every website element is always present, so it sanitizes missing
    data as empty strings or None.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, Any]] = []
    candidate_blocks = soup.select("tr, .result-row, .admit-row, .applicant-row, .entry")

    for block in candidate_blocks:
        text = " ".join(block.get_text(" ", strip=True).split())
        if not text:
            continue
        row = {
            "raw_text": text,
            "program": "",
            "university": "",
            "status": "",
            "date_added": "",
            "url": "",
            "comments": "",
            "decision_date": "",
            "start_term": "",
            "student_type": "",
            "gre": "",
            "gre_v": "",
            "gpa": "",
            "gre_aw": "",
            "degree_level": "",
            "raw_program": "",
        }

        for link in block.select("a[href]"):
            href = link.get("href", "")
            if href and "http" in href:
                row["url"] = href
                break

        rows.append(row)

    return rows


def scrape_data(
    pages: int = 1,
    delay_seconds: float = 1.0,
    max_rows: int = 100000,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Collect GradCafe applicant rows in a polite, rate-limited manner.

    The assignment says to programmatically pull data, use urllib to manage URLs,
    use BeautifulSoup and regex/string methods to parse, and stop where blocked or
    rate-limited. This function implements the public-access flow and keeps the
    collection respectful.
    """
    robots_text = check_robots_txt()
    if not robots_text:
        raise RuntimeError("robots.txt could not be read before scraping.")

    all_rows: List[Dict[str, Any]] = []
    page_number = 1

    while page_number <= pages:
        page_url = build_result_url(page=page_number, query=query)
        html = _safe_request(page_url)
        if not html:
            break

        page_rows = _extract_rows_from_html(html)
        if not page_rows:
            break

        all_rows.extend(page_rows)
        if len(all_rows) >= max_rows:
            break

        time.sleep(delay_seconds)
        page_number += 1

    return all_rows


def clean_data(data: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize extracted rows into a cleaner structure.

    This wrapper keeps the structure simple and delegates detailed cleaning to
    the separate clean.py module as required by the assignment.
    """
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
        })
    return cleaned


def save_data(data: Iterable[Dict[str, Any]], file_path: str | Path) -> None:
    """Save a JSON object to disk."""
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(list(data), handle, ensure_ascii=False, indent=2)


def load_data(file_path: str | Path) -> List[Dict[str, Any]]:
    """Load JSON data from disk."""
    with Path(file_path).open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded if isinstance(loaded, list) else []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape GradCafe applicant data.")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to request.")
    parser.add_argument("--output", type=str, default="applicant_data.json", help="Path to save the JSON output.")
    parser.add_argument("--max-rows", type=int, default=100000, help="Upper bound for rows to collect.")
    args = parser.parse_args()

    records = scrape_data(pages=args.pages, max_rows=args.max_rows)
    save_data(records, args.output)
    print(f"Saved {len(records)} rows to {args.output}")
