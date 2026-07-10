# The Morning Horsehide Herald — Design Spec

**Date:** 2026-07-10
**Status:** Approved design, ready for implementation planning
**Domain:** isitspringtraining.com (registered via dnsimple)

## Overview

A daily, automatically generated baseball digest — "The Morning Horsehide
Herald" — published each morning at isitspringtraining.com. A scheduled Claude
cloud agent runs the existing editorial "recipe" at 5:00 AM ET, writes the
edition as static HTML in a mock-heroic deadball-era voice, and publishes it by
committing to a GitHub repo that a static host auto-deploys.

The goal is to automate a workflow the user currently runs by hand (prompting an
agent with "morning dispatch") at minimal ongoing cost, while preserving the
editorial recipe exactly.

## Goals

- Publish a new edition automatically every morning at ~5:00 AM ET.
- Preserve the existing editorial recipe verbatim (voice, structure, sources of
  truth, consistency checks).
- Keep hosting cost at effectively $0 (static free tier) and generation cost
  covered by an existing Claude subscription.
- Maintain a browsable archive of every past edition (a "faithful daily
  chronicle").
- Handle the offseason and no-game days (including the All-Star break) with
  hot-stove coverage plus a countdown to spring training / Opening Day.
- Never serve a broken page: a failed run leaves the previous edition live.
- Make the account/subscription that runs the routine a single, documented point
  of change.

## Non-Goals

- No dynamic backend, database, or user accounts — the site is static HTML.
- No build step or framework — plain HTML + one CSS file.
- No comments, analytics, or interactivity beyond navigating editions.
- No reader-facing configuration; the recipe is the only editorial control
  surface.

## Architecture

```
  5:00 AM ET daily (cron)
       │
       ▼
┌─────────────────────────┐   reads    ┌──────────────────┐
│ Scheduled Claude agent  │◀───────────│ recipe.md         │
│ (cloud routine)         │            │ (editorial spec)  │
│                         │            └──────────────────┘
│ 1. Check prior day's slate (boxscore.email/mlb)
│ 2. Games? → full edition. No games? → hot-stove + countdown
│ 3. Write edition HTML in the Herald voice
│ 4. Update homepage (index.html) + archive index
│ 5. git commit && push
└───────────┬─────────────┘
            │ push
            ▼
┌─────────────────────────┐  auto-deploy  ┌──────────────────────┐
│ GitHub repo             │──────────────▶│ Cloudflare Pages      │
│ (editions + site source)│               │ (free static host)    │
└─────────────────────────┘               └──────────┬───────────┘
                                                      │ DNS (dnsimple)
                                                      ▼
                                           isitspringtraining.com
```

## Components

### 1. The recipe (`recipe.md`)

The editorial source of truth, stored in the repo. It is the user's existing
spec carried in verbatim, and it is the only file that needs editing to change
how the paper reads. The agent's daily prompt is short and simply instructs it
to read `recipe.md` and produce today's edition.

The recipe defines:

- **Trigger:** the "morning dispatch" cue (here, the scheduled run itself);
  pull the prior day's completed slate and run the edition.
- **Sources of truth:** boxscore.email/mlb is authoritative for scores, stats,
  standings, and leaderboards; when numbers/names conflict, the box score wins.
  ESPN and similar may be consulted for headline color and narrative detail
  after interesting events. Player names are cross-referenced against
  baseball-reference.com to confirm exact club affiliation before attribution.
  Internal consistency: a name/stat appearing in both the news section and a
  game summary must agree, with boxscore.email as tiebreaker.
- **Masthead** (flies on every edition):

  > ⚾ THE MORNING HORSEHIDE HERALD ⚾
  > *"Every Score Set Down, No Deed Unsung"*
  > ~ Being a Faithful Daily Chronicle of the National Pastime ~
  >
  > Volume/edition line, day and date, and a note on the number of contests
  > reported.

- **Structure:**
  1. ⭐ The Game of the Day — the single most interesting/impactful contest,
     with a thundering headline, mock-heroic subtitle, and a full paragraph;
     standings and leaderboard implications woven in.
  2. 📜 News Around the League — trades and rumors, injuries/roster moves,
     suspensions, All-Star and draft happenings, under small themed
     sub-headlines.
  3. 📋 The Rest of the Card — every remaining game, each with its own headline
     and a couple of sentences. No score goes unreported. Standings/leader
     sprinkles where they fit.
  4. A closing "word from the desk" flourish, then the ~ THE HERALD ~ sign-off.
- **Voice:** mock-heroic deadball-era purple prose — Grantland Rice by way of a
  slightly overwrought telegraph operator. Numbers spelled out in the old style
  ("five-and-sixty," "three-and-twentieth"), gods-and-heroes flourishes, but the
  facts underneath stay strictly accurate.

### 2. In-season vs. offseason logic

The agent determines the mode by checking whether the prior day's slate had
completed games:

- **Games played →** the full edition as specified above.
- **No games (offseason, or an in-season gap such as the All-Star break) →** the
  "hot stove" edition: offseason/roster news written in the same voice, plus a
  countdown to the next milestone (pitchers & catchers report → spring training →
  Opening Day). The masthead's "contests reported" note adapts accordingly
  (e.g., "no contests this day; the hot stove burns bright").

This logic lives in `recipe.md` so both modes stay in the editorial control
surface. It correctly covers the All-Star break as well as the winter offseason,
since both simply present as "no completed games yesterday."

### 3. Publishing & hosting

- The agent commits generated HTML to a GitHub repo.
- **Cloudflare Pages** (free tier) is connected to the repo and auto-deploys on
  every push. No build step — the site is static HTML, served as-is.
- **dnsimple** points the apex domain `isitspringtraining.com` at Cloudflare
  Pages via a CNAME/ALIAS record to the project's `.pages.dev` hostname
  (dnsimple supports ALIAS at the apex).
- GitHub Pages is a viable alternative (A/ALIAS records to GitHub's IPs); Pages
  is chosen for simpler apex handling and speed, but the design does not depend
  on the specific host.

**Self-healing failure mode:** because publishing is "commit on success only," a
failed or partial run produces no commit, so the previous edition stays live.
The site never shows a broken or half-written page.

### 4. Repo layout & routing

```
recipe.md                    ← editorial spec (edit this to change the paper)
assets/herald.css            ← shared deadball-era newspaper styling
templates/edition.html       ← masthead + page shell the agent fills in
index.html                   ← homepage: always the latest edition
archive.html                 ← index of all past editions, newest first
editions/YYYY/MM/DD.html      ← dated permalink for each edition
docs/superpowers/specs/       ← design specs (this file)
```

Routing:

- `/` (homepage) always shows today's edition.
- `/editions/YYYY/MM/DD.html` is the permanent link for a given day.
- `/archive.html` lists every edition, newest first.

Each morning the agent (a) writes the dated edition file, (b) updates
`index.html` to today's edition, and (c) prepends the new entry to
`archive.html`.

### 5. Look & feel

A single hand-tuned stylesheet (`assets/herald.css`) evoking an early-1900s
newspaper: cream/off-white stock, serif display headlines, column rules, and the
masthead flying on every edition. The exact visual treatment will be produced as
an approved mockup before going live. `templates/edition.html` holds the shared
page shell (masthead + structural sections) that the agent fills with each day's
content, so styling and structure stay consistent across editions.

### 6. Scheduling & account (single point of change)

- The daily run is a **scheduled Claude cloud agent (routine)** on a **cron of
  5:00 AM ET**, with correct handling of Eastern daylight/standard time.
- It runs against the user's **work Claude subscription** for now.
- **The account/subscription used is a documented single point of change.** The
  spec and repo will record exactly where the routine's owning account and
  GitHub credentials are configured, so switching to a personal subscription
  later is a config swap (re-create/transfer the routine under the new account
  and re-attach credentials), not a rebuild. Nothing about the account is
  hardcoded into the site or recipe.
- The routine has the GitHub repo attached and credentials (a fine-grained PAT
  with contents:read/write, or equivalent) available so it can commit and push.

## Error Handling

- **Run failure / source outage:** no commit → previous edition remains live.
- **Partial data (some sources down):** the recipe instructs the agent to prefer
  boxscore.email as authoritative and to proceed with what is verifiable rather
  than fabricate; consistency checks remain in force.
- **Run observability:** run status/logs are available through the scheduled-
  agent surface; a missing new commit on a given morning is the signal that a
  run failed.

## Verification

Content generation is not unit-testable in the usual sense; verification is:

1. **Pre-launch manual run:** trigger the agent once by hand, confirm the
   generated edition renders correctly and reads in the Herald voice.
2. **Publish path:** confirm the push deploys via Cloudflare Pages and the page
   is served at isitspringtraining.com (DNS resolves, TLS valid).
3. **Offseason/no-game path:** verify the hot-stove + countdown edition renders
   when the prior day had no games (testable immediately around the All-Star
   break).
4. **Ongoing editorial integrity:** the recipe's internal-consistency checks
   (boxscore.email tiebreaker, bbref affiliation cross-ref) run every edition.

## Cost

- **Hosting:** $0 (Cloudflare Pages free tier; domain already owned).
- **Generation:** covered by the existing Claude subscription; a single daily
  run is negligible against plan limits. If ever moved to metered API instead,
  approximately $15–60/month depending on model (Sonnet ~$15, Opus ~$60).

## Open Items (for implementation planning)

- Exact Cloudflare Pages ↔ GitHub connection steps and the dnsimple record
  values.
- The precise cron expression and timezone/DST configuration for 5:00 AM ET.
- Where and how the routine's owning account + GitHub credentials are recorded
  (the documented single point of change).
- Final visual design of `herald.css` (approved mockup).
- Initial `archive.html` / `index.html` bootstrap content before the first run.
