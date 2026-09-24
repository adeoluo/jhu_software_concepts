"""SQLAlchemy ORM versions of the analysis queries; ``analysis_snapshot`` feeds the Analysis page."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, desc, func, or_, select

from models import Applicant, SessionLocal


def fall_2026() -> Any:
    """Filter: term mentions Fall 2026."""
    return func.lower(func.trim(Applicant.term)).contains("fall 2026")


def fall_2025() -> Any:
    """Filter: term mentions Fall 2025."""
    return func.lower(func.trim(Applicant.term)).contains("fall 2025")


def accepted() -> Any:
    """Filter: status is an acceptance (``accept*`` or ``admitted``)."""
    normalized_status = func.lower(func.trim(Applicant.status))
    return or_(normalized_status.contains("accept"), normalized_status == "admitted")


def listed_university(column: Any) -> Any:
    """Filter: ``column`` names Georgetown, MIT, Stanford, or Carnegie Mellon."""
    normalized_university = func.lower(func.trim(column))
    return or_(
        normalized_university.contains("georgetown"),
        normalized_university.contains("massachusetts institute of technology"),
        normalized_university == "mit",
        normalized_university.contains("stanford"),
        normalized_university.contains("carnegie mellon"),
    )


def question_1() -> Select[tuple[int]]:
    """Q1: number of Fall 2026 entries."""
    return select(func.count(Applicant.p_id)).where(fall_2026())


def question_4() -> Select[tuple[float | Decimal | None]]:
    """Q4: average GPA of American Fall 2026 applicants."""
    return select(func.avg(Applicant.gpa)).where(
        fall_2026(),
        func.lower(func.trim(Applicant.us_or_international)) == "american",
        Applicant.gpa.is_not(None),
    )


def question_5() -> Select[tuple[float | Decimal | None]]:
    """Q5: percentage of Fall 2025 entries that are acceptances."""
    acceptance_count = func.count(Applicant.p_id).filter(accepted())
    return select(
        100.0 * acceptance_count / func.nullif(func.count(Applicant.p_id), 0)
    ).where(fall_2025())


def question_8() -> Select[tuple[int]]:
    """Q8: Fall 2026 PhD Computer Science acceptances at listed universities (original fields)."""
    return select(func.count(Applicant.p_id)).where(
        fall_2026(),
        accepted(),
        func.lower(func.trim(Applicant.degree)).contains("phd"),
        func.lower(func.trim(Applicant.program)).contains("computer science"),
        listed_university(Applicant.university),
    )


def question_9() -> Select[tuple[int]]:
    """Q9: the Q8 count using the LLM-generated program and university fields."""
    return select(func.count(Applicant.p_id)).where(
        fall_2026(),
        accepted(),
        func.lower(func.trim(Applicant.degree)).contains("phd"),
        func.lower(func.trim(Applicant.llm_generated_program)).contains("computer science"),
        listed_university(Applicant.llm_generated_university),
    )


def question_10() -> Select[tuple[str | None, int]]:
    """Q10: five universities with the most Fall 2026 entries."""
    return (
        select(Applicant.university, func.count(Applicant.p_id).label("applicant_count"))
        .where(
            fall_2026(),
            Applicant.university.is_not(None),
            func.trim(Applicant.university) != "",
        )
        .group_by(Applicant.university)
        .order_by(desc("applicant_count"), Applicant.university.asc())
        .limit(5)
    )


def question_2() -> Select[tuple[float | Decimal | None]]:
    """Q2: percentage of classified entries that are international."""
    classification = func.lower(func.trim(Applicant.us_or_international))
    international_count = func.count(Applicant.p_id).filter(classification == "international")
    usable_count = func.count(Applicant.p_id).filter(
        and_(Applicant.us_or_international.is_not(None), func.trim(Applicant.us_or_international) != "")
    )
    return select(100.0 * international_count / func.nullif(usable_count, 0))


def question_3() -> Select[tuple[Any, Any, Any, Any]]:
    """Q3: average GPA, GRE Quantitative, GRE Verbal, and GRE Analytical Writing."""
    return select(
        func.avg(Applicant.gpa),
        func.avg(Applicant.gre),
        func.avg(Applicant.gre_v),
        func.avg(Applicant.gre_aw),
    )


def question_6() -> Select[tuple[float | Decimal | None]]:
    """Q6: average GPA of accepted Fall 2026 applicants."""
    return select(func.avg(Applicant.gpa)).where(
        fall_2026(),
        accepted(),
        Applicant.gpa.is_not(None),
    )


def question_7() -> Select[tuple[int]]:
    """Q7: Johns Hopkins master's Computer Science entries."""
    return select(func.count(Applicant.p_id)).where(
        or_(
            func.lower(func.trim(Applicant.university)).contains("johns hopkins"),
            func.lower(func.trim(Applicant.university)) == "jhu",
        ),
        func.lower(func.trim(Applicant.program)).contains("computer science"),
        func.lower(func.trim(Applicant.degree)).op("~")(
            r"(^|[^a-z])(masters?[\u0027\u2019]?|m\\.?s\\.?)([^a-z]|$)"
        ),
    )


