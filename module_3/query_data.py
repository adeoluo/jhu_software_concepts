from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import psycopg

from load_data import psycopg_connection_string


SQL_QUERIES: dict[str, str] = {
    "Question 1": """
        SELECT COUNT(*)
        FROM applicants
        WHERE term ILIKE '%Fall 2026%'
    """,
    "Question 2": """
        SELECT
            100.0 * COUNT(*) FILTER (
                WHERE LOWER(TRIM(us_or_international)) = 'international'
            ) / NULLIF(COUNT(*), 0)
        FROM applicants
        WHERE us_or_international IS NOT NULL
          AND TRIM(us_or_international) <> ''
    """,
    "Question 3": """
        SELECT
            AVG(gpa),
            AVG(gre),
            AVG(gre_v),
            AVG(gre_aw)
        FROM applicants
    """,
    "Question 4": """
        SELECT AVG(gpa)
        FROM applicants
        WHERE term ILIKE '%Fall 2026%'
          AND LOWER(TRIM(us_or_international)) = 'american'
          AND gpa IS NOT NULL
    """,
    "Question 5": """
        SELECT
            100.0 * COUNT(*) FILTER (
                WHERE LOWER(TRIM(status)) LIKE '%accept%'
                   OR LOWER(TRIM(status)) = 'admitted'
            ) / NULLIF(COUNT(*), 0)
        FROM applicants
        WHERE term ILIKE '%Fall 2025%'
    """,
    "Question 6": """
        SELECT AVG(gpa)
        FROM applicants
        WHERE term ILIKE '%Fall 2026%'
          AND (
              LOWER(TRIM(status)) LIKE '%accept%'
              OR LOWER(TRIM(status)) = 'admitted'
          )
          AND gpa IS NOT NULL
    """,
    "Question 7": """
        SELECT COUNT(*)
        FROM applicants
        WHERE LOWER(COALESCE(university, '')) LIKE ANY (ARRAY['%johns hopkins%', '%jhu%'])
          AND LOWER(COALESCE(program, '')) LIKE '%computer science%'
                    AND LOWER(COALESCE(degree, '')) ~ '(^|[^a-z])(masters?|m\\.?s\\.?)([^a-z]|$)'
    """,
    "Question 8": """
        SELECT COUNT(*)
        FROM applicants
        WHERE term ILIKE '%Fall 2026%'
          AND (
              LOWER(TRIM(status)) LIKE '%accept%'
              OR LOWER(TRIM(status)) = 'admitted'
          )
          AND LOWER(COALESCE(degree, '')) LIKE '%phd%'
          AND LOWER(COALESCE(program, '')) LIKE '%computer science%'
          AND (
              LOWER(COALESCE(university, '')) LIKE '%georgetown%'
              OR LOWER(COALESCE(university, '')) LIKE '%massachusetts institute of technology%'
              OR LOWER(TRIM(COALESCE(university, ''))) = 'mit'
              OR LOWER(COALESCE(university, '')) LIKE '%stanford%'
              OR LOWER(COALESCE(university, '')) LIKE '%carnegie mellon%'
          )
    """,
    "Question 9": """
        SELECT COUNT(*)
        FROM applicants
        WHERE term ILIKE '%Fall 2026%'
          AND (
              LOWER(TRIM(status)) LIKE '%accept%'
              OR LOWER(TRIM(status)) = 'admitted'
          )
          AND LOWER(COALESCE(degree, '')) LIKE '%phd%'
          AND LOWER(COALESCE(llm_generated_program, '')) LIKE '%computer science%'
          AND (
              LOWER(COALESCE(llm_generated_university, '')) LIKE '%georgetown%'
              OR LOWER(COALESCE(llm_generated_university, '')) LIKE '%massachusetts institute of technology%'
              OR LOWER(TRIM(COALESCE(llm_generated_university, ''))) = 'mit'
              OR LOWER(COALESCE(llm_generated_university, '')) LIKE '%stanford%'
              OR LOWER(COALESCE(llm_generated_university, '')) LIKE '%carnegie mellon%'
          )
    """,
    "Question 10": """
        SELECT university, COUNT(*) AS applicant_count
        FROM applicants
        WHERE term ILIKE '%Fall 2026%'
          AND university IS NOT NULL
          AND TRIM(university) <> ''
        GROUP BY university
        ORDER BY applicant_count DESC, university ASC
        LIMIT 5
    """,
    "Question 11": """
        SELECT LOWER(TRIM(us_or_international)) AS classification, AVG(gpa)
        FROM applicants
        WHERE LOWER(TRIM(us_or_international)) IN ('american', 'international')
          AND gpa IS NOT NULL
        GROUP BY LOWER(TRIM(us_or_international))
        ORDER BY classification
    """,
}


