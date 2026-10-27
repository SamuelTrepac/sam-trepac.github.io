#!/usr/bin/env python3
"""Apply a Team Update's rule-text changes to the built site. See README.md.

    python3 tu_edit.py tu/TU06.json          # apply
    python3 tu_edit.py --check               # verify every data-search attr is in sync

Each rule exists twice (its category page + everything.html); every edit is
applied to both, the rule gets a TU badge, and its data-search is recomputed.
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

SITE = Path(__file__).resolve().parent
RULE_RE = r'<details class="rule" id="{id}" data-search="[^"]*">.*?</details>'


def search_text(block):
    inner = re.sub(r'^<details[^>]*>', "", block)
    inner = re.sub(r'<span class="pills">.*?</span></span>', "", inner)
    inner = re.sub(r'<a class="tu-badge"[^>]*>.*?</a>', "", inner)
    inner = re.sub(r'<span class="flag"[^>]*>.*?</span>', "", inner)
    text = html.unescape(re.sub(r"<[^>]+>", " ", inner))
    text = " ".join(text.split())
    if 'class="violation"' not in block:
        text += " "  # matches the original build.py, which joined an empty violation part
    return html.escape(text.lower(), quote=True)


def resync(block):
    return re.sub(r'data-search="[^"]*"', lambda _: f'data-search="{search_text(block)}"', block, count=1)


def pages():
    return sorted(SITE.glob("*.html"))


def check():
    bad = 0
    for p in pages():
        for m in re.finditer(RULE_RE.format(id=r"[A-Z]\d+"), p.read_text(encoding="utf-8"), re.S):
            if resync(m.group(0)) != m.group(0):
                print(f"out of sync: {p.name} {re.search(r'id=\"(\w+)\"', m.group(0)).group(1)}")
                bad += 1
    print("all data-search attrs in sync" if not bad else f"{bad} out of sync")
    return bad


def apply(tu):
    texts = {p: p.read_text(encoding="utf-8") for p in pages()}
    home = {}  # rule id -> category page (not everything.html)
    for e in tu["edits"]:
        rid = e["rule"]
        hits = 0
        for p, s in texts.items():
            m = re.search(RULE_RE.format(id=rid), s, re.S)
            if not m:
                continue
            block = m.group(0)
            if block.count(e["old"]) != 1:
                sys.exit(f"{rid} in {p.name}: 'old' found {block.count(e['old'])} times, need exactly 1:\n{e['old']}")
            block = block.replace(e["old"], e["new"])
            badge = f'<a class="tu-badge" href="updates.html#{tu["tu"]}">{tu["tu"]}</a>'
            if badge not in block:
                block = block.replace("</summary>", f" {badge}</summary>", 1)
            texts[p] = s[:m.start()] + resync(block) + s[m.end():]
            hits += 1
            if p.name != "everything.html":
                home[rid] = p.name
        if hits == 0:
            sys.exit(f"{rid} not found on any page")

    upd = SITE / "updates.html"
    links = "".join(f' <a class="tu-badge" href="{home.get(r, "everything.html")}#{r}">{r}</a>'
                    for r in dict.fromkeys(e["rule"] for e in tu["edits"]))
    entry = (f'<section class="banner" id="{tu["tu"]}"><strong>{tu["tu"]}</strong> ({tu["date"]})<br>'
             f'{html.escape(tu["summary"], quote=False)}<br>{links}</section>')
    s = texts[upd]
    if f'id="{tu["tu"]}"' in s:
        sys.exit(f"{tu['tu']} already logged on updates.html")
    i = s.index('<section class="banner"')  # newest first
    texts[upd] = s[:i] + entry + s[i:]

    today = date.today().isoformat()
    idx = SITE / "index.html"
    texts[idx] = re.sub(r"Up to date through: <strong>\w+</strong> \([\d-]+\)",
                        f'Up to date through: <strong>{tu["tu"]}</strong> ({tu["date"]})', texts[idx])
    texts[idx] = re.sub(r"Last built: <strong>[\d-]+</strong>", f"Last built: <strong>{today}</strong>", texts[idx])
    for p in texts:
        texts[p] = re.sub(r"Generated \d{4}-\d\d-\d\d\.", f"Generated {today}.", texts[p])
        p.write_text(texts[p], encoding="utf-8")
    print(f"{tu['tu']}: applied {len(tu['edits'])} edits to {len(home)} rules")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        sys.exit(1 if check() else 0)
    for f in sys.argv[1:]:
        apply(json.loads(Path(f).read_text(encoding="utf-8")))
