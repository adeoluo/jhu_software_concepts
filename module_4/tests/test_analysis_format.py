"""Answer labels and two-decimal percentage formatting."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

import app as app_module

PERCENT_RE = re.compile(r"\d[\d,]*(?:\.\d+)?%")
TWO_DECIMAL_PERCENT_RE = re.compile(r"^\d[\d,]*\.\d{2}%$")


def render(make_app, snapshot):
    return BeautifulSoup(make_app(query=lambda: snapshot).test_client().get("/analysis").data, "html.parser")


@pytest.mark.analysis
def test_every_rendered_analysis_item_is_labeled_answer(make_app, snapshot):
    answers = render(make_app, snapshot).select('[data-testid="answer"]')

    assert len(answers) >= 10
    assert all(answer.get_text(" ", strip=True).startswith("Answer:") for answer in answers)


@pytest.mark.analysis
def test_every_percentage_on_the_page_has_two_decimals(make_app, snapshot):
    percentages = PERCENT_RE.findall(render(make_app, snapshot).get_text(" "))

    assert "48.92%" in percentages and "39.28%" in percentages
    assert all(TWO_DECIMAL_PERCENT_RE.match(value) for value in percentages), percentages


@pytest.mark.analysis
@pytest.mark.parametrize(
    ("value", "expected"),
    [(39.2812, "39.28%"), (Decimal("48.9"), "48.90%"), (5, "5.00%"), (0.004, "0.00%"), (None, "N/A")],
)
def test_format_percent_always_uses_two_decimals(value, expected):
    assert app_module.format_percent(value) == expected


@pytest.mark.analysis
def test_format_number_rounds_and_groups_thousands():
    assert app_module.format_number(3.756) == "3.76"
    assert app_module.format_number(32600, 0) == "32,600"
    assert app_module.format_number(None) == "N/A"


@pytest.mark.analysis
def test_missing_percentages_render_as_na_not_a_bare_percent_sign(snapshot):
    display = app_module.page_data({**snapshot, "q2": None, "q5": None})["display"]

    assert display["q2"] == "N/A" and display["q5"] == "N/A"
    assert display["difference"] == "+2"
    assert display["q11"] == [("American", "3.70"), ("International", "3.65")]
