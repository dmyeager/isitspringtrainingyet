# Herald Citations Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each edition can carry an optional `sources` list that renders as a "The Herald Acknowledges Its Debts" colophon after the desk note, crediting every URL (and byline, where shown) that contributed facts to the edition.

**Architecture:** The edition JSON gains an optional top-level `sources` array validated by the existing schema subset in `render.py`; the renderer emits a new `<section class="sources">` after the desk-note section; `assets/herald.css` styles it as a small-type colophon; `recipe.md` and the morning-dispatch skill instruct the dispatch agent to record contributing sources. No pipeline shape changes.

**Tech Stack:** Python 3 stdlib (`render.py`), `unittest` (`tests/test_render.py`), hand-written JSON Schema subset, static CSS.

**Spec:** `docs/superpowers/specs/2026-08-10-herald-citations-design.md`

## Global Constraints

- Section heading text is exactly: `The Herald Acknowledges Its Debts`.
- `sources` is OPTIONAL at the top level (NOT added to the schema's `required` list); absent, `null`, and `[]` all render no section — all 33 existing editions must remain valid and their HTML byte-identical.
- Each source entry requires `url`, `title`, `publication`; `author` is optional and only ever present when the cited page shows a byline.
- Entry line format: `Author, <a>Title</a> — Publication` with the `Author, ` prefix omitted when there is no author; the dash is `&mdash;`.
- `url` is attribute-escaped with `html.escape(..., quote=True)`; `title`/`author`/`publication` go through `render_inline` like other prose.
- Tests run from the repo root: `python3 -m unittest tests.test_render -v`.
- Commit after each task; a task's tests must pass before its commit.

---

### Task 1: Schema — optional `sources` array

**Files:**
- Modify: `schema/edition.schema.json` (add one property after `desk_note`, line 58)
- Test: `tests/test_render.py` (new `TestSourcesSchema` class)

**Interfaces:**
- Produces: schema property `sources: [{url, title, publication, author?}]` — Task 2's renderer reads exactly these key names from the edition dict.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_render.py` (after the `TestEditionBody` class; `FIXTURES` and `_load` are already defined above it):

```python
REPO_SCHEMA = json.loads(
    (pathlib.Path(__file__).resolve().parent.parent / "schema" / "edition.schema.json")
    .read_text(encoding="utf-8")
)


class TestSourcesSchema(unittest.TestCase):
    def test_edition_with_sources_validates(self):
        data = _load("in_season.json")
        data["sources"] = [
            {"url": "https://www.mlb.com/news/some-story", "title": "Some Story",
             "publication": "MLB.com", "author": "Jane Writer"},
            {"url": "https://boxscore.email/mlb/2026-08-09",
             "title": "Morning digest for the games of August 9", "publication": "Boxscore"},
        ]
        render.validate(data, REPO_SCHEMA)  # no raise

    def test_null_sources_validates(self):
        data = _load("in_season.json")
        data["sources"] = None
        render.validate(data, REPO_SCHEMA)  # no raise

    def test_source_entry_missing_url_fails(self):
        data = _load("in_season.json")
        data["sources"] = [{"title": "t", "publication": "p"}]
        with self.assertRaises(ValueError):
            render.validate(data, REPO_SCHEMA)

    def test_source_entry_missing_publication_fails(self):
        data = _load("in_season.json")
        data["sources"] = [{"url": "https://x", "title": "t"}]
        with self.assertRaises(ValueError):
            render.validate(data, REPO_SCHEMA)

    def test_editions_without_sources_still_validate(self):
        render.validate(_load("in_season.json"), REPO_SCHEMA)
        render.validate(_load("hot_stove.json"), REPO_SCHEMA)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestSourcesSchema -v`
Expected: `test_source_entry_missing_url_fails` and `test_source_entry_missing_publication_fails` FAIL (no `ValueError` raised — the schema doesn't know `sources` yet, and the validator ignores unknown keys). The three positive tests already pass; that's fine — they're regression guards.

- [ ] **Step 3: Add the property to the schema**

In `schema/edition.schema.json`, change the `desk_note` line (currently line 58) from:

```json
    "desk_note": { "type": "string" }
```

to:

```json
    "desk_note": { "type": "string" },
    "sources": {
      "type": ["array", "null"],
      "items": {
        "type": "object",
        "required": ["url", "title", "publication"],
        "properties": {
          "url": { "type": "string" },
          "title": { "type": "string" },
          "publication": { "type": "string" },
          "author": { "type": "string" }
        }
      }
    }
```

Do NOT touch the top-level `"required"` array.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render -v`
Expected: all tests PASS (including every pre-existing test).

- [ ] **Step 5: Commit**

```bash
git add schema/edition.schema.json tests/test_render.py
git commit -m "feat: optional sources array in edition schema"
```

---

### Task 2: Renderer — the sources section

**Files:**
- Modify: `render.py` (new `render_sources` function; hook in `render_edition_body` after the desk-note append, currently lines 154-158)
- Test: `tests/test_render.py` (new `TestSourcesSection` class)

**Interfaces:**
- Consumes: edition dict key `sources` with entries `{url, title, publication, author?}` (Task 1).
- Produces: `render_sources(sources) -> str` returning `<section class="sources">...` markup with classes `sources`, `sources__list`, `sources__item` — Task 3's CSS targets exactly these class names.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_render.py`:

```python
class TestSourcesSection(unittest.TestCase):
    def _edition_with(self, sources):
        data = _load("in_season.json")
        data["sources"] = sources
        return data

    def test_sources_section_renders_after_signoff(self):
        body = render.render_edition_body(self._edition_with([
            {"url": "https://www.mlb.com/news/some-story", "title": "Some Story",
             "publication": "MLB.com", "author": "Jane Writer"},
        ]))
        self.assertIn("The Herald Acknowledges Its Debts", body)
        self.assertLess(body.index("~ THE HERALD ~"), body.index('class="sources"'))

    def test_entry_with_author_has_author_prefix(self):
        body = render.render_edition_body(self._edition_with([
            {"url": "https://www.mlb.com/news/some-story", "title": "Some Story",
             "publication": "MLB.com", "author": "Jane Writer"},
        ]))
        self.assertIn(
            '<li class="sources__item">Jane Writer, '
            '<a href="https://www.mlb.com/news/some-story" rel="noopener">Some Story</a>'
            ' &mdash; MLB.com</li>',
            body,
        )

    def test_entry_without_author_has_no_prefix(self):
        body = render.render_edition_body(self._edition_with([
            {"url": "https://boxscore.email/mlb/2026-08-09",
             "title": "Morning digest", "publication": "Boxscore"},
        ]))
        self.assertIn(
            '<li class="sources__item">'
            '<a href="https://boxscore.email/mlb/2026-08-09" rel="noopener">Morning digest</a>'
            ' &mdash; Boxscore</li>',
            body,
        )

    def test_url_is_attribute_escaped_and_text_is_escaped(self):
        body = render.render_edition_body(self._edition_with([
            {"url": 'https://example.com/?a=1&b="x"', "title": "Trades & Rumors",
             "publication": "P<Q>"},
        ]))
        self.assertIn('href="https://example.com/?a=1&amp;b=&quot;x&quot;"', body)
        self.assertIn(">Trades &amp; Rumors</a>", body)
        self.assertIn("P&lt;Q&gt;", body)

    def test_absent_null_and_empty_sources_render_no_section(self):
        absent = _load("in_season.json")
        absent.pop("sources", None)  # the fixture gains sources in Task 3
        for data in (absent,
                     self._edition_with(None),
                     self._edition_with([])):
            body = render.render_edition_body(data)
            self.assertNotIn('class="sources"', body)
            self.assertNotIn("Acknowledges Its Debts", body)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestSourcesSection -v`
Expected: the first four FAIL (no sources markup emitted); `test_absent_null_and_empty_sources_render_no_section` passes (nothing emits the section yet).

- [ ] **Step 3: Implement `render_sources` and hook it in**

In `render.py`, add above `render_edition_body`:

```python
def render_sources(sources):
    items = []
    for s in sources:
        prefix = render_inline(s["author"]) + ", " if s.get("author") else ""
        items.append(
            '<li class="sources__item">' + prefix
            + '<a href="' + html.escape(s["url"], quote=True) + '" rel="noopener">'
            + render_inline(s["title"]) + '</a> &mdash; '
            + render_inline(s["publication"]) + '</li>'
        )
    return (
        '<section class="sources">'
        '<h2 class="section__label">The Herald Acknowledges Its Debts</h2>'
        '<ul class="sources__list">' + "".join(items) + '</ul></section>'
    )
```

In `render_edition_body`, after the desk-note `parts.append(...)` (currently lines 154-158) and before `return "".join(parts)`, add:

```python
    sources = data.get("sources") or []
    if sources:
        parts.append(render_sources(sources))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: render The Herald Acknowledges Its Debts sources section"
```

---

### Task 3: CSS, end-to-end fixture, and site regeneration check

**Files:**
- Modify: `assets/herald.css` (new block after the "Desk note & sign-off" rules, currently lines 164-172)
- Modify: `tests/fixtures/in_season.json` (add a `sources` array)
- Modify: `tests/test_render.py` (one assertion each in `TestPipeline` and `TestPreview`)

**Interfaces:**
- Consumes: class names `sources`, `sources__list`, `sources__item` and heading markup from Task 2's `render_sources`.

- [ ] **Step 1: Add `sources` to the in-season fixture**

In `tests/fixtures/in_season.json`, add a top-level key (sibling of `desk_note`):

```json
  "sources": [
    {"url": "https://boxscore.email/mlb/2026-07-08",
     "title": "Morning digest for the games of July 8",
     "publication": "Boxscore"},
    {"url": "https://www.mlb.com/news/mudville-rally",
     "title": "Mudville rallies in the eleventh",
     "publication": "MLB.com",
     "author": "Jane Writer"}
  ]
```

(Adjust placement to keep the JSON valid; any position at the top level works.)

- [ ] **Step 2: Extend the pipeline and preview tests**

In `tests/test_render.py`, add to `TestPipeline.test_render_all_writes_editions_index_and_archive`, after the existing `archive` assertions:

```python
        july = (self.root / "editions" / "2026" / "07" / "09.html").read_text(encoding="utf-8")
        self.assertIn("The Herald Acknowledges Its Debts", july)
        self.assertIn('href="https://www.mlb.com/news/mudville-rally"', july)
```

Add to `TestPreview.test_preview_is_self_contained_and_styled`, after the existing assertions:

```python
        self.assertIn("The Herald Acknowledges Its Debts", page)  # sources render in previews
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_render -v`
Expected: all tests PASS (fixture already validates: Task 1 made `sources` legal; Task 2 renders it). If `TestSourcesSection.test_absent_null_and_empty_sources_render_no_section` fails because the fixture now carries `sources`, amend that test's absent case to pop the key first (`absent = _load("in_season.json"); absent.pop("sources", None)`) — this edit to `TestSourcesSection` is in scope for this task.

- [ ] **Step 4: Style the colophon**

In `assets/herald.css`, after the "Desk note & sign-off" block (the `.signoff` rule, currently ending line 172), add:

```css
/* ---- Sources colophon ---- */
.sources { margin-top: 2rem; font-size: 0.85rem; color: var(--ink-soft); }
.sources .section__label { font-size: 0.9rem; margin: 1.5rem 0 0.75rem; }
.sources__list { list-style: none; padding: 0; margin: 0; }
.sources__item { padding: 0.2rem 0; }
.sources__item a {
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--rule);
}
.sources__item a:hover { color: var(--red); }
```

- [ ] **Step 5: Visual check via preview**

Create `/private/tmp/claude-501/-Users-davidyeager-isitspringtrainingyet/a3dd97cf-4f79-493a-b164-f6d12a9d479a/scratchpad/sources-sample.json` by copying `editions/2026/08/10.json` and adding a realistic `sources` array (3-4 entries, at least one with an author), then:

```bash
python3 render.py --preview /private/tmp/claude-501/-Users-davidyeager-isitspringtrainingyet/a3dd97cf-4f79-493a-b164-f6d12a9d479a/scratchpad/sources-sample.json /private/tmp/claude-501/-Users-davidyeager-isitspringtrainingyet/a3dd97cf-4f79-493a-b164-f6d12a9d479a/scratchpad/sources-preview.html
```

Open/inspect the output: colophon sits below `~ THE HERALD ~`, small type, links underlined, authorless entries start with the link. (A grep-level check of the HTML is acceptable if no browser is available.)

- [ ] **Step 6: Confirm existing published pages are byte-identical**

```bash
python3 render.py --all
git status --porcelain
```

Expected: `git status` shows ONLY the intended modified files (`assets/herald.css`, `tests/...`) — **no changes** under `editions/`, `index.html`, or `archive.html`, since no published edition has `sources`. If any of those changed, stop and investigate before committing.

- [ ] **Step 7: Commit**

```bash
git add assets/herald.css tests/fixtures/in_season.json tests/test_render.py
git commit -m "feat: style sources colophon; exercise it end-to-end in fixtures"
```

---

### Task 4: Process docs — recipe.md and morning-dispatch skill

**Files:**
- Modify: `recipe.md` (new "The credits desk" section after "Formatting of prose fields", currently line 167; plus one step in "Producing and publishing an edition")
- Modify: `.claude/skills/morning-dispatch/SKILL.md` (procedure step + two common-mistake rows)

**Interfaces:**
- Consumes: the `sources` JSON shape from Task 1 (`url`, `title`, `publication`, `author?`).

- [ ] **Step 1: Add the credits-desk section to recipe.md**

Insert after the "Formatting of prose fields" section (after current line 167, before "## Producing and publishing an edition"):

```markdown
## The credits desk — cite what you used

Every edition ends with a citations colophon, "The Herald Acknowledges Its
Debts," built from the optional top-level `sources` array. Credit where it is
due:

- **Record as you write.** While composing, keep a running list of every page
  whose content contributes a printed fact — a story, a score, a schedule
  check that produced a printed claim. That list becomes `sources`.
- **Contributing means in print.** A page consulted but not used (a pre-flight
  check that yielded nothing printed) is NOT listed.
- **Entry shape:** `{"url", "title", "publication", "author"}` — `author` only
  when the page displays a byline. **Never invent or guess a byline**; omit
  `author` if you did not see one. Multiple bylines join naturally
  ("A. Writer and B. Scribe").
- **The boxscore.email entry cites the dated permalink.** You *fetch* the
  undated current edition (that rule is unchanged), but the undated URL shows
  a different edition tomorrow. Cite the dated permalink for the edition you
  used, after verifying it resolves (a `curl -s -o /dev/null -w "%{http_code}"`
  check with a browser User-Agent). If no working permalink exists, cite
  `https://boxscore.email/mlb` and put the edition's dateline in the title
  ("Morning digest for the games of <date>").
- Typical publications: "Boxscore", "MLB.com", "ESPN", "Baseball-Reference".
```

- [ ] **Step 2: Add the step to recipe.md's publishing checklist**

In "Producing and publishing an edition", renumber and insert after step 1:

```markdown
2. Compile the `sources` array from the credits desk's running list (see "The
   credits desk" above) and include it in the edition JSON.
```

(The existing steps 2-5 become 3-6.)

- [ ] **Step 3: Update the morning-dispatch skill**

In `.claude/skills/morning-dispatch/SKILL.md`:

(a) In the Procedure list, insert a new step after step 3 (the Variety pass), renumbering the rest:

```markdown
4. **Credits.** Per `recipe.md`'s "The credits desk": compile the `sources`
   array — every page that contributed a printed fact, with `url`, `title`,
   `publication`, and `author` only where a byline is shown. Cite
   boxscore.email by its **dated permalink** (verify it resolves with `curl`);
   never cite the undated current-edition URL.
```

(b) In step 4's schema bullet list (which becomes step 5), add a bullet:

```markdown
   - `sources` = the credits-desk list (see step 4). Omit only if genuinely
     nothing beyond the standard sources was used — an ordinary edition always
     has at least the boxscore entry.
```

(c) Add two rows to the "Common mistakes" table:

```markdown
| Citing `boxscore.email/mlb` (undated) in `sources` | Link shows a different edition tomorrow — dishonest citation | Cite the dated permalink for the edition actually used; verify it resolves |
| Inventing/guessing a byline for a source | Credits a person who didn't write it | Include `author` only when the page displays a byline; otherwise omit it |
```

- [ ] **Step 4: Verify docs render sensibly and nothing else broke**

Run: `python3 -m unittest tests.test_render -v`
Expected: all PASS (docs-only task; this is a guard).
Re-read both edited files once for numbering consistency (steps renumbered correctly, table intact).

- [ ] **Step 5: Commit**

```bash
git add recipe.md .claude/skills/morning-dispatch/SKILL.md
git commit -m "docs: credits desk — record and cite contributing sources"
```

---

## Verification (whole feature)

1. `python3 -m unittest tests.test_render -v` — all pass.
2. `python3 render.py --all && git status --porcelain` — no unexpected changes to published pages.
3. Preview from Task 3 Step 5 shows the colophon styled correctly.
4. Grep the plan's Global Constraints against the diff: heading text exact, `sources` not in schema `required`, entry format matches.