QUESTION_TEXT: dict[str, str] = {
    "Question 1": "How many entries are from applicants who applied for Fall 2026?",
    "Question 2": "Among classified entries, what percentage are international students?",
    "Question 3": "What are the separate average GPA and GRE scores for applicants who provide each metric?",
    "Question 4": "What is the average GPA of American applicants who applied for Fall 2026?",
    "Question 5": "What percentage of Fall 2025 entries are acceptances?",
    "Question 6": "What is the average GPA of accepted applicants who applied for Fall 2026?",
    "Question 7": "How many entries are for a master's degree in Computer Science at Johns Hopkins University?",
    "Question 8": "How many qualifying Fall 2026 PhD Computer Science acceptances use the original fields?",
    "Question 9": "How many qualifying Fall 2026 PhD Computer Science acceptances use the LLM-generated fields?",
    "Question 10": "Which five universities have the most Fall 2026 applicant entries?",
    "Question 11": "What is the average GPA for American and international applicants who provide a GPA?",
}


def run_queries() -> dict[str, Any]:
    results: dict[str, Any] = {}
    with psycopg.connect(psycopg_connection_string()) as connection:
        with connection.cursor() as cursor:
            for question, query in SQL_QUERIES.items():
                cursor.execute(query)
                results[question] = cursor.fetchall()
    return results


def format_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.{decimals}f}"


def format_results(results: dict[str, Any]) -> Iterable[str]:
    question_1 = results["Question 1"][0][0]
    yield f"Fall 2026 applicant count: {question_1:,}"

    question_2 = results["Question 2"][0][0]
    yield f"Percent international: {format_number(question_2)}%"

    averages = results["Question 3"][0]
    yield f"Average GPA: {format_number(averages[0])}"
    yield f"Average GRE Quantitative: {format_number(averages[1])}"
    yield f"Average GRE Verbal: {format_number(averages[2])}"
    yield f"Average GRE Analytical Writing: {format_number(averages[3])}"

    yield f"Fall 2026 American average GPA: {format_number(results['Question 4'][0][0])}"
    yield f"Fall 2025 acceptance percentage: {format_number(results['Question 5'][0][0])}%"
    yield f"Fall 2026 accepted average GPA: {format_number(results['Question 6'][0][0])}"
    yield f"Johns Hopkins master's Computer Science count: {results['Question 7'][0][0]:,}"

    original_count = results["Question 8"][0][0]
    llm_count = results["Question 9"][0][0]
    yield f"Original-field count: {original_count:,}"
    yield f"LLM-field count: {llm_count:,}"
    yield f"Difference: {llm_count - original_count:+,}"

    yield "Top five Fall 2026 universities:"
    for university, count in results["Question 10"]:
        yield f"  {university}: {count:,}"

    yield "Average GPA by classification:"
    for classification, average_gpa in results["Question 11"]:
        yield f"  {classification.title()}: {format_number(average_gpa)}"


def main() -> None:
    results = run_queries()
    for line in format_results(results):
        print(line)


if __name__ == "__main__":
    main()
