import unittest

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


if __name__ == "__main__":
    unittest.main()