# BIOBUZZ condensed manual site

A lightweight, offline-friendly quick reference to the FTC BIOBUZZ Competition
Manual, built for use on phones/tablets at competitions with bad wifi.

## How it fits together

```
manual/
  competition_integrity_contract.txt   \  original pasted manual text —
  violation_definitions.txt            |  the actual source of truth.
  game_rules/*.txt                     /  edit THESE when a rule's wording changes.

  fragments/
    integrity.html                     hand-formatted HTML for the two files above
    violations.html                    (no rule IDs to parse generically, so these
                                        are written by hand instead of generated)

  data/
    updates.json                       Team Update changelog entries (see below)

  build.py                             reads everything above, writes site/*.html

  site/                                <- point GitHub Pages (or any static host) here
    index.html                         hand-authored landing page — edit directly
    style.css, search.js               hand-authored, shared across every page
    *.html (everything else)           GENERATED — don't hand-edit, re-run build.py
```

## Why generated, not hand-written

Last year's site duplicated every rule by hand between its own category page
and the single "everything" page, and the two drifted out of sync over the
season. This year, `build.py` parses the rule text straight out of the
original `.txt` files and generates every page (category pages, the
`everything.html` combined page, and each rule's penalty pills) from that one
parse — so a category page and `everything.html` can't disagree, because
they're built from the exact same data in the same run.

**If you edit a `.txt` rule file, or `data/updates.json`, re-run:**

```
python3 build.py
```

No dependencies — plain Python 3 standard library only.

## Adding a Team Update

FIRST periodically publishes Team Updates (TUs) that change rule text. To log
one, add an entry to `data/updates.json`:

```json
{
  "tu": "TU5",
  "date": "2026-10-04",
  "rule_ids": ["G303", "G417"],
  "summary": "G303.E cross-reference corrected from R101 to R402. G417 no longer assesses a foul per ARTIFACT — now a single MAJOR FOUL."
}
```

Then update the relevant `.txt` file(s) in `game_rules/` to match the new
wording, and re-run `build.py`. Each rule listed in `rule_ids` automatically
gets a small badge on its rule card linking back to the matching entry on
`updates.html`.

## Diagrams

Not included yet. The rule text itself already names the exact figures it
refers to (e.g. "Figure 12‑1: Expansion Limit – Top View" under R105) — each
is rendered as a placeholder note by `build.py`. When ready to add them,
`grep -h "Figure [0-9]" game_rules/*.txt *.txt` gives an exact, short list of
what to pull from the official HTML manual
(https://ftc-resources.firstinspires.org/ftc/game/cm-html) instead of fetching
the whole thing. Save images locally under `site/` and self-host them —
don't hotlink the FIRST site, since the whole point of this build is to keep
working with no connection at competitions.

## Design notes

- No service worker, no client-side routing — plain multi-page static HTML
  so the browser's normal back/forward button always just works.
- No CDN, no webfonts, no external requests at all — everything is
  self-hosted so it keeps working on bad venue wifi.
- Colour-blind-safe penalty pills: fouls stay in the blue family (never
  confused with the literal card colours), true yellow/red are reserved for
  cards, and every pill always carries a text label too — colour is never
  the only signal.
- Search (`search.js`) is a pure on-page filter over already-loaded content,
  not a fetch — works fully offline, no index file needed.
