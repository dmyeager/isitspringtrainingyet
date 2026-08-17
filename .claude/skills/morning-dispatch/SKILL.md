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
2. Fetch boxscore.email/mlb's **current** edition (if WebFetch is blocked, `curl` with a normal browser User-Agent). Also skim the wire desks — **mlb.com/news** and **espn.com/mlb's "Top Headlines"** — for candidate News Around the League items (they never override boxscore.email on scores/stats). Cross-check team affiliations on baseball-reference.com. **Never fabricate**; omit anything unverifiable.
   - Per `recipe.md`'s **Pre-flight** gate, baseball-reference.com's homepage **"Upcoming Schedule"** is fetched on **every** run — including hot-stove and break mornings — *before* a word is written, not only when you expect to make a forward claim. b-ref 403s WebFetch — use `curl` with a browser User-Agent, same as boxscore.email. For probable pitchers, supplement with mlb.com/probable-pitchers.
   - **A forward-looking claim includes soft hedges.** "Resumes anon," "soon," "within days," "shortly," "before long" all count and are the easiest way to smuggle an unverified schedule through. Either name the b-ref-verified date/matchup or cut the forward reference — **never hedge around a schedule you haven't checked.**
3. **Variety pass.** Read the **three** most recent existing editions under
   `editions/` (read-only). Per `recipe.md`'s Variety section: hard rule against
   yesterday's edition (no reusing its team epithets or its Game-of-the-Day
   opening gambit); soft check against the two before it (avoid cycling
   distinctive coinages and repeating the same structural opener); consult
   `nicknames.md` for alternative handles. Use the same read for continuity —
   carry running storylines forward as continuations, referencing only coverage
   that actually appears in those editions. (The desk-note's fixed signature
   sign-off is exempt — keep it.)
4. **Credits.** Per `recipe.md`'s "The credits desk": start a running credits list now and finalize the `sources` array once the prose is composed — every page that contributed a printed fact, with `url`, `title`,
   `publication`, and `author` only where a byline is shown. Cite
   boxscore.email by its **dated permalink** (verify it resolves with `curl`);
   never cite the undated current-edition URL.
5. Build the edition per `schema/edition.schema.json`:
   - `meta.date` = **today** (US Eastern), `YYYY-MM-DD` — the *publication* date, NOT the game date. On a normal morning run this equals the dateline of boxscore.email's current edition; **never advance to a future date.** If `editions/YYYY/MM/DD.json` for today already exists, today's edition is already published — stop (don't overwrite or future-date unless the user explicitly asks to regenerate it).
   - `meta.weekday` + a flowery `meta.date_display` for today.
   - `meta.edition_number` = one greater than the highest existing `edition_number` under `editions/`.
   - Mode: games played → `in_season` (Game of the Day + News + **every** remaining game, no score unreported); none → `hot_stove` + a `countdown`.
   - Prose fields: plain text, `*italic*` / `**bold**` (markers hug the word), blank line between paragraphs, **no HTML**.
   - `sources` = the credits-desk list (see step 4). Omit only if genuinely
     nothing beyond the standard sources was used — an ordinary edition always
     has at least the boxscore entry.
6. Write it to `editions/YYYY/MM/DD.json` (today's date).
7. Render (from the repo root): `python3 render.py editions/YYYY/MM/DD.json`. On a validation error, fix the JSON and re-run until it exits 0.
8. (Optional) open `index.html` to eyeball it.
9. Commit the JSON + regenerated `index.html`, `archive.html`, and the edition page — `git commit -m "edition: YYYY-MM-DD"` — then `git push`. Pages redeploys in ~a minute.

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
| Reusing yesterday's epithets/opening gambit — or cycling a distinctive coinage on a two-day gap | Editions feel like a template; daily readers see the A-B-A rotation | Do the Variety pass: read the last **three** editions, vary handles (see `nicknames.md`), find a fresh way in |
| Guessing when play resumes / what's on tomorrow's card, or hedging with "resumes anon" / "within days" | Wrong forward-looking claims (e.g., implying games during the All-Star break); soft hedges dodge the check while still asserting a schedule | Fetch b-ref's homepage "Upcoming Schedule" (curl + browser UA) **every** run before writing; name the verified date/matchup or cut the forward reference |
| Citing `boxscore.email/mlb` (undated) in `sources` | Link shows a different edition tomorrow — dishonest citation | Cite the dated permalink for the edition actually used; verify it resolves |
| Inventing/guessing a byline for a source | Credits a person who didn't write it | Include `author` only when the page displays a byline; otherwise omit it |
