# Design: Day-to-Day Variety for The Morning Horsehide Herald

**Date:** 2026-07-11
**Status:** Approved (design), pending implementation plan

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

- No change to `render.py`, the schema, or the site.
- No rolling "recently-used" ledger file or multi-day look-back (considered and
  rejected as over-built for the need — see Decisions).
- No change to the masthead, structure, or mode logic.

## Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Nickname bank strictness | **Curated bank + explicit license to coin.** A static list alone would *reduce* variety (agent cycles the same 2 handles); the bank is a *palette to draw from and depart from*, plus an authenticity anchor so coined epithets stay period-true. |
| Look-back depth | **Just yesterday, descriptors only.** Read only the most recent existing edition. Cheapest; catches the jarring day-to-day echoes. |
| Desk-note sign-off | **Canonize as a fixed signature.** The closing sentence "…keep your scorecards near and your enthusiasms nearer." is already the de facto closer on every edition; make it an intentional fixed signature (like the masthead motto), NOT something to vary. |

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

## How the pieces fit

```
morning-dispatch SKILL.md ──▶ recipe.md ──▶ nicknames.md
        │                        │
        │  "read most recent     │  Variety subsection:
        │   edition for variety" │  - palette philosophy
        ▼                        │  - avoid yesterday's epithets + GotD gambit
  agent reads editions/…latest   │  - canonized sign-off
        │                        ▼
        └────────────▶ writes today's edition JSON (fresher, on-voice)
```

## Risks & mitigations

- **Bank becomes a crutch → *less* variety.** Mitigated by framing (§1 preamble)
  as a palette to depart from, plus the "don't repeat yesterday" rule.
- **Fabricated nicknames.** Mitigated by curating real/period-plausible handles
  during implementation; the recipe's "never fabricate" rule still governs.
- **Over-correction into awkward prose.** Mitigated by the "light touch" framing
  in §2.
- **Token cost of reading yesterday.** One JSON file; negligible.

## Testing / acceptance

- `nicknames.md` exists, covers all 30 clubs, handles are real/period-plausible.
- `recipe.md` Variety subsection + canonized sign-off present and internally
  consistent with existing sections.
- `SKILL.md` has the read-yesterday step.
- Sanity dry-run: regenerate a sample edition mentally/by hand against the new
  instructions to confirm nothing contradicts the schema or existing rules.
- No changes to `render.py`/schema; existing editions still render unchanged.
