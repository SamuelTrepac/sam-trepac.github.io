#!/usr/bin/env python3
"""
Generates the condensed BIOBUZZ manual site (site/*.html) directly from the
original pasted rule text (../*.txt, game_rules/*.txt) plus two hand-authored
HTML fragments (fragments/*.html) and the team-update log (data/updates.json).

Nothing here is hand-transcribed: every rule's wording, penalty text, and
structure is parsed straight out of the source .txt files at build time, so a
category page and everything.html can never drift out of sync with each other
the way last year's hand-duplicated pages did. Re-run this after editing a
source .txt file or data/updates.json:

    python3 build.py

Standard library only — no install step needed.
"""
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SITE = ROOT / "site"
FRAGMENTS = ROOT / "fragments"
DATA = ROOT / "data"

# ---------------------------------------------------------------- manifest --

CATEGORIES = [
    dict(src="game_rules/personal_safety.txt", slug="personal_safety", title="Personal Safety"),
    dict(src="game_rules/conduct.txt", slug="conduct", title="Conduct"),
    dict(src="game_rules/pre_match.txt", slug="pre_match", title="Pre-Match"),
    dict(src="game_rules/in_match.txt", slug="in_match", title="In-Match"),
    dict(src="game_rules/robot_construction_rules.txt", slug="robot_construction", title="Robot Construction"),
    dict(src="game_rules/fair_play_and_damage_prevention", slug="fair_play", title="Fair Play & Damage Prevention"),
    dict(src="game_rules/fabrication", slug="fabrication", title="Fabrication & COTS"),
    dict(src="game_rules/motors_and_actuators.txt", slug="motors_actuators", title="Motors & Actuators"),
    dict(src="game_rules/power_distribution.txt", slug="power_distribution", title="Power Distribution"),
    dict(src="game_rules/control_command_and_signals.txt", slug="control_signals", title="Control, Command & Signals"),
    dict(src="game_rules/pneumatics_and_airflow.txt", slug="pneumatics", title="Pneumatics & Airflow"),
    dict(src="game_rules/operator_console.txt", slug="operator_console", title="Operator Console"),
    dict(src="game_rules/robot_sign_rules.txt", slug="robot_sign", title="Robot Sign Rules"),
]

FRAGMENT_PAGES = [
    dict(slug="integrity", title="Competition Integrity Contract", fragment="integrity.html"),
    dict(slug="violations", title="Violations & Penalty Glossary", fragment="violations.html"),
]

LABELS = {
    "Verbal": "Verbal Warning",
    "Minor": "Minor Foul",
    "Major": "Major Foul",
    "Yellow": "Yellow Card",
    "Red": "Red Card",
    "Disabled": "Disabled",
    "Disqualified": "Disqualified",
}
SEVERITY_PATTERNS = [
    ("Red", r"\bRED CARD\b"),
    ("Yellow", r"\bYELLOW CARD\b"),
    ("Major", r"\bMAJOR FOUL\b"),
    ("Minor", r"\bMINOR FOUL\b"),
    ("Verbal", r"\bVERBAL WARNING\b"),
    ("Disabled", r"\bDISABLED\b"),
    ("Disqualified", r"\bDISQUALIFIED\b"),
    # "YELLOW or RED CARD" / "MAJOR or MINOR FOUL" style phrasing shares one noun
    # between the two severities, so the plain patterns above only catch the
    # second word. These catch the first word in each ordering.
    ("Yellow", r"\bYELLOW\s+or\s+RED\s+CARD\b"),
    ("Red", r"\bRED\s+or\s+YELLOW\s+CARD\b"),
    ("Major", r"\bMAJOR\s+or\s+MINOR\s+FOUL\b"),
    ("Minor", r"\bMINOR\s+or\s+MAJOR\s+FOUL\b"),
]

# ------------------------------------------------------------------- regex --

