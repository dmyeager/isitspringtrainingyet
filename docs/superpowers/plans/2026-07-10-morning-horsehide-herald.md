# The Morning Horsehide Herald Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static site that publishes a daily, auto-generated baseball digest ("The Morning Horsehide Herald") at isitspringtrainingyet.com, produced each morning by a scheduled Claude agent that writes structured edition data and renders it to HTML.

**Architecture:** The agent emits schema-validated JSON per edition; a deterministic zero-dependency Python renderer turns that JSON into static HTML (edition pages + homepage + archive) at generation time. Both data and HTML are committed to a personal GitHub repo that GitHub Pages serves as-is. A scheduled Claude routine runs the editorial recipe at 5 AM ET, commits on success only, and pushes.

**Tech Stack:** Python 3 standard library only (`json`, `re`, `html`, `string`, `pathlib`, `sys`, `unittest`) for the renderer and its tests; plain static HTML + one CSS file; GitHub Pages (host); dnsimple (DNS); a Claude scheduled cloud agent (routine) for daily generation.

> **Resolves spec open items:** renderer language = Python 3 stdlib; inline-emphasis convention = Markdown-style `*em*` / `**strong**`; host = GitHub Pages.

---

## File Structure

| Path | Responsibility |
|---|---|
| `render.py` | The renderer: pure functions (prose, validation, edition/archive/homepage HTML) plus a thin CLI. The only place markup is produced. |
| `schema/edition.schema.json` | The authoritative edition-data contract; loaded and enforced by `render.py`. |
| `templates/base.html` | The page shell (`$title`, `$body`, CSS link, colophon nav). Only structural markup outside `render.py`. |
| `assets/herald.css` | The entire visual design (deadball-era newspaper). |
| `recipe.md` | The editorial spec the agent follows to produce edition JSON. Editorial control surface. |
| `agent/dispatch-prompt.md` | The short daily prompt handed to the scheduled routine. |
| `editions/YYYY/MM/DD.json` | Authored edition content (source of truth), written by the agent. |
| `editions/YYYY/MM/DD.html` | Rendered edition page (generated). |
| `index.html`, `archive.html` | Homepage (latest edition) and archive index (generated). |
| `CNAME`, `.nojekyll` | GitHub Pages custom-domain marker and Jekyll-disable marker. |
| `tests/test_render.py`, `tests/fixtures/*.json` | Renderer unit + integration tests and sample editions. |
| `docs/superpowers/…` | Spec and this plan. |

Because content lives as JSON and all markup lives in `render.py` + `templates/base.html` + `assets/herald.css`, a design change is applied to the whole archive with `python3 render.py --all`.

---

### Task 1: Repository scaffolding

**Files:**
- Create: `render.py`
- Create: `tests/__init__.py`
- Create: `schema/edition.schema.json`
- Create: `.nojekyll`
- Create: `.gitignore`

- [ ] **Step 1: Create directory scaffolding and empty module**

Create `render.py` with only a module docstring:

```python
"""The Morning Horsehide Herald renderer: edition JSON -> static HTML."""
```

Create an empty `tests/__init__.py` (so `tests.test_render` is importable):

```python
```

Create `.nojekyll` (empty file — tells GitHub Pages to serve files untouched):

```
```

Create `.gitignore`:

```
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 2: Create the edition schema**

Create `schema/edition.schema.json`:

```json
{
  "type": "object",
  "required": ["meta", "news", "rest_of_the_card", "desk_note"],
  "properties": {
    "meta": {
      "type": "object",
      "required": ["date", "date_display", "weekday", "volume", "edition_number", "mode", "contests_reported"],
      "properties": {
        "date": { "type": "string" },
        "date_display": { "type": "string" },
        "weekday": { "type": "string" },
        "volume": { "type": "string" },
        "edition_number": { "type": "integer" },
        "mode": { "type": "string", "enum": ["in_season", "hot_stove"] },
        "contests_reported": { "type": "integer" }
      }
    },
    "game_of_the_day": {
      "type": ["object", "null"],
      "required": ["headline", "subtitle", "body"],
      "properties": {
        "headline": { "type": "string" },
        "subtitle": { "type": "string" },
        "body": { "type": "string" }
      }
    },
    "news": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["subhead", "body"],
        "properties": {
          "subhead": { "type": "string" },
          "body": { "type": "string" }
        }
      }
    },
    "rest_of_the_card": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["headline", "body"],
        "properties": {
          "headline": { "type": "string" },
          "body": { "type": "string" }
        }
      }
    },
    "countdown": {
      "type": ["object", "null"],
      "required": ["milestone", "target_date", "days_remaining"],
      "properties": {
        "milestone": { "type": "string" },
        "target_date": { "type": "string" },
        "days_remaining": { "type": "integer" }
      }
    },
    "desk_note": { "type": "string" }
  }
}
```

- [ ] **Step 3: Verify the module imports and schema parses**

Run: `python3 -c "import json, render; json.load(open('schema/edition.schema.json')); print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add render.py tests/__init__.py schema/edition.schema.json .nojekyll .gitignore
git commit -m "scaffold: renderer module, edition schema, pages markers"
```

---

### Task 2: Prose rendering (escaping + inline emphasis)

**Files:**
- Modify: `render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_render.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestProse -v`
Expected: FAIL with `AttributeError: module 'render' has no attribute 'render_inline'`

- [ ] **Step 3: Implement the prose functions**

Add to `render.py` (below the docstring):

```python
import html
import re

