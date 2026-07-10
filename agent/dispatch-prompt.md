It is the morning dispatch for The Morning Horsehide Herald.

Read `recipe.md` in this repository and follow it exactly to produce today's
edition (covering the prior day's slate). Concretely:

1. Gather the prior day's completed games and news from the sources of truth in
   the recipe (boxscore.email/mlb is authoritative; cross-check team
   affiliations on baseball-reference.com).
2. Decide the mode (in_season vs hot_stove) per the recipe.
3. Write the edition as JSON conforming to `schema/edition.schema.json` at
   `editions/YYYY/MM/DD.json` for the prior day's date.
4. Run `python3 render.py editions/YYYY/MM/DD.json`.
5. If the render reports a validation error, fix the JSON and re-run. Do not
   commit invalid output.
6. On success, `git add` the new JSON and the regenerated HTML
   (`index.html`, `archive.html`, and the edition page), commit with a message
   like "edition: YYYY-MM-DD", and push.
