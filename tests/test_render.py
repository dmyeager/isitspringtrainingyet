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


if __name__ == "__main__":
    unittest.main()
