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
