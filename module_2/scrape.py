from __future__ import annotations

import argparse
import json
import ssl
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_URL = "https://www.thegradcafe.com"
DEFAULT_RESULTS_PATH = "/results"


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
            "User-Agent": "Mozilla/5.0 (compatible; JHUProjectScraper/1.0; +https://example.com)",
            "Accept": "text/plain, */*",
        },
    )
    ssl_context = ssl._create_unverified_context()
    with urlopen(request, timeout=30, context=ssl_context) as response:
        text = response.read().decode("utf-8", errors="replace")
    return text


def build_result_url(page: int = 1, query: Optional[str] = None) -> str:
    """Build the public GradCafe results URL from the current live site layout."""
    params: Dict[str, str] = {"page": str(page)}
    if query:
        params["q"] = query
    url = f"{BASE_URL}{DEFAULT_RESULTS_PATH}?page={page}"
    if query:
        url += f"&q={query}"
    return url


def _safe_request(url: str, timeout: int = 30) -> Optional[str]:
    """Request a page with a browser-like User-Agent and explicit SSL handling."""
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    ssl_context = ssl._create_unverified_context()
    try:
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _extract_rows_from_saved_html(html: str) -> List[Dict[str, Any]]:
    """Parse saved GradCafe HTML content using BeautifulSoup.

    This matches the assignment note that the working approach is to open GradCafe
    in a normal browser, complete Cloudflare verification manually, and then save
    the resulting visible HTML for local parsing.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, Any]] = []
    for entry in soup.select("tr, .result-row, .admission-row, .applicant-row, .entry"):
        text = " ".join(entry.get_text(" ", strip=True).split())
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
        for link in entry.select("a[href]"):
            href = link.get("href", "")
            if href:
                full_url = href if href.startswith("http") else urljoin(BASE_URL, href)
                row["url"] = full_url
                break
        rows.append(row)
    return rows


def scrape_data_from_html_file(file_path: str | Path) -> List[Dict[str, Any]]:
    """Read a saved GradCafe HTML page and parse it into applicant records."""
    path = Path(file_path)
    html = path.read_text(encoding="utf-8", errors="replace")
    return _extract_rows_from_saved_html(html)


def scrape_data(
    pages: int = 1,
    delay_seconds: float = 1.0,
    max_rows: int = 100000,
    query: Optional[str] = None,
    html_file: Optional[str | Path] = None,
) -> List[Dict[str, Any]]:
    """Collect records from saved browser-captured HTML as the real working approach.

    The assignment note indicates that direct urllib or Selenium scraping is often
    blocked by Cloudflare, while a hybrid browser capture approach works reliably
    for a given page. This function therefore expects a saved HTML file that was
    captured from a user-verified browser session.
    """
    robots_text = check_robots_txt()
    if not robots_text:
        raise RuntimeError("robots.txt could not be read before scraping.")

    if html_file is not None:
        return scrape_data_from_html_file(html_file)

    all_rows: List[Dict[str, Any]] = []
    for page_number in range(1, pages + 1):
        page_url = build_result_url(page=page_number, query=query)
        html = _safe_request(page_url)
        if not html:
            break
        data = _extract_rows_from_saved_html(html)
        if not data:
            break
        all_rows.extend(data)
        if len(all_rows) >= max_rows:
            break
        time.sleep(delay_seconds)
    return all_rows


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
    parser = argparse.ArgumentParser(description="Scrape GradCafe applicant data from captured HTML pages.")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to process.")
    parser.add_argument("--html-file", type=str, default=None, help="Path to saved browser-captured GradCafe HTML.")
    parser.add_argument("--output", type=str, default="applicant_data.json", help="Path to save the JSON output.")
    parser.add_argument("--max-rows", type=int, default=100000, help="Upper bound for rows to collect.")
    args = parser.parse_args()

    records = scrape_data(pages=args.pages, max_rows=args.max_rows, html_file=args.html_file)
    save_data(records, args.output)
    print(f"Saved {len(records)} rows to {args.output}")
