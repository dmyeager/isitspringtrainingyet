# Design: Day-to-Day Variety for The Morning Horsehide Herald

**Date:** 2026-07-11
**Status:** Approved (design), pending implementation plan

## Scope

Two related pieces, designed together because the second is the test rig for the
first:

1. **Variety** — recipe/nicknames changes so editions stay fresh over a long run.
2. **Preview harness** — a way to generate an edition and eyeball it *without*
   going through the write → render → commit publish flow, so instruction tweaks
   (including the variety changes) are actually testable.

## Problem

The Herald's morning agent runs fresh each day from `recipe.md` + the
`morning-dispatch` skill, with **no memory of prior editions**. The prose is
strong, but over a long run of daily editions two kinds of staleness will creep
in:

1. **Repeated team epithets** — the same handles recur ("the Fish," "Pale Hose,"
   "Halos," "runaway Brewers") because the agent reaches for the same well every
   day with nothing telling it what it used yesterday.
2. **Repeated structural gambits** — most visibly the Game-of-the-Day opening
   flourish ("There is no fortress so grand that it cannot be stormed…").

The goal is **future freshness** without changing the voice the user already
likes. The agent already coins good epithets ("desert marauders" is invented,
not historical); we want to *protect and widen* that instinct, not replace it.

## Non-goals

- No change to the schema, the live site, or the published editions.
- No rolling "recently-used" ledger file or multi-day look-back (considered and
  rejected as over-built for the need — see Decisions).
- No change to the masthead, structure, or mode logic.
- The preview harness **never publishes** — no `editions/` writes, no root-page
  regeneration, no commits.

## Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Nickname bank strictness | **Curated bank + explicit license to coin.** A static list alone would *reduce* variety (agent cycles the same 2 handles); the bank is a *palette to draw from and depart from*, plus an authenticity anchor so coined epithets stay period-true. |
| Look-back depth | **Just yesterday, descriptors only.** Read only the most recent existing edition. Cheapest; catches the jarring day-to-day echoes. |
| Desk-note sign-off | **Canonize as a fixed signature.** The closing sentence "…keep your scorecards near and your enthusiasms nearer." is already the de facto closer on every edition; make it an intentional fixed signature (like the masthead motto), NOT something to vary. |
| Preview input | **Fixture by default, live on request.** A checked-in sample slate holds input constant for clean A/B of instruction tweaks; a `live` option fetches today's real slate for a realistic dry run. |
| Preview output | **Self-contained rendered HTML in a gitignored dir.** Not raw JSON dumped to chat and not a committed file — a browser-openable page (CSS inlined) the user peeks at and throws away. |
| Harness shape | **Separate `preview-edition` skill**, not a mode inside `morning-dispatch`, so the always-commit and never-commit instincts don't share one file. |

## Design

Three edits, all in the editorial layer. No code.

### 1. New file: `nicknames.md` (repo root)

A reference bank the recipe points to. Structure:

- **Preamble** stating the philosophy explicitly: these are genuine
  historical/period-authentic handles for each club; the agent may **use one,
  vary it, or coin a fresh one in the same deadball spirit** grounded in a real
  team trait that day. It must **never feel boxed into the list**, and should
  **not repeat the handle it used for a club in yesterday's edition** (ties into
  §2).
- **All 30 clubs**, each with ~3–6 authentic handles. Examples:
  - Yankees → the Americans, the Bronx Bombers, the Pinstripes
  - White Sox → the Pale Hose, the South Siders
  - Reds → the Redlegs
  - Pirates → the Buccaneers, the Corsairs
  - Cardinals → the Redbirds
  - Athletics → the White Elephants, the A's
  - Dodgers → the Bums (Brooklyn-era), the Boys in Blue
  - (…full 30 filled in during implementation, cross-checked so each handle is
    real/period-plausible, never fabricated nonsense.)

Placement at repo root alongside `recipe.md` keeps it discoverable and lets the
recipe reference it by a short relative path.

### 2. `recipe.md` — new "Variety" subsection + pointer

Add a short subsection (near **Voice**) that instructs the agent to, **before
writing**:

- Consult `nicknames.md` as a palette — draw from it, vary it, or coin in its
  spirit.
- **Glance at the most recent existing edition** under `editions/` (that is
  yesterday's, by construction — daily editions) and avoid reusing, for the
  clubs that appear in both:
  - the same **team epithets**, and
  - the same **Game-of-the-Day opening gambit**.
- Frame it as *reach for a different handle, not contort the prose* — variety is
  a light touch, not a mandate to be maximally different.

Also **canonize the sign-off**: state in the recipe (Structure → `desk_note`)
that the desk-note body varies daily but must **always close with the fixed
signature sentence** ending "…keep your scorecards near and your enthusiasms
nearer." The short lead-in ("Until the morrow's dispatch," / "Until the next
dispatch,") stays the agent's small choice. This closing is explicitly **exempt
from the "don't repeat yesterday" rule** — it is a signature, not an echo.

### 3. `SKILL.md` — one added procedure step

The `morning-dispatch` procedure runs the cloud agent, so the "read yesterday"
instruction must appear here too or it won't happen. Add a step (after reading
`recipe.md`, before building the edition):

> Read the most recent existing edition under `editions/` for variety — per
> recipe.md's Variety section, don't reuse its team epithets or its
> Game-of-the-Day opening gambit. Consult `nicknames.md` for alternative handles.

Optionally add a row to the skill's "Common mistakes" table if warranted.

## Design — Part 2: Preview / dry-run harness

