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


if __name__ == "__main__":
    unittest.main()
