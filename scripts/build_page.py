"""
Embed data/processed/*.json into site/template.html and write site/index.html,
a single self-contained page.

Usage:
    python scripts/build_page.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROCESSED, SITE  # noqa: E402


def embed(json_text):
    # Keep "</script>" inside the data from closing the script tag early
    return json_text.replace("</", "<\\/")


def main():
    template = (SITE / "template.html").read_text()
    page = (
        template
        .replace("__MAPDATA__", embed((PROCESSED / "map_data.json").read_text()))
        .replace("__REBUILD__", embed((PROCESSED / "rebuild.json").read_text()))
    )

    out = SITE / "index.html"
    out.write_text(page)
    print(f"Wrote {out} ({len(page) / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
