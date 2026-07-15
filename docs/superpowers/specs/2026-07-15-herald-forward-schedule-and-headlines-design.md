# Herald Source Tweaks: Forward-Schedule Verification & League Headline Feeds

**Date:** 2026-07-15
**Status:** Approved

## Problem

The 2026-07-15 edition implied play resumes imminently ("one last morning of
the recess") without checking any schedule source. The claim happened to be
roughly right — baseball-reference shows a lone Mets @ Phillies game on
Thursday July 16, full slate Friday — but it was a guess. Guessing about
future scheduling will bite harder in the playoffs (irregular slates, travel
days) and the offseason. Separately, on no-game days the Herald's news well is
thin; the league's own headline feeds go unused.

## What changes

Docs-only edits to `recipe.md` (editorial spec) and
`.claude/skills/morning-dispatch/SKILL.md` (operational procedure). No schema,
renderer, or section changes — the paper's shape is untouched.

### 1. Forward-looking claims must be verified

- Add **baseball-reference.com's homepage "Upcoming Schedule" section** as the
  canonical source for the coming days' slate (dated matchups with game
  times). Its "Upcoming Dates" section covers milestones.
- New rule: any forward-looking claim — "games resume tomorrow," countdown
  framing, playoff/offseason scheduling — must be checked against it before it
  is written. If it can't be verified, write around it (the existing "omit
  rather than invent" rule is the fallback).
- b-ref 403s WebFetch; the skill notes the same curl-with-browser-UA fallback
  already prescribed for boxscore.email.
- b-ref's homepage widget shows matchups and times but **not probable
  pitchers**; note **mlb.com/probable-pitchers** as the supplement for
  pitching matchups (useful in the playoffs).

### 2. League headline feeds join the daily fetch

- **mlb.com/news** and **espn.com/mlb's "Top Headlines"** become named sources,
  skimmed **every morning** as candidate items for News Around the League.
- Hierarchy stays explicit: boxscore.email remains authoritative for scores,
  stats, and standings. The headline feeds supply league-wide news (trades,
  labor, milestones) and become the **primary news well** in hot-stove /
  no-game editions.
- Existing "never fabricate" and cross-reference rules apply to items sourced
  from them.

## Not changing

- No new recurring section (verification rule only — approved choice).
- No schema or renderer edits.

## Testing / rollout

Run the `preview-edition` dry run after the edits. If the preview reads better
than the published 2026-07-15 edition, regenerate today's edition with the new
sourcing and commit/push (explicitly authorized by the user for today).
