# Herald Variety & Preview Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the Herald's daily editions fresh over a long run (a team-nickname palette, a "don't repeat yesterday" rule, a canonized sign-off) and add a preview/dry-run harness so instruction tweaks can be seen rendered without going through the publish flow.

**Architecture:** Two parts that ship together. Part A is a preview harness: a new `render.py --preview` mode that reuses the existing pure `render_edition()` to write a self-contained (CSS-inlined) HTML file anywhere, plus a separate `preview-edition` skill that composes an edition in memory (from a committed fixture slate or a live fetch) and renders it into a gitignored `preview/` dir, never publishing. Part B is editorial: a `nicknames.md` palette, a Variety subsection in `recipe.md`, a canonized desk-note sign-off, and a read-yesterday step in the `morning-dispatch` skill.

**Tech Stack:** Python 3 (stdlib only — no third-party deps), `unittest`, Markdown skills/recipe files, static HTML/CSS.

## Global Constraints

- **No third-party Python dependencies.** `render.py` is stdlib-only; keep it that way.
- **The preview path NEVER publishes:** it must not write under `editions/`, must not regenerate root `index.html`/`archive.html`, and must not `git add`/`commit`/`push`.
- **Never fabricate baseball facts in a published edition.** Test fixtures may contain clearly-labeled synthetic data; real editions may not.
- **Prose fields are plain text** with `*italic*`/`**bold**` only — no HTML. (Unchanged; relevant when editing recipe examples.)
- **`recipe.md` is the editorial source of truth**; skills wire the operational procedure around it.
- Run tests with: `python3 -m unittest discover -s tests -v` from the repo root.

---

## Task 1: `render.py --preview` mode (self-contained render, no publish)

Adds a preview renderer that turns one edition JSON into a self-contained, correctly-styled HTML file at an arbitrary path, without touching any published output.

**Files:**
- Modify: `render.py` (add `inline_preview_assets()`, `render_preview()`, and a `--preview` branch in `main()`)
- Test: `tests/test_render.py` (add a `TestPreview` class)

**Interfaces:**
- Consumes (existing, unchanged): `render_edition(data, base_template)`, `validate(data, schema)`, `_load_template(root)`, `_load_schema(root)`.
- Produces:
  - `inline_preview_assets(page_html: str, root) -> str` — returns `page_html` with the `<link rel="stylesheet" href="/assets/herald.css">` replaced by an inline `<style>…</style>` block containing `assets/herald.css`, and the absolute nav links (`href="/"`, `href="/archive.html"`) neutralized to `href="#"`.
  - `render_preview(root, json_path, out_path) -> None` — loads + validates the edition JSON, renders it, inlines assets, and writes the result to `out_path` (creating parent dirs). Writes nothing else.
  - CLI: `python3 render.py --preview <edition.json> <out.html>`.

- [ ] **Step 1: Write the failing tests**

Add this class to the end of `tests/test_render.py` (before the `if __name__ == "__main__":` block). It reuses the existing module-level `FIXTURES` / `_load` helpers.

