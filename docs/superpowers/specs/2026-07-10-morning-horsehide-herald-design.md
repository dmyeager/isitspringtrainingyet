# The Morning Horsehide Herald — Design Spec

**Date:** 2026-07-10
**Status:** Approved design, ready for implementation planning
**Domain:** isitspringtrainingyet.com (registered via dnsimple)

## Overview

A daily, automatically generated baseball digest — "The Morning Horsehide
Herald" — published each morning at isitspringtrainingyet.com. A scheduled
Claude cloud agent runs the existing editorial "recipe" at 6:00 AM ET, writes
the edition as **structured content (data)** in a mock-heroic deadball-era
voice, renders that data to static HTML via a small deterministic renderer, and
publishes by committing to a GitHub repo that a static host auto-deploys.

The goal is to automate a workflow the user currently runs by hand (prompting an
agent with "morning dispatch") at minimal ongoing cost, while preserving the
editorial recipe exactly and keeping content cleanly separated from
presentation.

## Goals

- Publish a new edition automatically every morning at ~6:00 AM ET.
- Preserve the existing editorial recipe verbatim (voice, structure, sources of
  truth, consistency checks).
- **Separate content from presentation:** the agent emits edition *data*; a
  renderer produces *HTML* from that data plus a shared template and one
  stylesheet. The agent never writes markup or CSS.
- Keep an archive that can be **re-rendered wholesale** after any design change,
  so every past edition stays visually consistent.
- Keep hosting cost at effectively $0 (static free tier) and generation cost
  covered by an existing Claude subscription.
- Handle the offseason and no-game days (including the All-Star break) with
  hot-stove coverage plus a countdown to spring training / Opening Day.
- Never serve a broken page: a failed or malformed run leaves the previous
  edition live.
- Make the Claude subscription that runs the routine a single, documented point
  of change.

## Non-Goals

