from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


PARAGRAPHS = [
    "Grad Cafe is an anonymous, self-reported source, so the database describes the entries that people chose to submit rather than a random sample of all graduate applicants. Selection bias may occur because applicants with especially positive, negative, or unusual outcomes may be more likely to post. Programs, universities, applicant types, and geographic groups whose applicants use the site more often may therefore be overrepresented, while applicants who never visit the site or who choose not to report an outcome may be absent. Self-reporting also creates risks of incorrect, incomplete, or inconsistently worded information. Missing GPA and GRE values are not random either: an applicant may omit a score because it is unavailable, weak, irrelevant to the program, or simply not entered. Consequently, the observed counts and averages are mathematically accurate summaries of the stored rows but should not be treated as unbiased estimates of the broader applicant population.",
    "For example, this database contains an average GRE Quantitative score of 165.38 among records with a retained Quantitative-scale value. That number tells us exactly what the selected records contain, but it does not establish that all graduate applicants average 165.38. Applicants with high scores may be more likely to report or include their scores, and programs with unusually strong or active online communities may contribute disproportionate numbers of entries. Similarly, the database contains 32,600 Fall 2026 entries and a 48.92% international share among usable classifications, but neither statistic proves that the full Fall 2026 applicant population has the same size or composition. The results are useful for describing this dataset and comparing groups within it, while broader real-world conclusions require a representative sampling design and independently verified information.",
]


def build_pdf(output_path: Path) -> None:
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontSize = 11
    body.leading = 16
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = [Paragraph("Module 3: Limitations of Grad Cafe Data", styles["Title"]), Spacer(1, 0.25 * inch)]
    for paragraph in PARAGRAPHS:
        story.append(Paragraph(paragraph, body))
        story.append(Spacer(1, 0.2 * inch))
    document.build(story)


if __name__ == "__main__":
    build_pdf(Path("limitations.pdf"))
    print("Saved limitations.pdf")