```python
class TestPreview(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        repo = pathlib.Path(__file__).resolve().parent.parent
        for sub in ("templates", "schema", "assets"):
            (self.root / sub).mkdir()
        shutil.copy(repo / "templates" / "base.html", self.root / "templates" / "base.html")
        shutil.copy(repo / "schema" / "edition.schema.json", self.root / "schema" / "edition.schema.json")
        shutil.copy(repo / "assets" / "herald.css", self.root / "assets" / "herald.css")
        # A valid edition JSON to preview.
        y, m, d = "2026", "07", "09"
        src = self.root / "editions" / y / m
        src.mkdir(parents=True, exist_ok=True)
        self.edition = src / (d + ".json")
        shutil.copy(FIXTURES / "in_season.json", self.edition)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_preview_is_self_contained_and_styled(self):
        out = self.root / "preview" / "index.html"
        render.render_preview(self.root, self.edition, out)
        page = out.read_text(encoding="utf-8")
        self.assertIn("MUDVILLE THUNDERS", page)                 # the edition rendered
        self.assertIn("<style>", page)                            # CSS inlined
        self.assertIn("period broadsheet stylesheet", page)       # actual herald.css content present
        self.assertNotIn('<link rel="stylesheet"', page)          # no external stylesheet link
        self.assertNotIn('href="/"', page)                        # absolute nav links neutralized
        self.assertNotIn('href="/archive.html"', page)

    def test_preview_writes_nothing_but_the_output(self):
        out = self.root / "preview" / "index.html"
        render.render_preview(self.root, self.edition, out)
        self.assertFalse((self.root / "index.html").exists())     # no homepage
        self.assertFalse((self.root / "archive.html").exists())   # no archive
        self.assertFalse((self.root / "editions" / "2026" / "07" / "09.html").exists())  # no edition page

    def test_preview_validates_and_refuses_bad_json(self):
        bad = self.root / "editions" / "2026" / "07" / "10.json"
        bad.write_text('{"meta": {"mode": "in_season"}}', encoding="utf-8")
        out = self.root / "preview" / "bad.html"
        with self.assertRaises(ValueError):
            render.render_preview(self.root, bad, out)
        self.assertFalse(out.exists())                            # nothing written on failure
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_render.TestPreview -v`
Expected: FAIL — `AttributeError: module 'render' has no attribute 'render_preview'`.

- [ ] **Step 3: Implement `inline_preview_assets` and `render_preview`**

In `render.py`, add these two functions immediately after `render_one` (around line 247):

```python
def inline_preview_assets(page_html, root):
    """Make a rendered page self-contained: inline the stylesheet and neutralize
    absolute nav links so it renders correctly opened directly from disk."""
    css = (Path(root) / "assets" / "herald.css").read_text(encoding="utf-8")
    page_html = page_html.replace(
        '<link rel="stylesheet" href="/assets/herald.css">',
        "<style>\n" + css + "\n</style>",
    )
    page_html = page_html.replace('href="/archive.html"', 'href="#"')
    page_html = page_html.replace('href="/"', 'href="#"')
    return page_html


def render_preview(root, json_path, out_path):
    """Render a single edition JSON to a self-contained HTML file at out_path.
    Validates first; writes nothing but out_path; never regenerates the site."""
    root = Path(root)
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    validate(data, _load_schema(root))            # fail loudly before writing anything
    page = render_edition(data, _load_template(root))
    page = inline_preview_assets(page, root)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
```