The test rig for Part 1 (and any future instruction tweak). Lets you generate an
edition and see it rendered without touching the publish flow.

### 4. `render.py` — new `--preview <edition.json> <out.html>` mode

- Loads and **validates** the JSON against the schema (so a tweak that breaks
  structure surfaces as a loud error, same as a real run).
- Renders via the **existing pure `render_edition(data, template)`** — no new
  rendering logic, just a new entry point.
- Produces a **self-contained** page: inline `assets/herald.css` as a `<style>`
  block instead of the `<link rel="stylesheet" href="/assets/herald.css">`, and
  neutralize the nav links (`/`, `/archive.html`) so nothing dangles. Rationale:
  the template's absolute `/assets/...` path does not resolve under `file://`, so
  a preview opened from a gitignored dir would otherwise be unstyled.
- Writes **only** to the given output path. Never calls `render_all`; never
  touches `editions/`, `index.html`, or `archive.html`.
- Likely shape: a `render_preview(root, json_path, out_path)` helper + a template
  variant (or post-process) that swaps the stylesheet link for an inline style;
  wire into `main()` as `--preview <in> <out>`.

### 5. New skill: `preview-edition`

Separate skill, sharing `recipe.md`/`nicknames.md` as editorial truth but with
**inverted guardrails** (never publish). Procedure:

1. **Choose input.** Default = **fixture**; `live` on request.
   - *Fixture*: read the checked-in raw slate at `tests/fixtures/sample-slate.md`
     (a saved `boxscore.email/mlb` day — committed, the stable A/B input). The
     agent treats it exactly as it would a live fetch.
   - *Live*: fetch the **current** `boxscore.email/mlb` (same rules as
     `morning-dispatch` — no date in the URL).
2. **Compose the edition JSON in memory** per `recipe.md` + `nicknames.md` + the
   Variety rules. May read the latest existing edition under `editions/`
   (read-only) for the "don't repeat yesterday" check.
3. **Write throwaway artifacts to gitignored `preview/`**: the composed JSON and
   the rendered HTML.
4. **Render**: `python3 render.py --preview preview/edition.json preview/index.html`.
5. **Report**: print the `preview/index.html` path for the user to open, and echo
   the Game-of-the-Day headline + desk-note inline for instant signal.
6. **Guardrail (hard):** never write under `editions/`, never regenerate the root
   `index.html`/`archive.html`, never `git add`/`commit`/`push`. A preview leaves
   the repo's tracked files untouched.

### 6. `tests/fixtures/sample-slate.md` (new, committed)

A saved copy of one real `boxscore.email/mlb` day's slate — the raw source
material the agent composes from, **not** a finished edition. Committed because
it is the stable input that makes tweak-to-tweak comparison meaningful. (Distinct
from the existing `in_season.json`/`hot_stove.json`, which are finished editions
for renderer tests.)

### 7. `.gitignore` — add `preview/`

So preview JSON/HTML never enters git history.

## How the pieces fit

```
recipe.md  ◀── nicknames.md          (editorial truth, shared)
   ▲   Variety subsection:
   │   - palette philosophy
   │   - avoid yesterday's epithets + GotD gambit
   │   - canonized sign-off
   │
   ├───────────────┬────────────────────────────────┐
   │               │                                 │
morning-dispatch   preview-edition                   │
(PUBLISH)          (NEVER PUBLISH)                    │
   │               │  input: fixture (default)|live  │
   ▼               ▼                                  │
writes             composes JSON in memory            │
editions/…  ──▶    render.py --preview ──▶ preview/index.html (gitignored)
render_all,        (self-contained, CSS inlined)      │
commit, push       report path + GotD inline          │
```

## Risks & mitigations

- **Bank becomes a crutch → *less* variety.** Mitigated by framing (§1 preamble)
  as a palette to depart from, plus the "don't repeat yesterday" rule.
- **Fabricated nicknames.** Mitigated by curating real/period-plausible handles
  during implementation; the recipe's "never fabricate" rule still governs.
- **Over-correction into awkward prose.** Mitigated by the "light touch" framing
  in §2.
- **Token cost of reading yesterday.** One JSON file; negligible.
- **Preview accidentally publishes.** Mitigated by a separate skill with hard
  never-commit guardrails, `--preview` writing only to the given path, and
  `preview/` being gitignored so stray artifacts can't be committed anyway.
- **Preview drifts from the real render.** Mitigated by reusing the same
  `render_edition()` function; only asset resolution differs (inlined vs linked).

## Testing / acceptance

**Part 1 (variety):**
- `nicknames.md` exists, covers all 30 clubs, handles are real/period-plausible.
- `recipe.md` Variety subsection + canonized sign-off present and internally
  consistent with existing sections.
- `morning-dispatch` SKILL.md has the read-yesterday step.

**Part 2 (preview):**
- `python3 render.py --preview <fixture-edition.json> preview/out.html` produces a
  self-contained, correctly-styled page and writes **nothing** else (verify
  `editions/`, `index.html`, `archive.html` unchanged; `git status` clean of
  tracked files).
- `--preview` still validates: a malformed edition JSON fails loudly.
- `preview/` is gitignored.
- `tests/fixtures/sample-slate.md` exists and is a raw slate, not a finished
  edition.
- `preview-edition` skill runs the fixture path end-to-end and leaves tracked
  files untouched.
- Existing `tests/test_render.py` still passes; the normal publish flow
  (`render.py <edition.json>` / `--all`) is unchanged.
