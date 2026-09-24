"""Generate ``query_results.pdf``: each SQL question with its answer, query, and explanation."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from query_data import QUESTION_TEXT, SQL_QUERIES, run_queries


EXPLANATIONS = {
    "Question 1": "Counts all rows whose term contains Fall 2026, regardless of other missing fields.",
    "Question 2": "Uses classified rows as the denominator and counts only International rows in the numerator.",
    "Question 3": "Calculates each metric independently, so missing GPA or GRE values do not exclude a row from another average.",
    "Question 4": "Filters to Fall 2026 American applicants and averages only non-NULL GPA values.",
    "Question 5": "Divides accepted Fall 2025 rows by all Fall 2025 rows, including rows without other optional fields.",
    "Question 6": "Filters to Fall 2026 accepted applicants and averages their available GPA values.",
    "Question 7": "Matches the original university, program, and degree fields using case-insensitive text patterns.",
    "Question 8": "Uses the original university and program fields while also requiring Fall 2026, acceptance, PhD, and Computer Science.",
    "Question 9": "Uses the LLM-generated university and program fields while retaining the original term, status, and degree filters.",
    "Question 10": "Groups Fall 2026 rows by university, counts each group, sorts from largest to smallest, and returns five rows.",
    "Question 11": "Groups American and International rows separately and averages only rows that provide a GPA.",
}


def format_value(value: Any) -> str:
    """Format floats/Decimals with two decimals; ``None`` becomes ``N/A``."""
    if value is None:
        return "N/A"
    if isinstance(value, (float, Decimal)):
        return f"{value:.2f}"
    return str(value)


def result_lines(question: str, results: dict[str, Any]) -> list[str]:
    """Return the display lines for one question's rows."""
    rows = results[question]
    if question == "Question 1":
        return [f"Fall 2026 applicant count: {rows[0][0]:,}"]
    if question == "Question 2":
        return [f"Percent international: {format_value(rows[0][0])}%"]
    if question == "Question 3":
        labels = ("Average GPA", "Average GRE Quantitative", "Average GRE Verbal", "Average GRE Analytical Writing")
        return [f"{label}: {format_value(value)}" for label, value in zip(labels, rows[0])]
    if question == "Question 4":
        return [f"Fall 2026 American average GPA: {format_value(rows[0][0])}"]
    if question == "Question 5":
        return [f"Fall 2025 acceptance percentage: {format_value(rows[0][0])}%"]
    if question == "Question 6":
        return [f"Fall 2026 accepted average GPA: {format_value(rows[0][0])}"]
    if question == "Question 7":
        return [f"Johns Hopkins master's Computer Science count: {rows[0][0]:,}"]
    if question in {"Question 8", "Question 9"}:
        return [f"{question} count: {rows[0][0]:,}"]
    if question == "Question 10":
        return [f"{university}: {count:,}" for university, count in rows]
    return [f"{classification.title()} average GPA: {format_value(average_gpa)}" for classification, average_gpa in rows]


def build_pdf(output_path: Path) -> None:
    """Run the SQL queries and write the formatted report to ``output_path``."""
    results = run_queries()
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]
    body_style.leading = 14
    code_style = ParagraphStyle(
        "SQLCode",
        parent=body_style,
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        alignment=TA_LEFT,
        backColor=colors.whitesmoke,
        borderColor=colors.lightgrey,
        borderWidth=0.5,
        borderPadding=6,
    )

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    story: list[Any] = [
        Paragraph("Module 3 SQL Analysis Results", title_style),
        Paragraph("Questions 1–9 and the two original database questions.", body_style),
        Spacer(1, 0.2 * inch),
    ]

    for index, question in enumerate(SQL_QUERIES):
        story.append(Paragraph(f"{question}: {QUESTION_TEXT[question]}", heading_style))
        story.append(Paragraph("<b>Result</b>", body_style))
        result_table = Table([[line] for line in result_lines(question, results)], colWidths=[7.1 * inch])
        result_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef5f7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9bb7bd")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c7d8db")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(result_table)
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("<b>SQL query</b>", body_style))
        story.append(Paragraph(escape(SQL_QUERIES[question].strip()), code_style))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"<b>Explanation:</b> {EXPLANATIONS[question]}", body_style))
        if index != len(SQL_QUERIES) - 1:
            story.append(PageBreak())

    document.build(story)


def main() -> None:
    """Command-line entry point: ``python generate_query_results_pdf.py --output <file.pdf>``."""
    parser = argparse.ArgumentParser(description="Generate the Module 3 SQL analysis PDF.")
    parser.add_argument("--output", type=Path, default=Path("query_results.pdf"))
    args = parser.parse_args()
    build_pdf(args.output)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
