# Updating BIOBUZZ for a new Team Update

The HTML here is the source of truth. The old `build.py` (in git history under
`biobuzz_src/`) is stale, so don't regenerate from it or you'll lose later fixes.

1. Get the TU PDF (FIRST also publishes a combined one). Render pages to images
   (`pdftoppm -r 80 -png TU.pdf pg`) and read them. **Yellow highlight = added,
   strikethrough = removed.** Plain `pdftotext` loses those marks.
2. Copy `tu/TU06.json` to `tu/TUxx.json`. Each edit is `{rule, old, new}`, an exact
   HTML snippet inside that rule's `<details>` block (copy it from the category page).
   `old` must match exactly once. Use the manual's own wording, not summaries.
3. `python3 tu_edit.py tu/TUxx.json`, then `python3 tu_edit.py --check`.
   The script edits the category page **and** `everything.html`, adds a TU badge,
   recomputes `data-search`, adds the entry to `updates.html`, and updates the home banner and dates.
4. Anything that isn't a rule card (the Violations/Integrity tables, sections this
   site doesn't cover) gets edited by hand. Still log the TU, using `"edits": []` if nothing on the site changed.
5. Spot-check in a browser (`python3 -m http.server`), then commit.
