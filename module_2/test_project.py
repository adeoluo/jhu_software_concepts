import unittest
from unittest.mock import patch

from auto_next_pages import _evaluate_js, _looks_blocked, _next_page_url_from_html
from capture_chrome_html import _read_current_page_html
from clean import clean_data
from scrape import _extract_rows_from_saved_html, build_result_url, robots_allows


SAMPLE_HTML = """
<table>
  <tbody>
    <tr>
      <td>Example University</td>
      <td>Computer Science PhD</td>
      <td>Sep 10, 2026</td>
      <td>Wait listed on Sep 10</td>
      <td><a href="/result/123">Total comments</a></td>
    </tr>
    <tr><td colspan="5">Spring 2027 International GRE 163 GRE V 158 GRE AW 4.00 GPA 3.57</td></tr>
    <tr><td colspan="5">Funding decision is pending.</td></tr>
    <tr>
      <td>Second University</td>
      <td>Creative Writing MFA</td>
      <td>Sep 08, 2026</td>
      <td>Accepted on Sep 08</td>
      <td>Total comments</td>
    </tr>
    <tr><td colspan="5">Fall 2026 American</td></tr>
  </tbody>
</table>
"""


class ScrapeTests(unittest.TestCase):
    @patch("auto_next_pages.websocket.create_connection")
    def test_collector_connection_omits_origin_header(self, create_connection):
        connection = create_connection.return_value
        connection.recv.return_value = '{"id": 1, "result": {"result": {"value": 20}}}'

        value = _evaluate_js("ws://localhost:9222/devtools/page/example", "document.querySelectorAll('tr').length")

        self.assertEqual(value, 20)
        create_connection.assert_called_once_with(
            "ws://localhost:9222/devtools/page/example",
            suppress_origin=True,
        )
        connection.close.assert_called_once_with()

    @patch("capture_chrome_html.websocket.create_connection")
    def test_chrome_connection_omits_origin_header(self, create_connection):
        connection = create_connection.return_value
        connection.recv.return_value = '{"id": 1, "result": {"result": {"value": "<html></html>"}}}'

        html = _read_current_page_html("ws://localhost:9222/devtools/page/example")

        self.assertEqual(html, "<html></html>")
        create_connection.assert_called_once_with(
            "ws://localhost:9222/devtools/page/example",
            suppress_origin=True,
        )
        connection.close.assert_called_once_with()

    def test_parser_groups_table_subrows_into_applicants(self):
        rows = _extract_rows_from_saved_html(SAMPLE_HTML)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["university"], "Example University")
        self.assertEqual(rows[0]["program"], "Computer Science")
        self.assertEqual(rows[0]["degree_level"], "PhD")
        self.assertEqual(rows[0]["status"], "Waitlisted")
        self.assertEqual(rows[0]["start_term"], "Spring 2027")
        self.assertEqual(rows[0]["student_type"], "International")
        self.assertEqual(rows[0]["gre"], "163")
        self.assertEqual(rows[0]["gre_v"], "158")
        self.assertEqual(rows[0]["gre_aw"], "4.00")
        self.assertEqual(rows[0]["gpa"], "3.57")
        self.assertEqual(rows[0]["comments"], "Funding decision is pending.")

    def test_cursor_url_is_encoded(self):
        url = build_result_url(cursor="abc+/=", query="computer science")

        self.assertEqual(
            url,
            "https://www.thegradcafe.com/survey?cursor=abc%2B%2F%3D&q=computer+science",
        )

    def test_robots_policy_allows_survey_but_not_profile(self):
        robots_text = "User-agent: *\nAllow: /\nDisallow: /profile\n"

        self.assertTrue(robots_allows("https://www.thegradcafe.com/survey", robots_text))
        self.assertFalse(robots_allows("https://www.thegradcafe.com/profile", robots_text))

    def test_cleaner_preserves_raw_source(self):
        cleaned = clean_data([{"program": " CS ", "raw_text": "  original   row  "}])

        self.assertEqual(cleaned[0]["program"], "CS")
        self.assertEqual(cleaned[0]["raw_text"], "original row")

    def test_next_page_url_ignores_previous_link(self):
        html = """
        <a href="/survey?cursor=previous">Previous</a>
        <a href="/survey?cursor=next">Next</a>
        """

        self.assertEqual(_next_page_url_from_html(html), "/survey?cursor=next")

    def test_looks_blocked_detects_challenge_page(self):
        self.assertTrue(_looks_blocked("<title>Just a moment...</title>"))
        self.assertTrue(_looks_blocked("<h1>Access Denied</h1>"))
        self.assertFalse(_looks_blocked(SAMPLE_HTML))


if __name__ == "__main__":
    unittest.main()