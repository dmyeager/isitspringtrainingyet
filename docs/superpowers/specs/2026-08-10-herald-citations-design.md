# The Herald Acknowledges Its Debts — Citations Design

**Date:** 2026-08-10
**Status:** Approved

## Purpose

Every edition of The Morning Horsehide Herald is written from a small set of
web sources. Give credit where it is due: each edition ends with a citations
section linking every source that contributed facts to that edition, with
author names where the source shows a byline.

## Scope decisions (made with the user)

- **Contributing sources only.** List each URL whose content actually informed
  the printed edition — a story, a score, a schedule check that produced a
  printed claim. Not an audit trail of every fetch: pre-flight checks that
  yielded nothing printed are omitted.
- **One flat list at the bottom.** A single section after the desk note, not
  per-story footnotes.
- **In-voice heading, plain entries.** Heading: "The Herald Acknowledges Its
  Debts". Entries are a clean, scannable list of linked titles with authors and
  publications — no flowery prose in the entries themselves.
- **No backfill.** Past editions' source lists were not recorded and cannot be
  honestly reconstructed. The field is optional; the 33 existing editions
  remain valid and render unchanged.

## Schema change (`schema/edition.schema.json`)

Add an **optional** top-level `sources` property:

```json
"sources": {
  "type": ["array", "null"],
  "items": {
    "type": "object",
    "required": ["url", "title", "publication"],
    "properties": {
      "url": { "type": "string" },
      "title": { "type": "string" },
      "publication": { "type": "string" },
      "author": { "type": "string" }
    }
  }
}
```

- `url` — the page cited, as fetched (see the boxscore.email permalink rule).
- `title` — the article/page title, or a sensible descriptive title for pages
  without one (e.g. "Morning digest for the games of August 9").
- `publication` — e.g. "MLB.com", "ESPN", "Boxscore", "Baseball-Reference".
- `author` — byline name(s), **only when the page displays one**. Never
  invented; omitted otherwise. Multiple authors joined naturally
  ("A. Writer and B. Scribe").

`sources` is NOT added to the schema's `required` list.

## Rendering (`render.py`)

After the desk-note section (following the `~ THE HERALD ~` signoff), when
`sources` is present and non-empty, emit:

```html
<section class="sources">
  <h2 class="section__label">The Herald Acknowledges Its Debts</h2>
  <ul class="sources__list">
    <li class="sources__item">
      Author Name, <a href="URL" rel="noopener">Title</a> &mdash; Publication
    </li>
    ...
  </ul>
</section>
```

- The `Author Name, ` prefix appears only when `author` is present.
- `url` is attribute-escaped (`html.escape(..., quote=True)`); title, author,
  and publication go through `render_inline` like other prose (escaped;
  `*em*`/`**strong**` supported but not expected).
- Editions without `sources` (or with an empty list / null) render exactly as
  today — no section, no heading.
- The homepage (`index.html`) mirrors the latest edition via `render_edition`,
  so it inherits the section automatically. The archive page is unchanged.

## Styling (`assets/herald.css`)

A small addition: the `.sources` block reads as a colophon — smaller type than
body prose, consistent with the sheet's look, links styled like existing links.
No layout changes elsewhere.

## The boxscore.email permalink rule

The dispatch always **fetches** the undated current edition
(`boxscore.email/mlb`) — that rule is unchanged. But that URL shows a
different edition tomorrow, so it is a dishonest permanent citation. When
citing it, the dispatch uses the **dated permalink** for the edition it
actually used, after verifying the permalink resolves (e.g. with a `curl`
status check). If no working permalink can be found, fall back to citing
`https://boxscore.email/mlb` with the edition's dateline in the title so the
reader knows which edition was meant.

## Process changes

- **`recipe.md`** — new short "Credits desk" section: while writing, record
  every source that contributes a printed fact (url, title, publication,
  byline if shown); the definition of "contributing" is that a fact from it
  appears in print; the boxscore permalink rule; never invent a byline.
- **`.claude/skills/morning-dispatch/SKILL.md`** — add the step to the
  procedure (compile `sources` before writing the JSON) and two rows to the
  common-mistakes table: citing the undated boxscore URL, and inventing or
  guessing bylines.
- **`.claude/skills/preview-edition`** — no changes; it inherits the renderer.
  Verify a preview with `sources` renders correctly during implementation.

## Testing (`tests/test_render.py`)

- Renderer: edition **with** `sources` produces the section with correctly
  escaped links, author-prefixed and authorless entries formatted right.
- Renderer: edition **without** `sources` (absent, null, and empty-list)
  produces no `.sources` section.
- Schema: a well-formed `sources` entry validates; an entry missing `url`
  (or `title`/`publication`) fails validation.
- Regression: all existing editions under `editions/` still validate and
  render (`render.py --all` exits 0).

## Out of scope

- Backfilling citations onto past editions.
- Per-story footnotes or inline citation markers.
- Any change to which sources the dispatch consults or how it verifies facts.
