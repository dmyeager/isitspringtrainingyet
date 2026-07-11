---
name: morning-dispatch
description: Use when running the "morning dispatch" for The Morning Horsehide Herald in this repo — generating and publishing today's daily baseball edition to isitspringtrainingyet.com. Triggers include "morning dispatch", "publish today's edition", "run the Herald/paper".
---

# Morning Dispatch — The Morning Horsehide Herald

## Overview

Produce and publish today's edition of The Morning Horsehide Herald. You write the edition as structured JSON; `render.py` turns it into the static site; a `git push` auto-deploys via GitHub Pages. **`recipe.md` is the editorial source of truth** (voice, sources, structure, in-season vs. hot-stove) — follow it for every content decision. This skill is the operational procedure around it.

## The rule that trips everyone up

The edition is **dated by its publication morning (today)** and reports **yesterday's** games. Fetch boxscore.email/mlb's **current** edition — plain `boxscore.email/mlb`, **no date in the URL, never browse for a date**. That current edition is itself a morning digest of the prior day's completed games — that IS your slate.

## Procedure

1. Read `recipe.md`; follow it for voice, sources of truth, structure, and the mode decision.
2. Fetch boxscore.email/mlb's **current** edition (if WebFetch is blocked, `curl` with a normal browser User-Agent). Cross-check team affiliations on baseball-reference.com. **Never fabricate**; omit anything unverifiable.
3. Build the edition per `schema/edition.schema.json`:
   - `meta.date` = **today** (US Eastern), `YYYY-MM-DD` — the *publication* date, NOT the game date. On a normal morning run this equals the dateline of boxscore.email's current edition; **never advance to a future date.** If `editions/YYYY/MM/DD.json` for today already exists, today's edition is already published — stop (don't overwrite or future-date unless the user explicitly asks to regenerate it).
   - `meta.weekday` + a flowery `meta.date_display` for today.
   - `meta.edition_number` = one greater than the highest existing `edition_number` under `editions/`.
   - Mode: games played → `in_season` (Game of the Day + News + **every** remaining game, no score unreported); none → `hot_stove` + a `countdown`.
   - Prose fields: plain text, `*italic*` / `**bold**` (markers hug the word), blank line between paragraphs, **no HTML**.
4. Write it to `editions/YYYY/MM/DD.json` (today's date).
5. Render (from the repo root): `python3 render.py editions/YYYY/MM/DD.json`. On a validation error, fix the JSON and re-run until it exits 0.
6. (Optional) open `index.html` to eyeball it.
7. Commit the JSON + regenerated `index.html`, `archive.html`, and the edition page — `git commit -m "edition: YYYY-MM-DD"` — then `git push`. Pages redeploys in ~a minute.

## Fail-safe

A failed or incomplete run must produce **no commit** — the previous edition stays live. If a source is down, validation fails, or data can't be verified, **stop without committing** rather than publish something wrong.

## Common mistakes (observed in production)

| Mistake | Consequence | Do instead |
|---|---|---|
| Fetching a *dated* boxscore.email page | Games a day too old (the site is itself a morning digest) | Fetch the **current** edition only |
| Dating the edition by the **game** day | Off-by-one; masthead contradicts "day prior" | `meta.date` = today (publication); games are yesterday |
| `git commit` before `render.py` passes | Publishes broken/unvalidated output | Render first; commit only on exit 0 |
| Writing HTML in prose fields | Double-escaped / broken markup | Plain text + `*em*`/`**strong**`; the renderer converts |
| Advancing to a future/next-empty date because today's edition exists | Publishes a date whose games aren't out yet (off-by-one, reprise) | One run = today's date. If today already exists, it's published — stop |