SECTION_HEADER_RE = re.compile(r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+([A-Z][A-Za-z0-9 /,&'\-]{1,60})$")
RULE_START_RE = re.compile(r"^([GR]\d{3,4})\s+(\*?)(.*)$")
LETTER_ITEM_RE = re.compile(r"^[A-Za-z]\.\s+\S")
ROMAN_ITEM_RE = re.compile(r"^[ivxlcdm]{1,4}\.\s+\S", re.IGNORECASE)
DASH_ITEM_RE = re.compile(r"^-\s+\S")
FIGURE_RE = re.compile(r"^Figure\s+\d+[‑\-]\d+:\s*(.*)$")
TABLE_RE = re.compile(r"^Table\s+\d+[‑\-]\d+:\s*(.*)$")
DIAGRAM_RE = re.compile(r"^Diagrams?\b")

esc = html.escape


def is_list_item(p):
    return bool(LETTER_ITEM_RE.match(p) or ROMAN_ITEM_RE.match(p) or DASH_ITEM_RE.match(p))


# ------------------------------------------------------------------- parse --

def find_severities(clause):
    hits = []
    for name, pat in SEVERITY_PATTERNS:
        m = re.search(pat, clause)
        if m:
            hits.append((m.start(), name))
    hits.sort()
    seen, ordered = set(), []
    for _, name in hits:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def parse_violation(paragraph):
    text = paragraph.strip()
    if text.startswith("Violation:"):
        text = text[len("Violation:"):].strip()
    clauses = re.split(r"(?<=\.)\s+(?=[A-Z])", text)
    out = []
    for c in clauses:
        c = c.strip()
        if not c:
            continue
        out.append({"text": c, "severities": find_severities(c)})
    return out


def build_blocks(paragraphs):
    blocks = []
    i, n = 0, len(paragraphs)
    while i < n:
        p = paragraphs[i]
        if FIGURE_RE.match(p):
            j = i + 1
            if j < n and DIAGRAM_RE.match(paragraphs[j]):
                j += 1
            blocks.append({"type": "figure", "caption": p})
            i = j
            continue
        if TABLE_RE.match(p):
            j = i + 1
            rows = []
            while (
                j < n
                and not is_list_item(paragraphs[j])
                and not FIGURE_RE.match(paragraphs[j])
                and not TABLE_RE.match(paragraphs[j])
                and len(paragraphs[j]) < 90
            ):
                rows.append(paragraphs[j])
                j += 1
            blocks.append({"type": "table", "caption": p, "rows": rows})
            i = j
            continue
        if is_list_item(p):
            items = []
            j = i
            while j < n and is_list_item(paragraphs[j]):
                items.append(paragraphs[j])
                j += 1
            blocks.append({"type": "list", "items": items})
            i = j
            continue
        blocks.append({"type": "p", "text": p})
        i += 1
    return blocks


def isolate_section_headers(raw):
    """Subsection headers like '11.4.2  TELEOP' are sometimes glued directly
    onto the previous or following line with no blank-line separator in the
    source text (an artifact of the original manual's layout). Force a blank
    line on both sides so the paragraph splitter treats them as their own
    paragraph instead of swallowing them into a rule's body text."""
    lines = raw.split("\n")
    out = []
    for line in lines:
        if SECTION_HEADER_RE.match(line.strip()):
            out.extend(["", line, ""])
        else:
            out.append(line)
    return "\n".join(out)


def parse_file(path):
    raw = isolate_section_headers(path.read_text(encoding="utf-8"))
    raw_blocks = re.split(r"\n\s*\n+", raw.strip())
    paragraphs = [" ".join(b.split()) for b in raw_blocks if b.strip()]

    intro = []
    section_number = None
    groups = []
    current_group = {"heading": None, "intro": [], "rules": []}
    current_rule = None
    current_rule_paragraphs = []
    current_violation_para = None

    def flush_rule():
        nonlocal current_rule, current_rule_paragraphs, current_violation_para
        if current_rule is None:
            return
        first = current_rule_paragraphs[0]
        m = re.match(r"^(.*?\.)(\s+(.*))?$", first, re.DOTALL)
        if m:
            title, rest = m.group(1).strip(), (m.group(3) or "").strip()
        else:
            title, rest = first, ""
        body_paragraphs = ([rest] if rest else []) + current_rule_paragraphs[1:]
        current_group["rules"].append({
            "id": current_rule["id"],
            "flagged": current_rule["flagged"],
            "title": title,
            "blocks": build_blocks(body_paragraphs),
            "violation": parse_violation(current_violation_para) if current_violation_para else [],
        })
        current_rule = None
        current_rule_paragraphs = []
        current_violation_para = None

    for p in paragraphs:
        sm = SECTION_HEADER_RE.match(p)
        rm = RULE_START_RE.match(p)
        if sm and not rm:
            flush_rule()
            if current_group["rules"] or current_group["heading"]:
                groups.append(current_group)
            current_group = {"heading": sm.group(2).strip(), "intro": [], "rules": []}
            if section_number is None:
                section_number = sm.group(1)
            continue
        if rm:
            flush_rule()
            current_rule = {"id": rm.group(1), "flagged": bool(rm.group(2))}
            current_rule_paragraphs = [rm.group(3).strip()]
            continue
        if p.startswith("Violation:"):
            current_violation_para = p
            continue
        if current_rule is not None:
            current_rule_paragraphs.append(p)
        elif current_group["heading"] is not None:
            current_group["intro"].append(p)
        else:
            intro.append(p)
    flush_rule()
    if current_group["rules"] or current_group["heading"]:
        groups.append(current_group)
    return {"intro": intro, "section_number": section_number, "groups": groups}


def rule_id_prefix_range(groups):
    prefixes = sorted({r["id"][0] + r["id"][1] for g in groups for r in g["rules"]})
    if not prefixes:
        return ""
    return prefixes[0] + "xx" if len(prefixes) == 1 else f"{prefixes[0]}xx–{prefixes[-1]}xx"


def block_plaintext(blocks):
    parts = []
    for b in blocks:
        if b["type"] == "p":
            parts.append(b["text"])
        elif b["type"] == "list":
            parts.extend(b["items"])
        elif b["type"] == "table":
            parts.append(b["caption"])
            parts.extend(b["rows"])
        elif b["type"] == "figure":
            parts.append(b["caption"])
    return " ".join(parts)


# ------------------------------------------------------------------ render --

def render_block(b):
    if b["type"] == "p":
        return f"<p>{esc(b['text'])}</p>"
    if b["type"] == "list":
        items = "".join(f"<li>{esc(it)}</li>" for it in b["items"])
        return f'<ul class="rule-list">{items}</ul>'
    if b["type"] == "table":
        cap = f'<div class="table-caption">{esc(b["caption"])}</div>'
        if b["rows"]:
            items = "".join(f"<li>{esc(r)}</li>" for r in b["rows"])
            cap += f'<ul class="compact-list">{items}</ul>'
        return cap
    if b["type"] == "figure":
        return f'<p class="figure-note">\U0001f5bc {esc(b["caption"])} — diagram not yet included in this condensed site.</p>'
    return ""


def render_rule(rule, tu_by_rule):
    body_html = "".join(render_block(b) for b in rule["blocks"])

    violation_html = ""
    if rule["violation"]:
        rows = []
        for clause in rule["violation"]:
            pills = "".join(f'<span class="pill {s}">{LABELS[s]}</span>' for s in clause["severities"])
            pills_html = f'<span class="pills">{pills}</span>' if pills else ""
            rows.append(f'<div class="violation-clause">{pills_html}{esc(clause["text"])}</div>')
        violation_html = f'<div class="violation">{"".join(rows)}</div>'
    elif rule["id"].startswith("R"):
        violation_html = (
            '<div class="violation"><div class="violation-clause" '
            'style="color:var(--text-dim);font-style:italic;">'
            "No standalone penalty text for this rule — non-compliance is "
            "typically addressed at inspection.</div></div>"
        )

    tu_badges = "".join(
        f' <a class="tu-badge" href="updates.html#{esc(u["tu"])}">{esc(u["tu"])}</a>'
        for u in tu_by_rule.get(rule["id"], [])
    )
    flag = ' <span class="flag" title="Flagged rule in the official manual">★</span>' if rule["flagged"] else ""

    search_text = esc(" ".join([
        rule["id"], rule["title"], block_plaintext(rule["blocks"]),
        " ".join(c["text"] for c in rule["violation"]),
    ]).lower())

    return (
        f'<details class="rule" id="{rule["id"]}" data-search="{search_text}">'
        f'<summary><span class="rule-id">{rule["id"]}</span>{flag} {esc(rule["title"])}{tu_badges}</summary>'
        f'<div class="rule-body">{body_html}{violation_html}</div>'
        f"</details>"
    )


def render_groups(parsed, tu_by_rule):
    out = []
    for b in build_blocks(parsed["intro"]):
        out.append(render_block(b))
    multi = len(parsed["groups"]) > 1
    for g in parsed["groups"]:
        gid = re.sub(r"[^a-z0-9]+", "-", (g["heading"] or "").lower()).strip("-")
        out.append(f'<section data-group{f" id=\"{gid}\"" if gid else ""}>')
        if multi and g["heading"]:
            out.append(f"<h2>{esc(g['heading'])}</h2>")
        for b in build_blocks(g["intro"]):
            out.append(render_block(b))
        for rule in g["rules"]:
            out.append(render_rule(rule, tu_by_rule))
        out.append("</section>")
    return "".join(out)


NAV = [("index.html", "Home"), ("everything.html", "Everything"), ("updates.html", "Team Updates")]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} – BIOBUZZ Manual</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="topbar"><div class="bar">
<a class="site-name" href="index.html">BIOBUZZ Condensed Manual</a>
<nav>{nav}</nav>
</div></header>
<main class="wrap">
{body}
<p class="disclaimer">This is a condensed, unofficial reference to help find rules quickly. Official rules always come from the current FTC BIOBUZZ Competition Manual — this site is not a substitute for it. Generated {date}.</p>
</main>
</body>
</html>
"""


def nav_html(active):
    return "".join(
        f'<a href="{href}"{" class=\"current\"" if href == active else ""}>{label}</a>'
        for href, label in NAV
    )


def page(active_href, title, body):
    return PAGE.format(title=esc(title), nav=nav_html(active_href), body=body, date=date.today().isoformat())


def search_box():
    return (
        '<input id="rule-search" class="search-box" type="search" '
        'placeholder="Search rule number or keyword…" autocomplete="off">'
        '<p class="search-count" id="search-count"></p>'
    )


# -------------------------------------------------------------------- main --

def main():
    SITE.mkdir(exist_ok=True)

    updates = json.loads((DATA / "updates.json").read_text(encoding="utf-8")) if (DATA / "updates.json").exists() else []
    tu_by_rule = {}
    for u in updates:
        for rid in u.get("rule_ids", []):
            tu_by_rule.setdefault(rid, []).append(u)

    parsed_categories = []
    for cat in CATEGORIES:
        parsed = parse_file(ROOT / cat["src"])
        parsed_categories.append((cat, parsed))

    # per-category pages
    everything_sections = []
    for cat, parsed in parsed_categories:
        if parsed["section_number"]:
            ref = ".".join(parsed["section_number"].split(".")[:2])  # drop sub-subsection, e.g. 11.4.1 -> 11.4
        else:
            ref = rule_id_prefix_range(parsed["groups"])
        ref_html = f'<p class="manual-ref">Manual Section {esc(ref)}</p>' if ref else ""
        body = f"<h1>{esc(cat['title'])}</h1>{ref_html}{search_box()}{render_groups(parsed, tu_by_rule)}"
        (SITE / f"{cat['slug']}.html").write_text(
            page(f"{cat['slug']}.html", cat["title"], body), encoding="utf-8"
        )
        everything_sections.append(f"<h2 id=\"{cat['slug']}\">{esc(cat['title'])}</h2>{ref_html}{render_groups(parsed, tu_by_rule)}")

    # search.js needs to be included on pages that have the search box; re-write with script tag included
    for cat in CATEGORIES:
        p = SITE / f"{cat['slug']}.html"
        text = p.read_text(encoding="utf-8")
        text = text.replace("</body>", '<script src="search.js"></script>\n</body>')
        p.write_text(text, encoding="utf-8")

    # fragment pages (Integrity, Violations)
    for frag in FRAGMENT_PAGES:
        frag_html = (FRAGMENTS / frag["fragment"]).read_text(encoding="utf-8")
        body = f"<h1>{esc(frag['title'])}</h1>{frag_html}"
        (SITE / f"{frag['slug']}.html").write_text(page(f"{frag['slug']}.html", frag["title"], body), encoding="utf-8")
        everything_sections.append(f"<h2 id=\"{frag['slug']}\">{esc(frag['title'])}</h2>{frag_html}")

    # everything.html
    everything_body = (
        f"<h1>Everything</h1>"
        f'<p class="manual-ref">Every rule on this site, on one page — generated from the same source as the category pages, so it can’t drift out of sync with them. Fully self-contained: once this page has loaded, it works with zero connection.</p>'
        + search_box()
        + "".join(everything_sections)
    )
    (SITE / "everything.html").write_text(
        page("everything.html", "Everything", everything_body).replace("</body>", '<script src="search.js"></script>\n</body>'),
        encoding="utf-8",
    )

    # updates.html
    cat_by_rule_prefix = {}
    for cat, parsed in parsed_categories:
        for g in parsed["groups"]:
            for r in g["rules"]:
                cat_by_rule_prefix[r["id"]] = cat["slug"]

    if updates:
        cards = []
        for u in sorted(updates, key=lambda x: x.get("date", ""), reverse=True):
            links = "".join(
                f' <a class="tu-badge" href="{cat_by_rule_prefix.get(rid, "everything")}.html#{esc(rid)}">{esc(rid)}</a>'
                for rid in u.get("rule_ids", [])
            )
            cards.append(
                f'<section class="banner" id="{esc(u["tu"])}"><strong>{esc(u["tu"])}</strong> '
                f'— {esc(u.get("date", ""))}<br>{esc(u.get("summary", ""))}<br>{links}</section>'
            )
        updates_body = f"<h1>Team Updates</h1>" + "".join(cards)
    else:
        updates_body = (
            "<h1>Team Updates</h1>"
            '<p>No Team Updates logged yet this season. As FIRST publishes each Team Update, add an entry to '
            '<code>data/updates.json</code> (tu, date, rule_ids, summary) and re-run <code>build.py</code> — '
            "affected rules will automatically get a badge linking back here.</p>"
        )
    (SITE / "updates.html").write_text(page("updates.html", "Team Updates", updates_body), encoding="utf-8")

    print(f"Built {len(CATEGORIES)} category pages + everything.html + updates.html + {len(FRAGMENT_PAGES)} fragment pages into {SITE}")


if __name__ == "__main__":
    main()
