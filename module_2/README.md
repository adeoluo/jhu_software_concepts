# Module 2: GradCafe Data Collection and Standardization

## Name

Adeolu Ogunnoiki (JHED: aogunno1, aogunno1@jh.edu)

## Module Info

- **Module:** Module 2 — Web Scraping Assignment
- **Course:** Modern Software Concepts in Python, EN.605.256.82.FA26
- **Due:** September 13, 2026 at 11:59 PM

## Approach

This project collects public graduate-admissions results from [The GradCafe](https://www.thegradcafe.com), converts the captured results into structured JSON, cleans the fields, and uses the supplied local LLM project to standardize program and university names. The personal project target is 100,000 unique applicant records, exceeding the assignment minimum of 30,000.

The collection workflow follows the September 7, 2026 assignment update, since a plain `urllib`/Selenium scrape is blocked by Cloudflare on this site. A normal Chrome session (launched with `--remote-debugging-port`) handles Cloudflare's human verification manually, one time. `capture_chrome_html.py`/`auto_next_pages.py` then connect to that already-verified Chrome tab over the Chrome DevTools Protocol (via `websocket-client`), read `document.documentElement.outerHTML`, and click the page's own "Next" control to paginate — no bypass of Cloudflare, CAPTCHA, or rate limits occurs, and only the public `/survey` results are visited. Selenium is not used.

Each captured page is parsed by `scrape.py` with BeautifulSoup: `_extract_rows_from_saved_html` walks each `<tr>`, uses `_parse_primary_row` to pull a primary applicant row (university, raw program text, status, date added, URL) via regex (`DECISION_RE`, `DATE_RE`, `DEGREE_LEVEL_RE`), then folds in the following detail sub-rows (comments, term, student type, GRE/GRE V/GRE AW/GPA) with `_merge_detail_text`. `auto_next_pages.py` runs this in a loop: it dedupes every record by a composite key (`university`, `raw_program`, `status`, `date_added`, `decision_date`, `raw_text`), merges new unique rows into `applicant_data.json`, waits 2 seconds between pages as a polite throttle, and scans each page for Cloudflare/rate-limit/challenge text (`_looks_blocked`) — if detected, it raises immediately and stops instead of retrying or working around the restriction. Progress is written to `data/html/` and `data/json/` per page and merged into `applicant_data.json` after every page (using an atomic temp-file-then-rename write in `save_data`), so an interrupted run never loses previously collected rows and can resume from the last captured page's "Next" link.

`clean.py` then produces a deterministic cleaned copy: `_normalize_text` collapses whitespace and standardizes missing values to `""`, and `_normalize_status` maps status synonyms (e.g., "admitted" → "Accepted") to a consistent vocabulary, while `raw_program`/`raw_text` are always preserved unmodified alongside the cleaned fields for traceability.

Finally, the supplied `llm_hosting/` project (TinyLlama via `llama-cpp-python`, with `canon_universities.txt`/`canon_programs.txt` canonical lists and difflib fuzzy matching) standardizes `program`/`university` into `llm-generated-program`/`llm-generated-university`, added on top of the cleaned row without altering the original fields. `llm_hosting/app.py`'s CLI was extended (beyond the file as originally supplied) with `--out`, `--append`, and `--final-json` flags so that a 100,000-row LLM pass writes JSON Lines incrementally and can resume after an interruption instead of restarting from row 0; `_cli_process_file` counts completed lines in the existing output file and skips that many input rows before continuing. No changes were made to `canon_universities.txt`/`canon_programs.txt` beyond the versions supplied with the assignment.

## Requirements

- Python 3.10 or later
- Google Chrome
- The Python packages in `requirements.txt`
- The separate packages in `llm_hosting/requirements.txt` for the LLM stage

Create and activate a virtual environment from the `module_2` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, the terminal prompt normally begins with `(.venv)`. Install the collector dependencies into that environment:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Keep the environment active while running the collection, tests, and cleaning commands in this README. When finished, leave it with:

```bash
deactivate
```

## Project Files

- `scrape.py`: robots.txt validation, cursor URL construction, captured-HTML parsing, and JSON helpers
- `capture_chrome_html.py`: captures one verified Chrome page
- `auto_next_pages.py`: captures successive pages, resumes existing work, and incrementally merges unique records
- `clean.py`: deterministic field normalization that preserves raw source text
- `llm_hosting/`: supplied local LLM project, adapted to standardize both program and university
- `robots_evidence.txt`: saved robots.txt evidence collected before applicant data
- `screenshot.jpg`: visual evidence of the robots.txt review (browser screenshot of `thegradcafe.com/robots.txt`)
- `RobotsTxT Screenshots.pdf`: additional visual evidence of the robots.txt review, same content as `screenshot.jpg`

## Collection Workflow

First, save and review robots.txt before collecting applicant records:

```bash
python3 scrape.py --check-robots --robots-output robots_evidence.txt
```

Launch a separate Chrome instance with remote debugging and open the public survey page:

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.gradcafe-chrome-profile" \
  "https://www.thegradcafe.com/survey"
```

After completing any normal browser verification and confirming that the results table is visible, run:

```bash
python3 auto_next_pages.py \
  --start-url "https://www.thegradcafe.com/survey" \
  --target-rows 100000 \
  --merged-output applicant_data.json
```

Temporary page HTML and page-level JSON are written under `data/html/` and `data/json/`. The merged dataset is rewritten after every successful page, so an interrupted run retains completed work. On restart, the helper loads existing page JSON and continues its page numbering.
It reads the last saved HTML page's `Next` link and returns Chrome to that exact cursor, so resuming does not depend on which page the browser currently displays. A fresh output directory always begins at `--start-url`.

## Cleaning and LLM Standardization

Create the deterministic cleaned dataset:

```bash
python3 clean.py \
  --input applicant_data.json \
  --output cleaned_applicant_data.json
```

Run the supplied local LLM from its directory. Its CLI writes JSON Lines incrementally so partial progress survives interruption:

```bash
cd llm_hosting
python3 app.py \
  --file ../cleaned_applicant_data.json \
  --out ../llm_standardization_progress.jsonl \
  --append \
  --final-json ../llm_extend_applicant_data.json
```

Each standardized row retains the source fields and adds `llm-generated-program` and `llm-generated-university`.

## Data Fields

Each parsed applicant object contains the university, program, degree level, status, date added, decision date, start term, student type, GRE scores, GPA, comments, source URL, raw program text, and full raw listing text. Missing values are represented by empty strings rather than invented values.

## Compliance

The collection code reads robots.txt and confirms that `/survey` is permitted before processing pages. It does not access sign-in, profile, registration, or other disallowed paths. It does not bypass Cloudflare, CAPTCHA, authentication, or rate limits. The captured policy is preserved in `robots_evidence.txt`, and `screenshot.jpg`/`RobotsTxT Screenshots.pdf` provide visual evidence of the review.

During collection, `auto_next_pages.py` waits 2 seconds between page requests as a polite throttle and scans each captured page for Cloudflare challenge, access-denied, or rate-limit markers (for example, "Just a moment", "Attention Required", "Access Denied", "Too Many Requests"). If any marker is found, collection stops immediately with a `BlockedError` instead of retrying or attempting to bypass the restriction.

## Known Bugs

- Regex-based field extraction (GRE/GRE V/GRE AW/GPA, term, student type) depends on GradCafe's current wording and can miss a field on a row phrased unusually; the row is still kept with that field set to `""` rather than dropped or guessed. `scrape.py` currently handles both "GRE 163" and "GRE, Quantitative: 165, Verbal: 159, Analytical Writing: 4" phrasings; a data audit after the first ~37,500 rows found only 1 row using the second phrasing and 14 rows using a colon format ("GRE: 740"), both now covered and backfilled into `applicant_data.json` from the preserved `raw_text`. Fix for any future gaps: expand the relevant regex in `scrape.py`/`_merge_detail_text` as new phrasings are found.
- GPA values are stored exactly as reported without assuming a 4.0 scale, so a small number of rows show values above 4.3 (for example 8.69, 9.10) because some applicants report on a 10-point or percentage scale. This is intentional (the assignment requires not altering applicant-provided data), but downstream analysis should treat `gpa` as scale-ambiguous rather than always-4.0.
- If the `data/html/` page cache is deleted (as happened once during development), the resume logic loses its exact pagination cursor and a restart begins again from `--start-url`, re-walking already-collected pages before reaching new ones. No data is lost (`applicant_data.json` and its `data/json/` page cache are unaffected and are reseeded on resume), but the run takes longer. Fix: avoid deleting `data/html/`, or extend `auto_next_pages.py` to persist the last "Next" URL separately from the per-page HTML files.
- GradCafe can change its page structure or pagination controls, which may require parser updates.
- The LLM stage downloads a local model on first use and can take substantial time for a large dataset; the LLM CLI keeps a JSON Lines checkpoint during processing and writes the required valid JSON array when the run completes, so an interruption does not require restarting from row 0.