Note on ordering: replace `href="/archive.html"` **before** `href="/"` is not strictly required (the strings don't overlap because of the closing quote), but doing the longer one first is defensive.

- [ ] **Step 4: Wire `--preview` into `main()`**

Replace the existing `main()` (lines ~250-259) with:

```python
def main(argv):
    root = Path(__file__).resolve().parent
    if len(argv) == 4 and argv[1] == "--preview":
        render_preview(root, argv[2], argv[3])
    elif len(argv) == 2 and argv[1] == "--all":
        render_all(root)
    elif len(argv) == 2:
        render_one(root, argv[1])
    else:
        print("usage: render.py <edition.json> | --all | --preview <edition.json> <out.html>",
              file=sys.stderr)
        return 2
    return 0
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `python3 -m unittest tests.test_render.TestPreview -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the full suite to confirm nothing regressed**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (all prior tests + the 3 new ones).

- [ ] **Step 7: Commit**

```bash
git add render.py tests/test_render.py
git commit -m "feat: render.py --preview mode for self-contained edition previews

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Gitignore the preview dir + add the fixture slate

Supporting artifacts for the preview skill: a committed synthetic slate to preview against, and a gitignore rule so preview output never enters history.

**Files:**
- Modify: `.gitignore`
- Create: `tests/fixtures/sample-slate.md`

**Interfaces:**
- Produces: `tests/fixtures/sample-slate.md` — a raw, pre-prose game slate the `preview-edition` skill composes an edition from. `preview/` is untracked.

- [ ] **Step 1: Add `preview/` to `.gitignore`**

Append to `.gitignore` (current contents are `__pycache__/`, `*.pyc`, `.DS_Store`):

```
preview/
```

- [ ] **Step 2: Create the fixture slate**

Create `tests/fixtures/sample-slate.md` with exactly this content. It is clearly-labeled **synthetic** data — never published, used only to exercise the preview harness with a stable input.

```markdown
# SAMPLE SLATE — SYNTHETIC TEST DATA (not a real day)

Fixed input for the `preview-edition` harness. Hold this constant to A/B-test
recipe/nicknames tweaks: the same slate in, so any change in the prose out is due
to the instruction change. NOT a real box score — never publish an edition built
from this file.

Game date reported: the prior day. Publication date: use today when previewing.

## Final scores (14 contests)

- Athletics 2, White Sox 9 — Chicago's Vargas 3-for-4, two home runs (18, 19), 5 RBI. LP Athletics' Sears (2-9).
- Dodgers 3, Diamondbacks 8 — Arizona's Marte 4-for-5, 3 RBI; Carroll HR (22). Ohtani HR (34) for LA. WP Rodriguez (9-3).
- Phillies 2, Tigers 11 — Detroit's Torkelson 2 HR (17, 18), 4 RBI; Keith HR. Tigers' 7th straight win. WP Flaherty (4-8).
- Nationals 3, Yankees 6 — New York 4 HR: Rice (30), Chisholm, Wells, Dominguez. Wood HR (27) for Washington.
- Royals 3, Orioles 5 — Baltimore's Basallo 2 RBI (HR 16); Henderson RBI single. SV Kittredge (4).
- Cubs 1, Reds 5 — Cincinnati's De La Cruz HR + triple; Greene 7 shutout-caliber innings (2-1). Suzuki 2B for Chicago.
- Marlins 2, Guardians 3 — Cleveland's DeLauter HR, 2 RBI. SV Smith (29, AL lead). Alcantara (10-6) hard-luck LP.
- Mariners 2, Rays 8 — Tampa Bay 4 HR incl. Caminero (29). Castillo (3-9) LP. Young HR for Seattle.
- Mets 2, Red Sox 7 — Boston 8th straight; Gray to 12-1 (AL wins lead). Abreu HR, 2 RBI; Yoshida 2 2B.
- Twins 3, Angels 5 — LA's Grissom HR, 2 RBI. SV Yates (4). Twins managed six doubles, no HR.
- Astros 3, Rangers 8 — Texas 3 HR: Burger (2-run), Pederson, Langford. Alvarez HR (31, AL HR lead) in defeat.
- Braves 1, Cardinals 3 — St. Louis's Crooks HR; Walker RBI single (76, NL RBI lead). SV O'Brien (24).
- Padres 3, Blue Jays 6 — Toronto's Okamoto 3-run HR (23). Bogaerts HR, 2 RBI for San Diego. LP San Diego's Vasquez (2-3).
- Giants 3, Rockies 5 — Colorado stuns SF on the road; Karros 2 RBI. Senzatela (10-1). Devers HR, 3 RBI for the Giants.

## Around the league

- Rumor: a veteran left-hander may be dealt before the deadline.
- Injury: a contending club's closer is day-to-day with a tight forearm.

## Standings notes

- NL: Dodgers lead the West and all of baseball; Brewers lead the Central with the best run differential; Braves lead the East.
- AL: Rays lead the East; Rangers lead the West by a game and a half over Seattle; White Sox and Guardians deadlocked in the Central, Detroit surging.

## Leaders (selected)

- AL: Alvarez 31 HR; Diaz .322 AVG; Witt Jr. 31 SB; Gray 12 wins.
- NL: Schwarber 32 HR; Walker 76 RBI; Lopez .341 AVG; Misiorowski 1.62 ERA.
```

- [ ] **Step 3: Verify the fixture is untracked-safe and slate is present**

Run: `git check-ignore -v preview/ ; test -f tests/fixtures/sample-slate.md && echo "slate present"`
Expected: the first command prints the matching `.gitignore` rule for `preview/`; the second prints `slate present`.

- [ ] **Step 4: Commit**

```bash
git add .gitignore tests/fixtures/sample-slate.md
git commit -m "chore: gitignore preview/ and add synthetic fixture slate for previews

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `preview-edition` skill

The operator procedure for the harness: compose an edition in memory from the fixture (default) or a live fetch, render it to gitignored `preview/`, report the path, and never publish.

**Files:**
- Create: `.claude/skills/preview-edition/SKILL.md`

**Interfaces:**
- Consumes: `render.py --preview` (Task 1), `tests/fixtures/sample-slate.md` (Task 2), `recipe.md`, `nicknames.md` (Task 4 — referenced; the skill still works before Task 4 lands, it just won't have the palette to consult yet).
- Produces: a skill invocable as "preview edition" / "dry-run edition" / "preview the paper".

- [ ] **Step 1: Create the skill file**

Create `.claude/skills/preview-edition/SKILL.md` with exactly this content:

```markdown
---
name: preview-edition
description: Use to preview/dry-run an edition of The Morning Horsehide Herald WITHOUT publishing — to see how a recipe/nicknames/instruction tweak renders. Triggers include "preview edition", "dry-run edition", "preview the paper", "test the recipe". This never writes to editions/ and never commits.
---

# Preview Edition — dry-run the Herald without publishing

## Overview

Generate one edition and render it to a throwaway, gitignored HTML file you can
open in a browser — **without** writing to `editions/`, regenerating the site, or
committing anything. This is the test rig for editorial tweaks: change
`recipe.md` or `nicknames.md`, preview against the fixed sample slate, and read
the difference in the prose.

## The one rule that separates this from morning-dispatch

**This skill NEVER publishes.** It must not create or modify anything under
`editions/`, must not regenerate `index.html`/`archive.html`, and must not
`git add`/`commit`/`push`. Every artifact it produces lives under the gitignored
`preview/` directory. If you catch yourself about to write into `editions/`, stop
— that is the `morning-dispatch` skill, not this one.

## Input modes

- **fixture (default):** compose from `tests/fixtures/sample-slate.md` — a fixed
  synthetic slate. Use this for A/B-testing instruction tweaks: same input in, so
  any change in the output is the tweak's doing.
- **live (on request — "preview live"):** fetch the **current** `boxscore.email/mlb`
  edition (plain URL, no date — same source rule as `morning-dispatch`) for a
  realistic end-to-end dry run.

## Procedure

1. Read `recipe.md` (editorial truth) and `nicknames.md` (the epithet palette).
2. Get the slate:
   - fixture mode: read `tests/fixtures/sample-slate.md`.
   - live mode: fetch `boxscore.email/mlb`'s current edition (curl with a normal
     User-Agent if WebFetch is blocked). Never fabricate; omit the unverifiable.
3. For the Variety pass, read the most recent existing edition under `editions/`
   (read-only — do not modify it) so you can avoid repeating its team epithets and
   its Game-of-the-Day opening gambit.
4. Compose the edition as JSON conforming to `schema/edition.schema.json`, exactly
   as `recipe.md` directs. For `meta.date` use **today** (the preview is a stand-in
   for a publication morning). Hold the JSON in memory / write it only under
   `preview/` — NOT under `editions/`.
5. Write the composed JSON to `preview/edition.json`.
6. Render it: `python3 render.py --preview preview/edition.json preview/index.html`.
   On a validation error, fix the JSON and re-run until it exits 0 — the same
   schema gate a real edition faces.
7. Report to the user: the path `preview/index.html` to open in a browser, plus an
   inline echo of the Game-of-the-Day headline and the desk-note so they get an
   immediate read on the voice.

## Fail-safe

There is nothing to fail *safe* toward here because nothing is published: on any
error, simply report it. But never "recover" by writing into `editions/` or
committing — a broken preview is fine; a stray publish is not.
```

- [ ] **Step 2: Smoke-test the harness end-to-end against the fixture**

This exercises Task 1's renderer through a hand-built edition (no LLM needed to verify the plumbing). Run from the repo root:

```bash
mkdir -p preview
cp tests/fixtures/in_season.json preview/edition.json
python3 render.py --preview preview/edition.json preview/index.html
echo "exit=$?"
test -f preview/index.html && grep -q "period broadsheet stylesheet" preview/index.html && echo "styled preview OK"
git status --porcelain preview/    # expect NO output — preview/ is ignored
```

Expected: `exit=0`, `styled preview OK`, and `git status` shows nothing for `preview/`.

- [ ] **Step 3: Commit the skill**

```bash
git add .claude/skills/preview-edition/SKILL.md
git commit -m "feat: preview-edition skill for non-publishing edition dry-runs

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `nicknames.md` team-epithet palette

The curated palette of period-authentic team handles, framed as something to draw from *and depart from*.

**Files:**
- Create: `nicknames.md` (repo root)

**Interfaces:**
- Produces: `nicknames.md`, referenced by `recipe.md` (Task 5) and consulted by both `morning-dispatch` and `preview-edition`.

- [ ] **Step 1: Create `nicknames.md`**

Create `nicknames.md` at the repo root with exactly this content:

```markdown
# The Herald's Book of Club Epithets

A palette of period-authentic handles for every club — **to draw from and to
depart from.** The Herald's voice thrives on variety, so:

- **Use** one of a club's handles when it fits the day's story.
- **Vary** it — do not lean on the same handle for the same club two editions
  running (the morning routine reads yesterday's edition to check).
- **Coin** a fresh epithet in the same deadball spirit when the day gives you a
  hook (a trait, a hot streak, a ballpark, a feat) — "the desert marauders" was
  invented, not looked up, and that instinct is welcome. Just keep it
  period-true and grounded in something real; never fabricate a fact to justify
  a nickname.

Never feel boxed in by this list. It is a floor for variety, not a lookup table.
Handles marked *(hist.)* are genuine historical names — safe and flavorful.

## American League

**East**
- Baltimore Orioles — the Orioles, the O's, the Birds, the Baltimores
- Boston Red Sox — the Red Sox, the Crimson Hose, the Hub nine, the Bostons, the Fenway men
- New York Yankees — the Yankees, the Americans, the Bronx Bombers, the Pinstripes, the Highlanders *(hist.)*
- Tampa Bay Rays — the Rays, the Bay nine, the Tampa men, the Gulf Coast club, the Sunshine nine
- Toronto Blue Jays — the Blue Jays, the Jays, the Torontos, the Maple Leaf nine, the Canadians

**Central**
- Chicago White Sox — the White Sox, the Pale Hose, the South Siders, the White Stockings *(hist.)*, the Chicagos
- Cleveland Guardians — the Guardians, the Cleveland nine, the Lake Erie men, the Forest City nine *(hist.)*, the Naps *(hist.)*
- Detroit Tigers — the Tigers, the Bengals, the Motor City nine, the Detroits
- Kansas City Royals — the Royals, the Kansas City nine, the Royal blues, the Missourians
- Minnesota Twins — the Twins, the Twin Cities nine, the Minnesotans, the Millers *(hist.)*

**West**
- Houston Astros — the Astros, the 'Stros, the Houston nine, the Colt .45s *(hist.)*, the Texans
- Los Angeles Angels — the Angels, the Halos, the Seraphs, the Anaheim nine
- Athletics — the Athletics, the A's, the White Elephants *(hist.)*, the Elephants, the Mackmen *(hist.)*
- Seattle Mariners — the Mariners, the M's, the Seattle nine, the Puget Sound men, the mariners of the Sound
- Texas Rangers — the Rangers, the Texas nine, the Arlington men, the Lone Star nine

## National League

**East**
- Atlanta Braves — the Braves, the Atlantas, the Tomahawk nine, the Dixie nine
- Miami Marlins — the Marlins, the Fish, the Miami nine, the Gulf Stream nine, the Floridians
- New York Mets — the Mets, the Metropolitans *(hist.)*, the Amazins, the Flushing nine
- Philadelphia Phillies — the Phillies, the Phils, the Quakers *(hist.)*, the Philadelphias, the Brotherly Love nine
- Washington Nationals — the Nationals, the Nats, the Senators *(hist.)*, the Capital nine, the Washingtons

**Central**
- Chicago Cubs — the Cubs, the Cubbies, the North Siders, the Bruins, the Colts *(hist.)*, the Orphans *(hist.)*
- Cincinnati Reds — the Reds, the Redlegs, the Red Stockings *(hist.)*, the Queen City nine, the Cincinnatis
- Milwaukee Brewers — the Brewers, the Brew Crew, the Cream City nine, the Milwaukees, the Suds men
- Pittsburgh Pirates — the Pirates, the Buccaneers, the Bucs, the Corsairs, the Smoky City nine, the Alleghenys *(hist.)*
- St. Louis Cardinals — the Cardinals, the Redbirds, the Cards, the Gas House nine *(hist.)*, the Mound City nine

**West**
- Arizona Diamondbacks — the Diamondbacks, the D-backs, the Snakes, the Desert nine, the Sonoran nine
- Colorado Rockies — the Rockies, the Rox, the Mountain men, the Mile High nine, the Coloradans
- Los Angeles Dodgers — the Dodgers, the Boys in Blue, the Bums *(hist.)*, the Trolley Dodgers *(hist.)*, the Angelenos
- San Diego Padres — the Padres, the Friars, the Pads, the Mission nine, the San Diego nine
- San Francisco Giants — the Giants, the Jints *(hist.)*, the Bay nine, the Orange and Black, the Frisco nine
```

- [ ] **Step 2: Sanity-check coverage**

Run: `grep -cE '^- [A-Z]' nicknames.md`
Expected: `30` (one bullet per club; the pattern matches club lines by their capitalized city, excluding the preamble's `- **Use**`-style bullets).

- [ ] **Step 3: Commit**

```bash
git add nicknames.md
git commit -m "feat: add nicknames.md — team-epithet palette for edition variety

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `recipe.md` — Variety subsection, sign-off canonization, palette pointer

Wire the variety instructions into the editorial source of truth: point at the palette, add the "don't repeat yesterday" rule, and canonize the desk-note sign-off.

**Files:**
- Modify: `recipe.md` (add a `## Variety` section; edit the `desk_note` structure item; the Variety section carries the `nicknames.md` pointer)

**Interfaces:**
- Consumes: `nicknames.md` (Task 4).
- Produces: recipe guidance that both `morning-dispatch` (Task 6) and `preview-edition` (Task 3) rely on.

- [ ] **Step 1: Canonize the sign-off in the Structure section**

In `recipe.md`, find the `desk_note` bullet (item 4 under "Structure → schema mapping", currently):

```
4. Closing **word from the desk** → `desk_note` (a string). The renderer adds the
   ~ THE HERALD ~ sign-off after it.
```

Replace it with:

```
4. Closing **word from the desk** → `desk_note` (a string). The renderer adds the
   ~ THE HERALD ~ sign-off after it. The desk-note's body varies each day, but it
   **always closes with the Herald's fixed signature sentence** — a lead-in of
   your choosing ("Until the morrow's dispatch," / "Until the next dispatch,")
   followed by the invariant words *"keep your scorecards near and your
   enthusiasms nearer."* This closing is a signature, like the masthead motto; it
   is **exempt** from the Variety rule below — never reword it.
```

- [ ] **Step 2: Add the `## Variety` section**

In `recipe.md`, insert this new section immediately after the `## Voice` section (after the paragraph ending "…the facts underneath stay strictly accurate.") and before `## Formatting of prose fields`:

```markdown
## Variety

The Herald runs every day; guard against staleness so a run of editions never
feels like a template.

- **Consult the epithet palette.** `nicknames.md` holds period-authentic handles
  for all thirty clubs. Draw from it, vary it, or coin a fresh epithet in the
  same deadball spirit grounded in the day's real story (a trait, a streak, a
  ballpark, a feat). It is a floor for variety, not a lookup table — never feel
  boxed into it, and never fabricate a fact to justify a nickname.
- **Don't repeat yesterday.** Before writing, glance at the most recent existing
  edition under `editions/`. For clubs that appear in both, avoid reusing **its
  team epithets** and avoid reusing **its Game-of-the-Day opening gambit** (the
  first-sentence flourish). Reach for a different handle or a different way in.
- **A light touch.** Variety is a seasoning, not a mandate to be maximally
  different. Don't contort the prose or strain for novelty — just don't lean on
  the same well two mornings running. The fixed sign-off (see the desk-note item
  above) is the one deliberate exception: it stays the same on purpose.
```

- [ ] **Step 3: Verify the edits are present and consistent**

Run: `grep -n "keep your scorecards near" recipe.md ; grep -n "^## Variety" recipe.md ; grep -n "nicknames.md" recipe.md`
Expected: one hit for the signature sentence, one hit for the `## Variety` heading, and at least one hit for the `nicknames.md` pointer.

- [ ] **Step 4: Commit**

```bash
git add recipe.md
git commit -m "feat: recipe Variety section, canonized sign-off, palette pointer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `morning-dispatch` skill — read-yesterday variety step

Make the daily publish flow actually perform the Variety pass (the cloud agent runs from this skill, so the instruction must appear here, not only in `recipe.md`).

**Files:**
- Modify: `.claude/skills/morning-dispatch/SKILL.md` (add a variety step to the Procedure)

**Interfaces:**
- Consumes: `recipe.md` Variety section (Task 5), `nicknames.md` (Task 4).
- Produces: no new interface; the daily run now varies epithets/openers against yesterday.

- [ ] **Step 1: Add the variety step to the Procedure**

In `.claude/skills/morning-dispatch/SKILL.md`, the Procedure currently has step 3 beginning "Build the edition per `schema/edition.schema.json`:". Insert a new step **between** the current step 2 (fetch boxscore.email) and step 3 (build), renumbering the rest. The inserted step:

```
3. **Variety pass.** Read the most recent existing edition under `editions/`
   (read-only). Per `recipe.md`'s Variety section, don't reuse its team epithets
   or its Game-of-the-Day opening gambit; consult `nicknames.md` for alternative
   handles. (The desk-note's fixed signature sign-off is exempt — keep it.)
```

Renumber the subsequent steps (old 3→4, 4→5, 5→6, 6→7, 7→8) so the list stays sequential.

- [ ] **Step 2: Add a row to the "Common mistakes" table**

In the same file, add this row to the "Common mistakes (observed in production)" table:

```
| Reusing yesterday's epithets/opening gambit | Editions feel like a template | Do the Variety pass: read yesterday, vary handles (see `nicknames.md`), find a fresh way in |
```

- [ ] **Step 3: Verify the edits**

Run: `grep -n "Variety pass" .claude/skills/morning-dispatch/SKILL.md ; grep -c "^[0-9]\." .claude/skills/morning-dispatch/SKILL.md`
Expected: the "Variety pass" step is present; the numbered Procedure steps count is 8 (was 7).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/morning-dispatch/SKILL.md
git commit -m "feat: morning-dispatch variety pass (read yesterday, vary epithets)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] **Full test suite:** `python3 -m unittest discover -s tests -v` → all pass.
- [ ] **Preview plumbing end-to-end:** the Task 3 Step 2 smoke test produces a styled `preview/index.html` that `git status` ignores.
- [ ] **Publish flow untouched:** `python3 render.py --all` still regenerates the site with no errors, and `git status` shows no unintended changes under `editions/`.
- [ ] **Coverage sanity:** `nicknames.md` lists 30 clubs; `recipe.md` has the Variety section, the canonized sign-off, and the palette pointer; both skills reference the Variety behavior.
```
