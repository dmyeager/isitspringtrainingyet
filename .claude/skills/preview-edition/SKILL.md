---
name: preview-edition
description: Use to preview/dry-run an edition of The Morning Horsehide Herald WITHOUT publishing — to see how a recipe/nicknames/instruction tweak renders against today's real slate. Triggers include "preview edition", "dry-run edition", "preview the paper", "test the recipe". This never writes to editions/ and never commits.
---

# Preview Edition — dry-run the Herald without publishing

## Overview

Generate **today's real edition** and render it to a throwaway, gitignored HTML
file you can open in a browser — **without** writing to `editions/`, regenerating
the site, or committing anything. This is the test rig for editorial tweaks:
change `recipe.md` or `nicknames.md`, run this against the same live sources a real
morning would see, and read the difference in the prose.

A preview is only useful as a stand-in for a publication morning if it runs the
**same live inputs** through the prompts. So this skill always composes from the
live sources — exactly as `morning-dispatch` does — and differs from it in one
respect only: **it never publishes.**

## The two rules that define this skill

1. **NEVER publish.** Do not create or modify anything under `editions/`, do not
   regenerate `index.html`/`archive.html`, do not `git add`/`commit`/`push`. Every
   artifact lives under the gitignored `preview/` directory. If you catch yourself
   about to write into `editions/`, stop — that is `morning-dispatch`, not this.
2. **NEVER invent the slate.** The games reported come from the live pre-flight
   sources below and nowhere else. Do **not** compose from a synthetic or sample
   slate, and do **not** infer the slate from yesterday's edition (see the Variety
   step — yesterday's edition is read for *voice variety only*, never to learn what
   was played). If a day had no games, that is a real, reportable fact (hot-stove
   mode) — discover it from the sources, don't assume it.

## Fetching sources — curl first

Fetch every source with **curl and a normal browser User-Agent**; this is the
default because the hosted `WebFetch` tool is regularly blocked (403) by these
sites. Only fall back to `WebFetch` if curl fails for a given URL. Example:

```
curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/120.0 Safari/537.36" "https://boxscore.email/mlb" -o box.html
```

Then strip tags to read the text. Do the fetches under `preview/` or the
scratchpad — never commit the raw HTML. Never fabricate; omit the unverifiable.

## Procedure

1. Read `recipe.md` (editorial truth) and `nicknames.md` (the epithet palette).
   The preview obeys `recipe.md` in full — this skill only overrides *where the
   output goes* (preview/, never published), not *how the edition is composed*.
2. **Run the recipe's full pre-flight source gate**, in order, before writing a
   word — same gate a real edition faces (see `recipe.md` → "Pre-flight"):
   1. **boxscore.email/mlb** (current edition, plain URL, no date) — the spine and
      source of truth for games played and their outcomes.
   2. **baseball-reference.com** homepage "Upcoming Schedule" — the forward ledger;
      fetch it **always**, even when you are certain nothing lies ahead. Every
      forward-looking word (including soft gestures like "resumes soon") must be
      checked against it or cut. Also the authority for player–team affiliation.
   3. **mlb.com/news** and **espn.com/mlb** "Top Headlines" — the wire desks for
      league news (trades, injuries, roster moves, milestones).
3. **Determine the mode from what the sources show** (not from assumption): prior
   day had completed games → `in_season`; no games → `hot_stove` with a countdown
   to the next milestone, its date taken from the b-ref Upcoming Schedule.
4. **Variety pass (voice only):** read the most recent existing edition under
   `editions/` (read-only) to avoid repeating its team epithets and its
   Game-of-the-Day opening gambit. This step informs *phrasing*, never the slate —
   the games always come from step 2's live sources.
5. Compose the edition as JSON conforming to `schema/edition.schema.json`, exactly
   as `recipe.md` directs. Set `meta.date` to **today** (the preview stands in for
   a publication morning). Write it **only** to `preview/edition.json` — NOT under
   `editions/`.
6. Render it: `python3 render.py --preview preview/edition.json preview/index.html`.
   On a validation error, fix the JSON and re-run until it exits 0 — the same
   schema gate a real edition faces.
7. Report to the user: the path `preview/index.html` to open, plus an inline echo
   of the Game-of-the-Day headline and the desk-note for an immediate read on the
   voice. Note anything a tweak visibly changed.

## Fail-safe

There is nothing to fail *safe* toward here because nothing is published: on any
error, simply report it. But never "recover" by writing into `editions/` or
committing — a broken preview is fine; a stray publish is not.
