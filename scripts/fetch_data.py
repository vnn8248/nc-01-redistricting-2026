"""
Download the raw inputs into data/raw/: the two congressional plans from the
NC General Assembly, two NCSBE precinct shapefiles, and NCSBE precinct results
for Nov 5, 2024 and Nov 3, 2026.

NCSBE ships results as tab-delimited .txt inside a zip; they're saved here as
comma-separated .csv. Rerun after Nov 3, 2026 to replace the zero-vote 2026
template with real results (--only results_2026).

Usage:
    python scripts/fetch_data.py
    python scripts/fetch_data.py --only results_2026
"""

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAW  # noqa: E402

NCLEG = "https://www.ncleg.gov/Files/GIS/Plans_Main"
NCSBE = "https://s3.amazonaws.com/dl.ncsbe.gov"

SHAPEFILES = {
    "plan_2023": (f"{NCLEG}/Congress_2023/SL%202023-145%20Congress%20-%20Shapefile.zip",
                  RAW / "plans" / "plan_2023_SL2023-145"),
    "plan_2025": ("https://webservices.ncleg.gov/ViewBillDocument/2025/7667/0/SL%202025-95%20-%20Shapefile",
                  RAW / "plans" / "plan_2025_SL2025-95"),
    "precincts_2024": (f"{NCSBE}/PrecinctMaps/SBE_PRECINCTS_20240723.zip",
                       RAW / "precincts" / "SBE_PRECINCTS_20240723"),
    "precincts_2026": (f"{NCSBE}/PrecinctMaps/SBE_PRECINCTS_20260824.zip",
                       RAW / "precincts" / "SBE_PRECINCTS_20260824"),
}
RESULTS = {
    "results_2024": (f"{NCSBE}/ENRS/2024_11_05/results_pct_20241105.zip",
                     RAW / "results" / "results_pct_20241105.csv"),
    "results_2026": (f"{NCSBE}/ENRS/2026_11_03/results_pct_20261103.zip",
                     RAW / "results" / "results_pct_20261103.csv"),
}


def download(url):
    with urllib.request.urlopen(url) as response:
        return response.read()


def safe_members(archive):
    """Zip entries that stay inside the target folder (no absolute or ../ paths)."""

    for name in archive.namelist():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError(f"Refusing unsafe path in zip: {name}")

    return archive.namelist()


def fetch_shapefile(url, folder):
    folder.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(download(url))) as archive:
        archive.extractall(folder, members=safe_members(archive))

    print(f"Extracted {url} -> {folder}")


def fetch_results(url, csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(download(url))) as archive:
        txt = next(n for n in safe_members(archive) if n.endswith(".txt"))
        raw = archive.read(txt)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    df = pd.read_csv(io.StringIO(text), sep="\t", dtype=str)

    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df):,} rows from {url} -> {csv_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(SHAPEFILES | RESULTS), action="append")
    args = parser.parse_args()

    wanted = args.only or list(SHAPEFILES | RESULTS)

    for key in wanted:
        if key in SHAPEFILES:
            fetch_shapefile(*SHAPEFILES[key])
        else:
            fetch_results(*RESULTS[key])


if __name__ == "__main__":
    main()
