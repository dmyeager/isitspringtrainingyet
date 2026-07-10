import json
import pathlib
import unittest

import render


class TestProse(unittest.TestCase):
    def test_inline_escapes_html(self):
        self.assertEqual(
            render.render_inline("Tinker & <Evers>"),
            "Tinker &amp; &lt;Evers&gt;",
        )

    def test_inline_strong_then_em(self):
        self.assertEqual(
            render.render_inline("a **bold** and *soft* word"),
            "a <strong>bold</strong> and <em>soft</em> word",
        )

    def test_inline_emphasis_after_escaping(self):
        # Emphasis markers survive escaping and still convert.
        self.assertEqual(
            render.render_inline("**A&B**"),
            "<strong>A&amp;B</strong>",
        )

    def test_body_splits_paragraphs_on_blank_lines(self):
        self.assertEqual(
            render.render_body("First para.\n\nSecond para."),
            "<p>First para.</p><p>Second para.</p>",
        )

    def test_body_ignores_trailing_whitespace_blocks(self):
        self.assertEqual(render.render_body("Only one.\n\n   \n"), "<p>Only one.</p>")


class TestValidate(unittest.TestCase):
    SCHEMA = {
        "type": "object",
        "required": ["meta", "count"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["mode"],
                "properties": {"mode": {"type": "string", "enum": ["in_season", "hot_stove"]}},
            },
            "count": {"type": "integer"},
            "note": {"type": ["object", "null"]},
        },
    }

    def test_valid_passes(self):
        render.validate({"meta": {"mode": "in_season"}, "count": 3, "note": None}, self.SCHEMA)

    def test_missing_required_key_raises(self):
        with self.assertRaises(ValueError):
            render.validate({"meta": {"mode": "in_season"}}, self.SCHEMA)

    def test_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            render.validate({"meta": {"mode": "in_season"}, "count": "three"}, self.SCHEMA)

    def test_bad_enum_raises(self):
        with self.assertRaises(ValueError):
            render.validate({"meta": {"mode": "spring"}, "count": 1}, self.SCHEMA)

    def test_bool_is_not_integer(self):
        with self.assertRaises(ValueError):
            render.validate({"meta": {"mode": "in_season"}, "count": True}, self.SCHEMA)

    def test_nullable_object_accepts_null(self):
        render.validate({"meta": {"mode": "hot_stove"}, "count": 0, "note": None}, self.SCHEMA)


class TestPageAndMasthead(unittest.TestCase):
    TEMPLATE = "<t>$title</t><b>$body</b>"

    def test_render_page_substitutes_and_escapes_title(self):
        out = render.render_page("A & B", "<p>hi</p>", self.TEMPLATE)
        self.assertEqual(out, "<t>A &amp; B</t><b><p>hi</p></b>")

    def test_masthead_in_season_note(self):
        meta = {
            "date": "2026-07-09", "date_display": "the Ninth of July",
            "weekday": "Thursday", "volume": "Vol. I", "edition_number": 1,
            "mode": "in_season", "contests_reported": 15,
        }
        html_out = render.render_masthead(meta)
        self.assertIn("THE MORNING HORSEHIDE HERALD", html_out)
        self.assertIn("Reporting 15 contests", html_out)
        self.assertIn("the Ninth of July", html_out)

    def test_masthead_hot_stove_note(self):
        meta = {
            "date": "2026-12-20", "date_display": "the Twentieth of December",
            "weekday": "Sunday", "volume": "Vol. I", "edition_number": 99,
            "mode": "hot_stove", "contests_reported": 0,
        }
        self.assertIn("hot stove burns bright", render.render_masthead(meta))

    def test_masthead_singular_contest(self):
        meta = {
            "date": "2026-04-01", "date_display": "Opening Day",
            "weekday": "Wednesday", "volume": "Vol. I", "edition_number": 1,
            "mode": "in_season", "contests_reported": 1,
        }
        self.assertIn("Reporting 1 contest ", render.render_masthead(meta))


FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestEditionBody(unittest.TestCase):
    def test_in_season_has_all_sections(self):
        body = render.render_edition_body(_load("in_season.json"))
        self.assertIn("The Game of the Day", body)
        self.assertIn("MUDVILLE THUNDERS", body)
        self.assertIn("<strong>seven runs to six</strong>", body)
        self.assertIn("News Around the League", body)
        self.assertIn("The Rest of the Card", body)
        self.assertIn("~ THE HERALD ~", body)
        self.assertNotIn("countdown__line", body)

    def test_hot_stove_omits_game_and_card_shows_countdown(self):
        body = render.render_edition_body(_load("hot_stove.json"))
        self.assertNotIn("The Game of the Day", body)
        self.assertNotIn("The Rest of the Card", body)
        self.assertIn("60 days until", body)
        self.assertIn("Pitchers and Catchers report", body)

    def test_render_edition_wraps_body_in_page(self):
        out = render.render_edition(_load("in_season.json"), "<t>$title</t><b>$body</b>")
        self.assertTrue(out.startswith("<t>The Morning Horsehide Herald — "))
        self.assertIn("MUDVILLE THUNDERS", out)


class TestHomeAndArchive(unittest.TestCase):
    def test_edition_url_from_date(self):
        self.assertEqual(render.edition_url("2026-07-09"), "/editions/2026/07/09.html")

    def test_homepage_none_shows_placeholder(self):
        out = render.render_homepage(None, "<t>$title</t><b>$body</b>")
        self.assertIn("presses are warming up", out)

    def test_homepage_latest_is_the_edition(self):
        out = render.render_homepage(_load("in_season.json"), "<t>$title</t><b>$body</b>")
        self.assertIn("MUDVILLE THUNDERS", out)

    def test_archive_entries_sorted_desc_with_labels(self):
        entries = render.build_archive_entries([_load("in_season.json"), _load("hot_stove.json")])
        self.assertEqual([e["date"] for e in entries], ["2026-12-20", "2026-07-09"])
        self.assertEqual(entries[0]["label"], "Hot Stove Edition")
        self.assertEqual(entries[1]["label"], "MUDVILLE THUNDERS PAST THE ROBINS IN THE ELEVENTH")

    def test_render_archive_lists_links(self):
        entries = render.build_archive_entries([_load("in_season.json")])
        out = render.render_archive(entries, "<t>$title</t><b>$body</b>")
        self.assertIn('href="/editions/2026/07/09.html"', out)
        self.assertIn("The Archive", out)


if __name__ == "__main__":
    unittest.main()
