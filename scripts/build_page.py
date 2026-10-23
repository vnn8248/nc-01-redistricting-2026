"""
Embed data/processed/*.json into site/template.html and write site/index.html,
a single self-contained page.

Numbers in the page's text are {{placeholders}} filled from rebuild.json and
race_data.json, so the prose always matches the data. The build fails if any placeholder is left.

Usage:
    python scripts/build_page.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROCESSED, SITE  # noqa: E402


def embed(json_text):
    # Keep "</script>" inside the data from closing the script tag early
    return json_text.replace("</", "<\\/")


NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def article(n):
    """"a" or "an" before a number written in digits: an 8, an 11, an 18, an 80."""
    return "an" if n in ("8", "11", "18") or n.startswith("8") else "a"


def margin_label(m):
    # Matches marginLabel() in the template
    return "Even" if abs(m) < 0.05 else f"{'D' if m > 0 else 'R'}+{abs(m):.1f}"


def text_numbers(rebuild, race):
    """The figures written into the page's prose, from rebuild.json and race_data.json."""

    house = rebuild["house_2024"]
    pres = next(c for c in rebuild["contests"] if c["contest"] == "President")
    shifts = [abs(c["shift"]) for c in rebuild["contests"]]
    # Davis's edge over Harris on the old lines, carried to the new ones
    edge = house["margin"] - pres["old"]["margin"]

    def group(status):
        rows = [c for c in rebuild["counties"] if c["status"] == status]
        dem, rep, total = (sum(c[k] for c in rows) for k in ("dem", "rep", "total"))
        return rows, (dem - rep) / total * 100

    removed, removed_margin = group("removed")
    added, added_margin = group("added")
    kept, _ = group("kept")

    def share(area, group):
        counts = race["districts"][area]
        return f"{counts[group] / counts['total'] * 100:.0f}"

    return {
        "house_label": margin_label(house["margin"]),
        "house_abs": f"{abs(house['margin']):.1f}",
        "house_dem_pct": f"{house['dem_pct']:.1f}",
        "house_rep_pct": f"{house['rep_pct']:.1f}",
        "pres_old_label": margin_label(pres["old"]["margin"]),
        "pres_new_label": margin_label(pres["new"]["margin"]),
        "pres_old_abs": f"{abs(pres['old']['margin']):.1f}",
        "pres_new_abs": f"{abs(pres['new']['margin']):.1f}",
        "pres_old_int": f"{abs(pres['old']['margin']):.0f}",
        "pres_new_int": f"{abs(pres['new']['margin']):.0f}",
        "pres_new_article": article(f"{abs(pres['new']['margin']):.0f}"),
        "shift_min": f"{min(shifts):.0f}",
        "shift_max": f"{max(shifts):.0f}",
        "davis_edge": f"{edge:.1f}",
        "davis_new_abs": f"{abs(pres['new']['margin'] + edge):.1f}",
        # Partial-county rows (Granville, Swansboro) are in the groups' margins but aren't whole counties
        "removed_word": NUMBER_WORDS[sum(not c.get("part") for c in removed)],
        "added_word": NUMBER_WORDS[sum(not c.get("part") for c in added)],
        "removed_abs": f"{abs(removed_margin):.0f}",
        "added_abs": f"{abs(added_margin):.0f}",
        "kept_counties": str(sum(not c.get("part") for c in kept)),
        "race_old_black": share("old", "black"),
        "race_new_black": share("new", "black"),
        "race_removed_white": share("removed", "white"),
        "race_added_white": share("added", "white"),
        "people_per_dot": str(race["people_per_dot"]),
    }


def fill(template, values):
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], template)
    left = re.findall(r"\{\{\w*\}\}", page)
    assert not left, f"unfilled placeholders: {left}"
    return page


def main():
    rebuild = (PROCESSED / "rebuild.json").read_text()
    race = (PROCESSED / "race_data.json").read_text()
    template = fill((SITE / "template.html").read_text(), text_numbers(json.loads(rebuild), json.loads(race)))
    page = (
        template
        .replace("__MAPDATA__", embed((PROCESSED / "map_data.json").read_text()))
        .replace("__REBUILD__", embed(rebuild))
        .replace("__RACEDATA__", embed(race))
    )

    out = SITE / "index.html"
    out.write_text(page)
    print(f"Wrote {out} ({len(page) / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