_STRONG = re.compile(r"\*\*(.+?)\*\*")
_EM = re.compile(r"\*(.+?)\*")


def render_inline(text):
    """Escape HTML, then apply the *em* / **strong** convention. No block tags."""
    escaped = html.escape(text, quote=False)
    escaped = _STRONG.sub(r"<strong>\1</strong>", escaped)
    escaped = _EM.sub(r"<em>\1</em>", escaped)
    return escaped


def render_body(text):
    """Render prose as one or more <p> blocks split on blank lines."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    return "".join("<p>{}</p>".format(render_inline(b)) for b in blocks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render.TestProse -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: prose rendering with escaping and inline emphasis"
```

---

### Task 3: Schema validation

**Files:**
- Modify: `render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_render.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestValidate -v`
Expected: FAIL with `AttributeError: module 'render' has no attribute 'validate'`

- [ ] **Step 3: Implement the validator**

Add to `render.py`:

```python
_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate(data, schema):
    """Validate data against the supported JSON Schema subset. Raises ValueError."""
    _validate_node(data, schema, "$")


def _validate_node(value, schema, path):
    types = schema.get("type")
    if isinstance(types, str):
        types = [types]
    if types is not None and not any(_TYPE_CHECKS[t](value) for t in types if t in _TYPE_CHECKS):
        raise ValueError("{}: expected {}, got {}".format(path, types, type(value).__name__))
    if value is None:
        return
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("{}: {!r} not in {}".format(path, value, schema["enum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError("{}: missing required key '{}'".format(path, key))
        for key, subschema in schema.get("properties", {}).items():
            if key in value:
                _validate_node(value[key], subschema, "{}.{}".format(path, key))
    elif isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _validate_node(item, item_schema, "{}[{}]".format(path, i))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render.TestValidate -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: zero-dependency edition schema validation"
```

---

### Task 4: Page shell and masthead

**Files:**
- Create: `templates/base.html`
- Modify: `render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Create the base template**

Create `templates/base.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<link rel="stylesheet" href="/assets/herald.css">
</head>
<body>
<main class="sheet">
$body
</main>
<footer class="colophon">
<a href="/">Today&rsquo;s Edition</a> &middot; <a href="/archive.html">The Archive</a>
</footer>
</body>
</html>
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_render.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestPageAndMasthead -v`
Expected: FAIL with `AttributeError: module 'render' has no attribute 'render_page'`

- [ ] **Step 4: Implement page + masthead**

Add to `render.py` (add `import string` near the other imports):

```python
import string

_MASTHEAD_HEAD = (
    '<h1 class="masthead__title">⚾ THE MORNING HORSEHIDE HERALD ⚾</h1>'
    '<p class="masthead__motto">"Every Score Set Down, No Deed Unsung"</p>'
    '<p class="masthead__subtitle">~ Being a Faithful Daily Chronicle of the National Pastime ~</p>'
)


def render_page(title, body_html, base_template):
    return string.Template(base_template).safe_substitute(
        title=html.escape(title, quote=False), body=body_html
    )


def render_masthead(meta):
    if meta["mode"] == "in_season":
        n = meta["contests_reported"]
        note = "Reporting {} contest{} from the day prior.".format(n, "" if n == 1 else "s")
    else:
        note = "No contests this day; the hot stove burns bright."
    line = "{} &middot; No. {} &middot; {}, {}".format(
        render_inline(meta["volume"]),
        meta["edition_number"],
        render_inline(meta["weekday"]),
        render_inline(meta["date_display"]),
    )
    return (
        '<header class="masthead">'
        + _MASTHEAD_HEAD
        + '<p class="masthead__line">' + line + '</p>'
        + '<p class="masthead__note">' + note + '</p>'
        + '</header>'
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render.TestPageAndMasthead -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add templates/base.html render.py tests/test_render.py
git commit -m "feat: page shell and masthead rendering"
```

---

### Task 5: Edition body and full edition page

**Files:**
- Modify: `render.py`
- Test: `tests/test_render.py`
- Create: `tests/fixtures/in_season.json`
- Create: `tests/fixtures/hot_stove.json`

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/in_season.json`:

```json
{
  "meta": {
    "date": "2026-07-09",
    "date_display": "the Ninth of July, Two Thousand and Twenty-Six",
    "weekday": "Thursday",
    "volume": "Volume I",
    "edition_number": 1,
    "mode": "in_season",
    "contests_reported": 2
  },
  "game_of_the_day": {
    "headline": "MUDVILLE THUNDERS PAST THE ROBINS IN THE ELEVENTH",
    "subtitle": "In which a mighty blow settles a duel of five-and-forty outs",
    "body": "Under a copper sky the Thunders did prevail, **seven runs to six**, when the great Callahan smote the horsehide o'er the distant fence.\n\nThe standings tighten, and the faithful roar."
  },
  "news": [
    {
      "subhead": "Of Trades and Whispers",
      "body": "The wires hum with rumor that a *southpaw of renown* may yet change his colors before the deadline."
    }
  ],
  "rest_of_the_card": [
    {
      "headline": "THE CINCINNATI NINE SUBDUE THE COLTS, THREE TO ONE",
      "body": "A crisp affair decided by timely leather and a lone errant throw."
    }
  ],
  "desk_note": "And so the presses rest until the morrow, when fresh deeds await their chronicler."
}
```

Create `tests/fixtures/hot_stove.json`:

```json
{
  "meta": {
    "date": "2026-12-20",
    "date_display": "the Twentieth of December",
    "weekday": "Sunday",
    "volume": "Volume I",
    "edition_number": 164,
    "mode": "hot_stove",
    "contests_reported": 0
  },
  "game_of_the_day": null,
  "news": [
    {
      "subhead": "The Stove Roars",
      "body": "A slugger of great repute has affixed his name to a contract most **handsome**, and the winter grows warm with talk."
    }
  ],
  "rest_of_the_card": [],
  "countdown": {
    "milestone": "Pitchers and Catchers report",
    "target_date": "the Eighteenth of February",
    "days_remaining": 60
  },
  "desk_note": "Patience, faithful reader; the crocus of the diamond shall bloom in its season."
}
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_render.py` (add `import json` and `import pathlib` at the top of the file):

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestEditionBody -v`
Expected: FAIL with `AttributeError: module 'render' has no attribute 'render_edition_body'`

- [ ] **Step 4: Implement edition body + edition page**

Add to `render.py`:

```python
def render_edition_body(data):
    meta = data["meta"]
    parts = [render_masthead(meta)]

    gotd = data.get("game_of_the_day")
    if gotd:
        parts.append(
            '<section class="game-of-the-day">'
            '<h2 class="section__label">⭐ The Game of the Day</h2>'
            '<h3 class="gotd__headline">' + render_inline(gotd["headline"]) + '</h3>'
            '<p class="gotd__subtitle">' + render_inline(gotd["subtitle"]) + '</p>'
            + render_body(gotd["body"])
            + '</section>'
        )

    countdown = data.get("countdown")
    if countdown:
        parts.append(
            '<section class="countdown"><p class="countdown__line">'
            + "{} days until ".format(countdown["days_remaining"])
            + render_inline(countdown["milestone"])
            + " (" + render_inline(countdown["target_date"]) + ")."
            + '</p></section>'
        )

    news = data.get("news") or []
    if news:
        items = "".join(
            '<div class="news__item"><h3 class="news__subhead">'
            + render_inline(n["subhead"]) + '</h3>' + render_body(n["body"]) + '</div>'
            for n in news
        )
        parts.append(
            '<section class="news"><h2 class="section__label">'
            '\U0001f4dc News Around the League</h2>' + items + '</section>'
        )

    card = data.get("rest_of_the_card") or []
    if card:
        items = "".join(
            '<div class="card__game"><h3 class="card__headline">'
            + render_inline(g["headline"]) + '</h3>' + render_body(g["body"]) + '</div>'
            for g in card
        )
        parts.append(
            '<section class="rest-of-the-card"><h2 class="section__label">'
            '\U0001f4cb The Rest of the Card</h2>' + items + '</section>'
        )

    parts.append(
        '<section class="desk-note">'
        + render_body(data["desk_note"])
        + '<p class="signoff">~ THE HERALD ~</p></section>'
    )
    return "".join(parts)


def render_edition(data, base_template):
    title = "The Morning Horsehide Herald — " + data["meta"]["date_display"]
    return render_page(title, render_edition_body(data), base_template)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render.TestEditionBody -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add render.py tests/test_render.py tests/fixtures/in_season.json tests/fixtures/hot_stove.json
git commit -m "feat: edition body and full edition page rendering"
```

---

### Task 6: Homepage, archive, and edition URLs

**Files:**
- Modify: `render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_render.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestHomeAndArchive -v`
Expected: FAIL with `AttributeError: module 'render' has no attribute 'edition_url'`

- [ ] **Step 3: Implement URLs, homepage, and archive**

Add to `render.py`:

```python
def edition_url(date):
    year, month, day = date.split("-")
    return "/editions/{}/{}/{}.html".format(year, month, day)


def render_homepage(latest, base_template):
    if latest is None:
        body = (
            '<header class="masthead">' + _MASTHEAD_HEAD + '</header>'
            '<section class="placeholder"><p>The presses are warming up. '
            'The first edition goes to press at dawn.</p></section>'
        )
        return render_page("The Morning Horsehide Herald", body, base_template)
    return render_edition(latest, base_template)


def build_archive_entries(editions):
    entries = []
    for data in editions:
        meta = data["meta"]
        gotd = data.get("game_of_the_day")
        entries.append({
            "date": meta["date"],
            "date_display": meta["date_display"],
            "url": edition_url(meta["date"]),
            "label": gotd["headline"] if gotd else "Hot Stove Edition",
        })
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def render_archive(entries, base_template):
    items = "".join(
        '<li class="archive__item"><a href="' + e["url"] + '">'
        + render_inline(e["date_display"]) + '</a> &mdash; '
        + render_inline(e["label"]) + '</li>'
        for e in entries
    )
    body = (
        '<header class="masthead masthead--mini">' + _MASTHEAD_HEAD + '</header>'
        '<section class="archive"><h2 class="section__label">The Archive</h2>'
        '<ul class="archive__list">' + items + '</ul></section>'
    )
    return render_page("The Archive — The Morning Horsehide Herald", body, base_template)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render.TestHomeAndArchive -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: homepage, archive, and edition URL helpers"
```

---

### Task 7: CLI orchestration (render one / render all)

**Files:**
- Modify: `render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing integration tests**

Add to `tests/test_render.py` (add `import shutil` and `import tempfile` at the top):

```python
class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "templates").mkdir()
        (self.root / "schema").mkdir()
        # Real template and schema from the repo, so the test exercises them.
        repo = pathlib.Path(__file__).resolve().parent.parent
        shutil.copy(repo / "templates" / "base.html", self.root / "templates" / "base.html")
        shutil.copy(repo / "schema" / "edition.schema.json", self.root / "schema" / "edition.schema.json")
        for name, date in [("in_season.json", "2026-07-09"), ("hot_stove.json", "2026-12-20")]:
            y, m, d = date.split("-")
            dst = self.root / "editions" / y / m
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy(FIXTURES / name, dst / (d + ".json"))

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_render_all_writes_editions_index_and_archive(self):
        render.render_all(self.root)
        self.assertTrue((self.root / "editions" / "2026" / "07" / "09.html").exists())
        self.assertTrue((self.root / "editions" / "2026" / "12" / "20.html").exists())
        index = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertIn("hot stove burns bright", index)  # latest edition is the Dec one
        archive = (self.root / "archive.html").read_text(encoding="utf-8")
        self.assertIn('href="/editions/2026/07/09.html"', archive)

    def test_render_one_validates_before_writing(self):
        bad = self.root / "editions" / "2026" / "07" / "10.json"
        bad.write_text('{"meta": {"mode": "in_season"}}', encoding="utf-8")
        with self.assertRaises(ValueError):
            render.render_one(self.root, bad)
        # A failed render must not have produced the bad edition's HTML.
        self.assertFalse((self.root / "editions" / "2026" / "07" / "10.html").exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestPipeline -v`
Expected: FAIL with `AttributeError: module 'render' has no attribute 'render_all'`

- [ ] **Step 3: Implement orchestration + CLI**

Add to `render.py` (add `import json`, `import sys`, and `from pathlib import Path` at the top):

```python
def discover_editions(root):
    files = sorted(Path(root).glob("editions/*/*/*.json"))
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def _load_template(root):
    return (Path(root) / "templates" / "base.html").read_text(encoding="utf-8")


def _load_schema(root):
    return json.loads((Path(root) / "schema" / "edition.schema.json").read_text(encoding="utf-8"))


def render_all(root):
    root = Path(root)
    template = _load_template(root)
    schema = _load_schema(root)
    editions = discover_editions(root)
    for data in editions:               # validate everything before writing anything
        validate(data, schema)
    for data in editions:
        out = root / edition_url(data["meta"]["date"]).lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_edition(data, template), encoding="utf-8")
    latest = max(editions, key=lambda d: d["meta"]["date"]) if editions else None
    (root / "index.html").write_text(render_homepage(latest, template), encoding="utf-8")
    entries = build_archive_entries(editions)
    (root / "archive.html").write_text(render_archive(entries, template), encoding="utf-8")


def render_one(root, json_path):
    root = Path(root)
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    validate(data, _load_schema(root))  # fail loudly on the new edition first
    render_all(root)                     # regenerate everything from disk


def main(argv):
    root = Path(__file__).resolve().parent
    if len(argv) == 2 and argv[1] == "--all":
        render_all(root)
    elif len(argv) == 2:
        render_one(root, argv[1])
    else:
        print("usage: render.py <edition.json> | --all", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the full suite to verify everything passes**

Run: `python3 -m unittest discover -s tests -t . -v`
Expected: PASS (all tests across TestProse, TestValidate, TestPageAndMasthead, TestEditionBody, TestHomeAndArchive, TestPipeline)

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: render CLI orchestration with validate-before-write"
```

---

### Task 8: Newspaper stylesheet (`herald.css`)

**Files:**
- Create: `assets/herald.css`

> This is a first-cut, real stylesheet. **Checkpoint:** produce a rendered preview (Task 10) and get the visual design approved before go-live; iterate on this file as needed. Because content is data, restyling never requires touching editions.

- [ ] **Step 1: Create the stylesheet**

Create `assets/herald.css`:

```css
:root {
  --stock: #f4f1e8;
  --ink: #1c1a15;
  --rule: #6f6857;
  --accent: #7a2e1d;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--stock);
  color: var(--ink);
  font-family: var(--serif);
  line-height: 1.5;
}

.sheet {
  max-width: 46rem;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}

.masthead {
  text-align: center;
  border-bottom: 3px double var(--ink);
  padding-bottom: 0.75rem;
  margin-bottom: 1.5rem;
}

.masthead__title {
  font-size: clamp(1.6rem, 6vw, 2.6rem);
  letter-spacing: 0.04em;
  margin: 0 0 0.25rem;
}

.masthead__motto { font-style: italic; margin: 0.1rem 0; }
.masthead__subtitle { font-variant: small-caps; letter-spacing: 0.06em; margin: 0.1rem 0; }
.masthead__line { margin: 0.5rem 0 0; font-variant: small-caps; }
.masthead__note { margin: 0.2rem 0 0; font-style: italic; color: var(--rule); }
.masthead--mini .masthead__title { font-size: clamp(1.3rem, 5vw, 2rem); }

.section__label {
  font-variant: small-caps;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 0.2rem;
  margin: 2rem 0 0.75rem;
}

.gotd__headline, .card__headline {
  font-size: 1.25rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin: 0 0 0.15rem;
}
.gotd__subtitle { font-style: italic; color: var(--rule); margin: 0 0 0.5rem; }

.news__item, .card__game { margin-bottom: 1rem; }
.news__subhead { font-variant: small-caps; letter-spacing: 0.05em; margin: 0 0 0.2rem; color: var(--accent); }

.countdown__line {
  text-align: center;
  font-variant: small-caps;
  letter-spacing: 0.05em;
  border: 1px solid var(--rule);
  padding: 0.5rem;
}

.desk-note { margin-top: 2rem; font-style: italic; }
.signoff { text-align: center; font-variant: small-caps; letter-spacing: 0.2em; margin-top: 1rem; }

.archive__list { list-style: none; padding: 0; }
.archive__item { padding: 0.35rem 0; border-bottom: 1px dotted var(--rule); }
.archive__item a { color: var(--accent); text-decoration: none; }
.archive__item a:hover { text-decoration: underline; }

.placeholder { text-align: center; font-style: italic; margin-top: 3rem; }

.colophon {
  max-width: 46rem;
  margin: 0 auto;
  padding: 1rem 1.25rem 2rem;
  text-align: center;
  font-variant: small-caps;
  border-top: 1px solid var(--rule);
}
.colophon a { color: var(--accent); text-decoration: none; }

p { margin: 0 0 0.75rem; }
```

- [ ] **Step 2: Smoke-render the fixtures and open the output**

Run:
```bash
mkdir -p editions/2026/07/09 editions/2026/12/20
cp tests/fixtures/in_season.json editions/2026/07/09.json
cp tests/fixtures/hot_stove.json editions/2026/12/20.json
python3 render.py --all
python3 -c "import pathlib; print('index.html', pathlib.Path('index.html').stat().st_size, 'bytes')"
```
Expected: prints a non-zero byte count; `index.html`, `archive.html`, and the two edition pages now exist. Open `index.html` in a browser to eyeball the design.

- [ ] **Step 3: Remove the smoke-test editions (they are not real editions)**

Run:
```bash
rm -rf editions
git checkout -- index.html archive.html 2>/dev/null || true
```
Expected: `editions/` is gone; no generated site files are staged.

- [ ] **Step 4: Commit the stylesheet**

```bash
git add assets/herald.css
git commit -m "feat: deadball-era newspaper stylesheet (first cut)"
```

---

### Task 9: The editorial recipe (`recipe.md`)

**Files:**
- Create: `recipe.md`

- [ ] **Step 1: Write the recipe**

Create `recipe.md`:

```markdown
# The Morning Horsehide Herald — Recipe

You are the chronicler of The Morning Horsehide Herald. This file is the
editorial spec. When cued for the morning dispatch, produce **one edition** as a
JSON file conforming to `schema/edition.schema.json`, then render and publish it
(see "Producing and publishing an edition" at the end).

## Trigger

The morning dispatch has been rung. Pull the **prior day's completed slate** and
run the edition for that day.

## Sources of truth

- **boxscore.email/mlb** is authoritative for scores, stats, standings, and
  leaderboards. When any number or name conflicts across sources, the box score
  wins.
- ESPN and similar outlets may be consulted for headline color and narrative
  detail after interesting events (dramatic finishes, debuts, milestones).
- Cross-reference player names against **baseball-reference.com** to confirm
  exact club affiliation before attributing anyone to a team.
- Internal consistency: when a name or stat appears in both the news section and
  a game summary, the two must agree, with boxscore.email as the tiebreaker.
- Never fabricate. If a fact cannot be verified, omit it rather than invent it.

## Determine the mode

Check whether the prior day had **completed games**:

- **Games played →** `meta.mode = "in_season"`. Produce the full edition.
- **No games** (winter offseason, or an in-season gap such as the All-Star
  break) **→** `meta.mode = "hot_stove"`. Produce the hot-stove edition:
  offseason/roster news in the same voice, plus a countdown to the next
  milestone (pitchers & catchers report → spring training → Opening Day). Look
  up the next milestone's date; compute `days_remaining` from the edition date.

## Masthead (flies on every edition)

> ⚾ THE MORNING HORSEHIDE HERALD ⚾
> *"Every Score Set Down, No Deed Unsung"*
> ~ Being a Faithful Daily Chronicle of the National Pastime ~

The masthead's fixed lines are rendered automatically. You supply the metadata:
`volume`, `edition_number`, `weekday`, `date_display` (the flowery date), and
`contests_reported`. The date-line and contest note are assembled by the
renderer.

## Structure → schema mapping

1. ⭐ **The Game of the Day** → `game_of_the_day: {headline, subtitle, body}`.
   The single most interesting/impactful contest: a thundering headline, a
   mock-heroic subtitle, and a full paragraph. Weave in standings and
   leaderboard implications. (Null in hot-stove mode.)
2. 📜 **News Around the League** → `news: [{subhead, body}]`. Trades and rumors,
   injuries/roster moves, suspensions, All-Star and draft happenings, grouped
   under small themed sub-headlines.
3. 📋 **The Rest of the Card** → `rest_of_the_card: [{headline, body}]`. Every
   remaining game, each with its own headline and a couple of sentences. **No
   score goes unreported.** Sprinkle standings/leaders where they fit. (Empty in
   hot-stove mode.)
4. Closing **word from the desk** → `desk_note` (a string). The renderer adds the
   ~ THE HERALD ~ sign-off after it.

In hot-stove mode, also supply `countdown: {milestone, target_date,
days_remaining}`.

## Voice

Mock-heroic deadball-era purple prose — Grantland Rice by way of a slightly
overwrought telegraph operator. Numbers spelled out in the old style
("five-and-sixty," "three-and-twentieth"), gods-and-heroes flourishes — but the
facts underneath stay strictly accurate.

## Formatting of prose fields

Prose fields are plain text. For emphasis, use `*italic*` and `**bold**` (the
renderer converts these). Do **not** write HTML. Separate paragraphs within a
body with a blank line.

## Producing and publishing an edition

1. Determine the prior day's date; set `meta.date` to `YYYY-MM-DD`.
2. Write the edition JSON to `editions/YYYY/MM/DD.json` (matching `meta.date`).
3. Run `python3 render.py editions/YYYY/MM/DD.json`. This validates the JSON
   against the schema and regenerates the edition page, the homepage, and the
   archive.
4. **If validation fails, fix the JSON and re-run. Never commit invalid output.**
5. On success, commit the JSON and all generated HTML, then push. A failed run
   produces no commit, so the previous edition stays live.
```

- [ ] **Step 2: Commit**

```bash
git add recipe.md
git commit -m "docs: editorial recipe mapping the Herald spec to edition JSON"
```

---

### Task 10: Agent dispatch prompt + local end-to-end dry run

**Files:**
- Create: `agent/dispatch-prompt.md`

- [ ] **Step 1: Write the daily dispatch prompt**

Create `agent/dispatch-prompt.md`:

```markdown
It is the morning dispatch for The Morning Horsehide Herald.

Read `recipe.md` in this repository and follow it exactly to produce today's
edition (covering the prior day's slate). Concretely:

1. Gather the prior day's completed games and news from the sources of truth in
   the recipe (boxscore.email/mlb is authoritative; cross-check team
   affiliations on baseball-reference.com).
2. Decide the mode (in_season vs hot_stove) per the recipe.
3. Write the edition as JSON conforming to `schema/edition.schema.json` at
   `editions/YYYY/MM/DD.json` for the prior day's date.
4. Run `python3 render.py editions/YYYY/MM/DD.json`.
5. If the render reports a validation error, fix the JSON and re-run. Do not
   commit invalid output.
6. On success, `git add` the new JSON and the regenerated HTML
   (`index.html`, `archive.html`, and the edition page), commit with a message
   like "edition: YYYY-MM-DD", and push.
```

- [ ] **Step 2: Do a manual end-to-end dry run**

This validates the whole content path with a real (human-triggered) agent run
before any scheduling exists. In a Claude Code session with this repo:

Run (paste the dispatch prompt, or):
```bash
cat agent/dispatch-prompt.md
```
Then have the agent execute it for the most recent day with games. Confirm:
- A new `editions/YYYY/MM/DD.json` was created and validates.
- `python3 render.py editions/YYYY/MM/DD.json` exits 0.
- `index.html` shows the new edition; opening it in a browser reads in the
  Herald voice and looks right (design checkpoint for Task 8).

- [ ] **Step 3: Commit the prompt (and the first real edition, if produced)**

```bash
git add agent/dispatch-prompt.md
git commit -m "docs: daily dispatch prompt for the scheduled agent"
# If the dry run produced a real, correct edition you want to keep live:
# git add editions index.html archive.html && git commit -m "edition: YYYY-MM-DD"
```

---

### Task 11: Publish via GitHub Pages

**Files:**
- Create: `CNAME`

> Ops/config task — verification-based, not TDD. Uses the personal `dmyeager`
> GitHub account. Requires `gh` authenticated as `dmyeager` (`gh auth status`).

- [ ] **Step 1: Add the custom-domain marker**

Create `CNAME`:

```
isitspringtrainingyet.com
```

Commit:
```bash
git add CNAME && git commit -m "chore: GitHub Pages custom domain marker"
```

- [ ] **Step 2: Create the remote repo and push**

Run:
```bash
gh auth status   # confirm you are dmyeager; if not: gh auth switch
gh repo create dmyeager/isitspringtrainingyet --public --source=. --remote=origin --push
```
Expected: repo created under `dmyeager`, `main` pushed.

- [ ] **Step 3: Enable GitHub Pages from the main branch root**

Run:
```bash
gh api -X POST repos/dmyeager/isitspringtrainingyet/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```
Expected: HTTP 201 with a Pages object. (If Pages already exists, use
`-X PUT repos/dmyeager/isitspringtrainingyet/pages` to update the source.)

- [ ] **Step 4: Verify the default Pages URL serves**

Run:
```bash
sleep 60
curl -sSI https://dmyeager.github.io/isitspringtrainingyet/ | head -n 1
```
Expected: `HTTP/2 200` (a page is being served). If 404, wait and retry — first
deploys can take a couple minutes.

---

### Task 12: Point the domain at Pages (dnsimple)

> Ops/config task. Requires access to the dnsimple account holding
> `isitspringtrainingyet.com`. Commands use the `dnsimple` API via `curl`; the
> web UI is an equally valid path.

- [ ] **Step 1: Create the apex ALIAS record → GitHub Pages**

In dnsimple for `isitspringtrainingyet.com`, add:
- **ALIAS** record, name `` (apex/blank), content `dmyeager.github.io`.
- Optional **CNAME** record, name `www`, content `dmyeager.github.io`.

Via API (replace `$DNSIMPLE_TOKEN` and `$ACCOUNT_ID`):
```bash
curl -sS -H "Authorization: Bearer $DNSIMPLE_TOKEN" -H "Content-Type: application/json" \
  -X POST "https://api.dnsimple.com/v2/$ACCOUNT_ID/zones/isitspringtrainingyet.com/records" \
  -d '{"name":"","type":"ALIAS","content":"dmyeager.github.io","ttl":3600}'
```

- [ ] **Step 2: Set the custom domain in Pages and enable HTTPS**

Run:
```bash
gh api -X PUT repos/dmyeager/isitspringtrainingyet/pages \
  -f 'cname=isitspringtrainingyet.com' -F 'https_enforced=true'
```
Expected: HTTP 204. (GitHub provisions a certificate automatically once DNS
resolves; this can take up to an hour on first setup.)

- [ ] **Step 3: Verify DNS and HTTPS**

Run:
```bash
dig +short isitspringtrainingyet.com
curl -sSI https://isitspringtrainingyet.com/ | head -n 1
```
Expected: `dig` returns GitHub Pages IP addresses; `curl` returns `HTTP/2 200`
with a valid certificate (no TLS warning). Retry if the certificate is still
provisioning.

---

### Task 13: Schedule the daily routine

> Ops/config task — the automation. The **Claude subscription that runs the
> routine is the single point of change**: record it here so switching to a
> personal account later is a config swap, not a rebuild.

- [ ] **Step 1: Provision GitHub push credentials for the routine**

Create a fine-grained personal access token on the `dmyeager` account scoped to
the `isitspringtrainingyet` repo with **Contents: read and write**. Store it
where the routine can use it (the scheduled-agent secret/credential store).
Record the token's location and its purpose in the repo:

Append to `agent/dispatch-prompt.md` a short "Runtime notes" section (commit
it) documenting:
- Which Claude account/subscription owns this routine (**currently: work
  subscription** — the single point of change).
- Where the `dmyeager` GitHub PAT is stored for the routine.
- The cron and timezone (below).

```bash
git add agent/dispatch-prompt.md && git commit -m "docs: routine runtime notes (account + credential locations)"
```

- [ ] **Step 2: Create the scheduled routine**

Using the scheduled cloud agent / routine mechanism (the `schedule` skill), on
the **work Claude subscription**, create a routine that:
- Runs on cron `0 5 * * *` in timezone **America/New_York** (5:00 AM ET, DST-aware).
- Has the `dmyeager/isitspringtrainingyet` repo attached, with the PAT from
  Step 1 for push access.
- Uses the contents of `agent/dispatch-prompt.md` as its prompt.

Record the routine's ID/URL in `agent/dispatch-prompt.md` runtime notes and
commit.

- [ ] **Step 3: Trigger one live run manually and verify end-to-end**

Trigger the routine once by hand (do not wait for 5 AM). Confirm:
```bash
git -C <local clone> pull
ls editions/$(date -u +%Y)/   # a new edition directory/file appeared
curl -sSI https://isitspringtrainingyet.com/ | head -n 1   # HTTP/2 200
```
Expected: a new commit from the routine, a new edition JSON + HTML, and the live
homepage updated to the new edition. If nothing committed, check the routine's
run logs — a failed run intentionally leaves the previous edition live.

- [ ] **Step 4: Confirm the account swap procedure is documented**

Re-read the runtime notes. Verify they state, in one place, exactly what to
change to move the routine from the work subscription to a personal one
(re-create/transfer the routine under the new Claude account; re-attach the same
`dmyeager` GitHub PAT; nothing in the repo changes). Fix if unclear; commit.

---

### Task 14: Verify the hot-stove / no-games path

> Can be exercised immediately around the All-Star break (~mid-July), which
> presents as "no completed games yesterday," without waiting for the winter.

- [ ] **Step 1: Confirm the mode switch on a real no-games day**

On (or just after) an all-star-break day with no games, let the routine run (or
trigger it manually). Confirm the produced edition has `meta.mode: "hot_stove"`,
a populated `countdown`, no `game_of_the_day`, and an empty `rest_of_the_card`,
and that the rendered homepage shows the hot-stove edition with the countdown
line.

- [ ] **Step 2: If the mode logic misfires, refine the recipe (not the code)**

The in-season/hot-stove decision lives entirely in `recipe.md`. If the agent
mis-detects a no-games day, tighten the "Determine the mode" instructions and
commit — no renderer change should be needed.

```bash
git add recipe.md && git commit -m "docs: sharpen no-games mode detection in recipe"
```

---

## Self-Review

**Spec coverage** — every spec section maps to a task:
- Recipe (§1) → Task 9. In-season/offseason logic (§2) → recipe (Task 9) + verified in Task 14.
- Content schema & renderer (§3) → Tasks 1–7 (schema, prose, validation, edition, homepage/archive, CLI). Render-at-generation-time + validate-before-write → Task 7. Re-render-all → `render.py --all` (Tasks 7, 8).
- Publishing & hosting (§4) → Tasks 11 (Pages, `.nojekyll`, `CNAME`) + 12 (dnsimple). Self-healing failure mode → Task 7 (validate-before-write) + Task 13 Step 3.
- Repo layout & routing (§5) → Task 1 + file structure table; URLs → Task 6.
- Look & feel (§6) → Task 8 (with a design-approval checkpoint in Task 10).
- Scheduling & account (§7) → Task 13, including the single-point-of-change documentation (Steps 1 & 4).
- Error handling → Task 7 (schema validation), Task 13 Step 3 (failed run leaves prior edition).
- Verification → renderer unit/integration tests (Tasks 2–7), Task 10 (dry run + design), Tasks 11–13 (publish path), Task 14 (hot-stove path).
- Cost → no build required; $0 hosting realized by Tasks 11–12.

**Placeholder scan** — no "TBD"/"handle edge cases"/"similar to Task N"; all code steps show complete code; ops steps give concrete commands with expected output.

**Type/name consistency** — function names used consistently across tasks:
`render_inline`, `render_body`, `validate`, `render_page`, `render_masthead`,
`render_edition_body`, `render_edition`, `edition_url`, `render_homepage`,
`build_archive_entries`, `render_archive`, `discover_editions`, `render_all`,
`render_one`, `main`. Schema keys (`meta.date`, `meta.date_display`,
`game_of_the_day`, `rest_of_the_card`, `countdown`, `desk_note`) match between
the schema (Task 1), fixtures (Task 5), renderer (Tasks 5–6), and recipe (Task 9).

## Post-review hardening (applied)

After Tasks 1–7 passed spec review, the code-quality review surfaced two issues, fixed in commit `3da34ea`. The inline code blocks in Tasks 2, 3, and 6 predate these — apply them if re-running the plan from scratch:

- **Emphasis regex** (Task 2): guard against space-padded asterisks so prose like "3 * 4" is not italicized — `_STRONG = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*")` and `_EM = re.compile(r"\*(?!\s)(.+?)(?<!\s)\*")`.
- **Date pattern** (Tasks 1 & 3): `_validate_node` gained `pattern` support (after the enum check: `if "pattern" in schema and isinstance(value, str): re.fullmatch(...) else ValueError`), and `meta.date` is constrained to `"^\\d{4}-\\d{2}-\\d{2}$"`. Only `meta.date` — `date_display` and `countdown.target_date` remain free-form display strings.
- **Archive href** (Task 6): `render_archive` escapes the URL with `html.escape(e["url"], quote=True)` as defense-in-depth.

Three tests were added (`test_inline_ignores_space_padded_asterisks`, `test_inline_single_word_em_still_works`, `test_pattern_rejects_nonmatching_string`); the suite is 28 tests, all passing.
```