- No dynamic backend, database, or user accounts — the site is static HTML.
- No host-side build step and no web framework — a small zero-dependency
  renderer runs at generation time (inside the agent's run); the host serves the
  committed static HTML + one CSS file as-is.
- No comments, analytics, or interactivity beyond navigating editions.
- No reader-facing configuration; the recipe is the only editorial control
  surface.

## Architecture

```
  6:00 AM ET daily (cron)
       │
       ▼
┌─────────────────────────┐   reads    ┌──────────────────┐
│ Scheduled Claude agent  │◀───────────│ recipe.md         │
│ (cloud routine)         │            │ (editorial spec)  │
│                         │            └──────────────────┘
│ 1. Check prior day's slate (boxscore.email/mlb)
│ 2. Games? → full edition. No games? → hot-stove + countdown
│ 3. Write edition as structured data (JSON) in the Herald voice
│ 4. Run renderer → edition HTML + regenerated homepage + archive
│ 5. git commit (data + HTML) && push
└───────────┬─────────────┘
            │ push
            ▼
┌─────────────────────────┐  auto-deploy  ┌──────────────────────┐
│ GitHub repo (dmyeager)  │──────────────▶│ GitHub Pages          │
│ (recipe, renderer,      │               │ (free static host)    │
│  edition data + HTML)   │               │                       │
└─────────────────────────┘               └──────────┬───────────┘
                                                      │ DNS (dnsimple)
                                                      ▼
                                           isitspringtrainingyet.com
```

## Components

### 1. The recipe (`recipe.md`)

The editorial source of truth, stored in the repo. It is the user's existing
spec carried in verbatim, and it is the only file that needs editing to change
how the paper reads. The agent's daily prompt is short and simply instructs it
to read `recipe.md` and produce today's edition **as structured data** (see §3),
not as HTML.

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

The recipe also tells the agent how the structure above maps onto the edition
data schema in §3, so the editorial spec and the machine contract stay aligned.

### 2. In-season vs. offseason logic

The agent determines the mode by checking whether the prior day's slate had
completed games:

- **Games played →** `mode: "in_season"`, the full edition as specified above.
- **No games (offseason, or an in-season gap such as the All-Star break) →**
  `mode: "hot_stove"`: offseason/roster news written in the same voice, plus a
  countdown to the next milestone (pitchers & catchers report → spring training
  → Opening Day). The masthead's "contests reported" note adapts accordingly.

This logic lives in `recipe.md` so both modes stay in the editorial control
surface. It covers the All-Star break as well as the winter offseason, since
both simply present as "no completed games yesterday."

### 3. Content schema & renderer

This is the content/presentation boundary. The agent produces content *data*; a
renderer produces *HTML*. Markup and CSS class names exist **only** in the
template and stylesheet — never in the agent's output.

**Edition data — `editions/YYYY/MM/DD.json`**, conforming to a documented schema
(`schema/edition.schema.json`):

- `meta`: `{ date, weekday, volume, edition_number, mode, contests_reported }`
  where `mode` is `"in_season"` or `"hot_stove"`.
- `game_of_the_day`: `{ headline, subtitle, body }` (null in `hot_stove` mode).
- `news`: `[ { subhead, body } ]` — themed News-Around-the-League subsections.
- `rest_of_the_card`: `[ { headline, body } ]` — every remaining game (empty in
  `hot_stove` mode).
- `countdown`: `{ milestone, target_date, days_remaining }` (present in
  `hot_stove` mode).
- `desk_note`: the closing "word from the desk" flourish.

Prose fields hold plain text with a small inline-emphasis convention (Markdown
`*em*` / `**strong**`) that the renderer converts; the agent writes no HTML.

**Renderer — `render.*`**, a small zero-dependency script, deterministic:
`render(editionData) → HTML`, using `templates/edition.html` +
`assets/herald.css`. It:

- Validates the data against `schema/edition.schema.json` and **fails loudly**
  on any violation (no HTML produced, no commit).
- Emits the per-edition page `editions/YYYY/MM/DD.html`.
- Regenerates `index.html` (homepage = most recent edition).
- Regenerates `archive.html` (a derived view over all edition data files,
  newest first).
- Applies the inline-emphasis convention and escapes prose so content can never
  break the markup.

**Rendering runs at generation time**, inside the agent's session: the agent
writes the JSON, runs the renderer, and commits **both** the data and the
rendered HTML. The host therefore needs no build step and serves committed HTML
as-is. A redesign (editing `herald.css` or the template) is applied to the whole
archive by running the renderer over every edition's JSON once
(`render --all`) — because content is stored as data, every past page updates
consistently.

### 4. Publishing & hosting

- The agent commits generated files to a GitHub repo. The repo lives under the
  user's **personal `dmyeager` GitHub account** — independent of the Claude
  subscription that runs the routine (see Scheduling & account below).
  Publishing (GitHub + static host + dnsimple) is entirely on personal accounts;
  only the agent-execution subscription is currently the work account.
- **GitHub Pages** (free) serves the repo and redeploys on every push. No build
  step — the committed HTML is served as-is. A `.nojekyll` file disables Jekyll
  so the static files are published untouched. Pages lives on the same personal
  `dmyeager` account as the repo, so no third service is involved.
- **dnsimple** points the apex domain `isitspringtrainingyet.com` at GitHub
  Pages via ALIAS/A records (to GitHub's Pages IPs), with the custom domain set
  in the repo's Pages settings; HTTPS is provisioned automatically.

**Self-healing failure mode:** publishing is "commit on success only." A failed
run, a source outage, or edition data that fails schema validation produces no
commit, so the previous edition stays live. The site never shows a broken or
half-written page.

### 5. Repo layout & routing

```
recipe.md                     ← editorial spec (edit this to change the paper)
schema/edition.schema.json    ← the edition data contract
render.*                      ← deterministic renderer (zero dependencies)
templates/edition.html        ← masthead + page shell
assets/herald.css             ← shared deadball-era newspaper styling
index.html                    ← homepage: latest edition   (GENERATED)
archive.html                  ← archive index, newest first (GENERATED)
editions/YYYY/MM/DD.json       ← edition content, agent-authored (SOURCE OF TRUTH)
editions/YYYY/MM/DD.html       ← rendered edition            (GENERATED)
docs/superpowers/specs/        ← design specs (this file)
```

Routing:

- `/` (homepage) always shows today's edition.
- `/editions/YYYY/MM/DD.html` is the permanent link for a given day.
- `/archive.html` lists every edition, newest first.

`index.html`, `archive.html`, and each `editions/**/*.html` are renderer output;
the `editions/**/*.json` files are the authored source of truth. A rebuild
(`render --all`) can regenerate all HTML from the JSON at any time.

### 6. Look & feel

A single hand-tuned stylesheet (`assets/herald.css`) evoking an early-1900s
newspaper: cream/off-white stock, serif display headlines, column rules, and the
masthead flying on every edition. `templates/edition.html` holds the shared page
shell (masthead + section scaffolding) that the renderer fills with each day's
data. Because all markup and classes live here — never in the agent's output — a
single design change re-renders across the whole archive (`render --all`). The
exact visual treatment will be produced as an approved mockup before going live.

### 7. Scheduling & account (single point of change)

- The daily run is a **scheduled Claude cloud agent (routine)** on a **cron of
  6:00 AM ET**, with correct handling of Eastern daylight/standard time. 6 AM
  is chosen because boxscore.email publishes its morning edition well before
  then, so the routine's fetch of the current edition always has the prior day's
  completed slate.
- It runs against the user's **work Claude subscription** for now. This is
  distinct from the publishing side: the **GitHub repo, static host, and
  dnsimple domain are all on the user's personal accounts** (GitHub =
  `dmyeager`). Only the Claude subscription that executes the routine is
  currently the work account.
- **The Claude subscription used to run the routine is a documented single point
  of change.** The spec and repo will record exactly where the routine's owning
  Claude account is configured, so switching it to a personal subscription later
  is a config swap (re-create/transfer the routine under the new account and
  re-attach the same personal GitHub credentials), not a rebuild. Nothing about
  the account is hardcoded into the site, recipe, or renderer.
- The routine authenticates to the personal `dmyeager` GitHub repo with a
  fine-grained PAT (contents:read/write) or equivalent so it can commit and
  push — this credential is independent of which Claude subscription runs the
  routine.

## Error Handling

- **Run failure / source outage:** no commit → previous edition remains live.
- **Malformed edition data:** the renderer's schema validation fails the run
  before any HTML is written → no commit → previous edition remains live.
- **Partial data (some sources down):** the recipe instructs the agent to prefer
  boxscore.email as authoritative and to proceed with what is verifiable rather
  than fabricate; consistency checks remain in force.
- **Run observability:** run status/logs are available through the scheduled-
  agent surface; a missing new commit on a given morning is the signal that a
  run failed.

## Verification

Content generation is not unit-testable in the usual sense; verification is:

1. **Renderer tests:** the renderer is deterministic and pure, so it is
   unit-testable directly — feed sample edition JSON (in-season and hot-stove
   fixtures), assert the produced HTML and the schema-validation failure path.
2. **Pre-launch manual run:** trigger the agent once by hand, confirm the
   generated edition renders correctly and reads in the Herald voice.
3. **Publish path:** confirm the push deploys and the page is served at
   isitspringtrainingyet.com (DNS resolves, TLS valid).
4. **Offseason/no-game path:** verify the hot-stove + countdown edition renders
   when the prior day had no games (testable immediately around the All-Star
   break).
5. **Ongoing editorial integrity:** the recipe's internal-consistency checks
   (boxscore.email tiebreaker, bbref affiliation cross-ref) run every edition.

## Cost

- **Hosting:** $0 (static host free tier; domain already owned).
- **Generation:** covered by the existing Claude subscription; a single daily
  run is negligible against plan limits. If ever moved to metered API instead,
  approximately $15–60/month depending on model (Sonnet ~$15, Opus ~$60).

## Open Items (for implementation planning)

- Exact GitHub Pages setup steps (custom domain in Pages settings, `.nojekyll`)
  and the specific dnsimple ALIAS/A record values for the apex domain.
- The renderer's implementation language (a zero-dependency script; candidate:
  Python stdlib or Node with no external packages) and the inline-emphasis
  convention it supports.
- The precise cron expression and timezone/DST configuration for 6:00 AM ET.
- Where and how the routine's owning Claude account is recorded (the documented
  single point of change) and where the personal `dmyeager` GitHub PAT is stored
  for the routine to use.
- Final visual design of `herald.css` (approved mockup).
- Bootstrap content for `index.html` / `archive.html` before the first run.