def question_11() -> Select[tuple[str | None, Any]]:
    """Q11: average GPA for American vs. international applicants."""
    classification = func.lower(func.trim(Applicant.us_or_international)).label("classification")
    return (
        select(classification, func.avg(Applicant.gpa))
        .where(
            classification.in_(["american", "international"]),
            Applicant.gpa.is_not(None),
        )
        .group_by(classification)
        .order_by(classification)
    )


def run_orm_queries() -> dict[str, Any]:
    """Run the ORM queries used by the command-line report and return their rows by question."""
    statements = {
        "Question 1": question_1(),
        "Question 4": question_4(),
        "Question 5": question_5(),
        "Question 8": question_8(),
        "Question 9": question_9(),
        "Question 10": question_10(),
    }
    with SessionLocal() as session:
        results: dict[str, Any] = {}
        for question, statement in statements.items():
            results[question] = session.execute(statement).all()
    return results


def analysis_snapshot() -> dict[str, Any]:
    """Return all webpage analyses using Applicant ORM expressions."""
    with SessionLocal() as session:
        q3 = session.execute(question_3()).one()
        q11 = session.execute(question_11()).all()
        q10 = session.execute(question_10()).all()
        q8 = session.scalar(question_8())
        q9 = session.scalar(question_9())
        return {
            "q1": session.scalar(question_1()),
            "q2": session.scalar(question_2()),
            "q3": {
                "gpa": q3[0],
                "gre": q3[1],
                "gre_v": q3[2],
                "gre_aw": q3[3],
            },
            "q4": session.scalar(question_4()),
            "q5": session.scalar(question_5()),
            "q6": session.scalar(question_6()),
            "q7": session.scalar(question_7()),
            "q8": q8,
            "q9": q9,
            "q10": q10,
            "q11": q11,
            "q9_difference": (q9 or 0) - (q8 or 0),
        }


def format_value(value: Any, decimals: int = 2) -> str:
    """Format floats/Decimals with fixed decimals; ``None`` becomes ``N/A``."""
    if value is None:
        return "N/A"
    if isinstance(value, (float, Decimal)):
        return f"{value:.{decimals}f}"
    return str(value)


def format_results(results: dict[str, Any]) -> Iterable[str]:
    """Yield one human-readable line per answer from ``run_orm_queries`` output."""
    yield f"ORM Question 1 count: {results['Question 1'][0][0]:,}"
    yield f"ORM Question 4 average GPA: {format_value(results['Question 4'][0][0])}"
    yield f"ORM Question 5 acceptance percentage: {format_value(results['Question 5'][0][0])}%"
    yield f"ORM Question 8 count: {results['Question 8'][0][0]:,}"
    yield f"ORM Question 9 count: {results['Question 9'][0][0]:,}"
    yield f"ORM Question 10 top five universities:"
    for university, count in results["Question 10"]:
        yield f"  {university}: {count:,}"


def main() -> None:
    """Command-line entry point: print every ORM answer."""
    for line in format_results(run_orm_queries()):
        print(line)


if __name__ == "__main__":
    main()
