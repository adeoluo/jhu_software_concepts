from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, desc, func, or_, select

from models import Applicant, SessionLocal


def fall_2026() -> Any:
    return func.lower(func.trim(Applicant.term)).contains("fall 2026")


def fall_2025() -> Any:
    return func.lower(func.trim(Applicant.term)).contains("fall 2025")


def accepted() -> Any:
    normalized_status = func.lower(func.trim(Applicant.status))
    return or_(normalized_status.contains("accept"), normalized_status == "admitted")


def listed_university(column: Any) -> Any:
    normalized_university = func.lower(func.trim(column))
    return or_(
        normalized_university.contains("georgetown"),
        normalized_university.contains("massachusetts institute of technology"),
        normalized_university == "mit",
        normalized_university.contains("stanford"),
        normalized_university.contains("carnegie mellon"),
    )


def question_1() -> Select[tuple[int]]:
    return select(func.count(Applicant.p_id)).where(fall_2026())


def question_4() -> Select[tuple[float | Decimal | None]]:
    return select(func.avg(Applicant.gpa)).where(
        fall_2026(),
        func.lower(func.trim(Applicant.us_or_international)) == "american",
        Applicant.gpa.is_not(None),
    )


def question_5() -> Select[tuple[float | Decimal | None]]:
    acceptance_count = func.count(Applicant.p_id).filter(accepted())
    return select(
        100.0 * acceptance_count / func.nullif(func.count(Applicant.p_id), 0)
    ).where(fall_2025())


def question_8() -> Select[tuple[int]]:
    return select(func.count(Applicant.p_id)).where(
        fall_2026(),
        accepted(),
        func.lower(func.trim(Applicant.degree)).contains("phd"),
        func.lower(func.trim(Applicant.program)).contains("computer science"),
        listed_university(Applicant.university),
    )


def question_9() -> Select[tuple[int]]:
    return select(func.count(Applicant.p_id)).where(
        fall_2026(),
        accepted(),
        func.lower(func.trim(Applicant.degree)).contains("phd"),
        func.lower(func.trim(Applicant.llm_generated_program)).contains("computer science"),
        listed_university(Applicant.llm_generated_university),
    )


def question_10() -> Select[tuple[str | None, int]]:
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


def run_orm_queries() -> dict[str, Any]:
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


def format_value(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (float, Decimal)):
        return f"{value:.{decimals}f}"
    return str(value)


def format_results(results: dict[str, Any]) -> Iterable[str]:
    yield f"ORM Question 1 count: {results['Question 1'][0][0]:,}"
    yield f"ORM Question 4 average GPA: {format_value(results['Question 4'][0][0])}"
    yield f"ORM Question 5 acceptance percentage: {format_value(results['Question 5'][0][0])}%"
    yield f"ORM Question 8 count: {results['Question 8'][0][0]:,}"
    yield f"ORM Question 9 count: {results['Question 9'][0][0]:,}"
    yield f"ORM Question 10 top five universities:"
    for university, count in results["Question 10"]:
        yield f"  {university}: {count:,}"


def main() -> None:
    for line in format_results(run_orm_queries()):
        print(line)


if __name__ == "__main__":
    main()
