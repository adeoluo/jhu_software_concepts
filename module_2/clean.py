from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _normalize_text(value: Any) -> str:
    """Return a consistent representation for missing or messy text values."""
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _normalize_status(value: Any) -> str:
    """Normalize common status labels to a consistent string."""
    status = _normalize_text(value).lower()
    mapping = {
        "admitted": "Accepted",
        "accepted": "Accepted",
        "rejected": "Rejected",
        "waitlisted": "Waitlisted",
        "interview": "Interview",
    }
    return mapping.get(status, _normalize_text(value))


def clean_data(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean raw applicant rows for downstream analysis.

    The assignment requires preserving the original raw listing text for
    traceability while also creating a consistent representation for missing or
    unavailable fields. This function keeps the raw values in the source record,
    then stores normalized values in the cleaned structure.
    """
    cleaned: List[Dict[str, Any]] = []
    for item in records:
        clean_row = {
            "raw_program": _normalize_text(item.get("raw_program") or item.get("program") or item.get("raw_text") or ""),
            "program": _normalize_text(item.get("program") or item.get("raw_program") or ""),
            "university": _normalize_text(item.get("university") or ""),
            "comments": _normalize_text(item.get("comments") or ""),
            "date_added": _normalize_text(item.get("date_added") or ""),
            "url": _normalize_text(item.get("url") or ""),
            "status": _normalize_status(item.get("status") or ""),
            "decision_date": _normalize_text(item.get("decision_date") or ""),
            "start_term": _normalize_text(item.get("start_term") or ""),
            "student_type": _normalize_text(item.get("student_type") or ""),
            "gre": _normalize_text(item.get("gre") or ""),
            "gre_v": _normalize_text(item.get("gre_v") or ""),
            "gpa": _normalize_text(item.get("gpa") or ""),
            "gre_aw": _normalize_text(item.get("gre_aw") or ""),
            "degree_level": _normalize_text(item.get("degree_level") or ""),
            "raw_text": _normalize_text(item.get("raw_text") or ""),
        }
        cleaned.append(clean_row)
    return cleaned


def save_data(data: Iterable[Dict[str, Any]], file_path: str | Path) -> None:
    """Save cleaned data to a JSON file atomically so a crash mid-write cannot corrupt the file."""
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(list(data), handle, ensure_ascii=False, indent=2)
    temp_path.replace(output_path)


def load_data(file_path: str | Path) -> List[Dict[str, Any]]:
    """Load cleaned JSON data from disk."""
    with Path(file_path).open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded if isinstance(loaded, list) else []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean the merged GradCafe applicant dataset.")
    parser.add_argument("--input", default="applicant_data.json", help="Merged raw JSON input path.")
    parser.add_argument(
        "--output",
        default="cleaned_applicant_data.json",
        help="Cleaned JSON output path for the later LLM standardization step.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.exists():
        raw_rows = load_data(input_path)
        cleaned_rows = clean_data(raw_rows)
        save_data(cleaned_rows, args.output)
        print(f"Cleaned {len(cleaned_rows)} rows and saved {args.output}")
    else:
        raise FileNotFoundError(f"No input dataset found at {input_path}. Run the collection step first.")
