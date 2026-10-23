"""
Download the raw inputs into data/raw/: the two congressional plans from the
NC General Assembly, two NCSBE precinct shapefiles, NCSBE precinct results
for Nov 5, 2024 and Nov 3, 2026, census shoreline county boundaries for the
maps' water, 2020 census block data (P.L. 94-171 redistricting file and TIGER
block shapes) for the district's counties, and the Census Bureau's citizen
voting-age population (CVAP) tabulation from the 2020-2024 ACS.

NCSBE ships results as tab-delimited .txt inside a zip; they're saved here as
comma-separated .csv. Rerun after Nov 3, 2026 to replace the zero-vote 2026
template with real results (--only results_2026).

Usage:
    python scripts/fetch_data.py
    python scripts/fetch_data.py --only results_2026
    python scripts/fetch_data.py --only census
"""

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CENSUS_BLOCKS, CENSUS_PL, CVAP_BLOCK_GROUPS, CVAP_DISTRICTS, NEW_COUNTIES, OLD_COUNTIES, PARTIAL_COUNTIES, RAW,
)

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
    "land": ("https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_county_500k.zip",
             RAW / "census" / "cb_2020_us_county_500k"),
}
RESULTS = {
    "results_2024": (f"{NCSBE}/ENRS/2024_11_05/results_pct_20241105.zip",
                     RAW / "results" / "results_pct_20241105.csv"),
    "results_2026": (f"{NCSBE}/ENRS/2026_11_03/results_pct_20261103.zip",
                     RAW / "results" / "results_pct_20261103.csv"),
}
CENSUS = "https://www2.census.gov"
PL_URL = f"{CENSUS}/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/North_Carolina/nc2020.pl.zip"
BLOCKS_URL = CENSUS + "/geo/tiger/TIGER2020PL/STATE/37_NORTH_CAROLINA/37{fips}/tl_2020_37{fips}_tabblock20.zip"
# The geographic header, segment 1 (P1, P2: everyone) and segment 2 (P3, P4: adults)
PL_MEMBERS = {"ncgeo2020.pl", "nc000012020.pl", "nc000022020.pl"}
CVAP_URL = f"{CENSUS}/programs-surveys/decennial/rdo/datasets/2024/2024-cvap/CVAP_2020-2024_ACS_csv_files.zip"


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


def fetch_census():
    """The P.L. 94-171 file, then block shapes for every county in either district."""

    CENSUS_PL.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(download(PL_URL))) as archive:
        archive.extractall(CENSUS_PL, members=[n for n in safe_members(archive) if n in PL_MEMBERS])
    print(f"Extracted {PL_URL} -> {CENSUS_PL}")

    # County FIPS codes from the file's own county rows (summary level 050)
    geo = pd.read_csv(CENSUS_PL / "ncgeo2020.pl", sep="|", header=None, dtype=str, encoding="latin-1")
    counties = geo[geo[2] == "050"]
    fips = dict(zip(counties[86].str.upper(), counties[14]))

    for county in sorted(set(OLD_COUNTIES) | set(NEW_COUNTIES) | set(PARTIAL_COUNTIES)):
        fetch_shapefile(BLOCKS_URL.format(fips=fips[county]), CENSUS_BLOCKS / fips[county])

    # Citizen voting-age population; the national files are large, so keep NC rows only
    with zipfile.ZipFile(io.BytesIO(download(CVAP_URL))) as archive:
        for member, out, prefix in (("BlockGr.csv", CVAP_BLOCK_GROUPS, "1500000US37"), ("CD.csv", CVAP_DISTRICTS, "5001900US37")):
            with archive.open(member) as f:
                df = pd.read_csv(f, dtype={"geoid": str}, encoding="latin-1")
            df[df["geoid"].str.startswith(prefix)].to_csv(out, index=False)
            print(f"Saved NC rows of {member} -> {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted([*SHAPEFILES, *RESULTS, "census"]), action="append")
    args = parser.parse_args()

    wanted = args.only or [*SHAPEFILES, *RESULTS, "census"]

    for key in wanted:
        if key == "census":
            fetch_census()
        elif key in SHAPEFILES:
            fetch_shapefile(*SHAPEFILES[key])
        else:
            fetch_results(*RESULTS[key])


if __name__ == "__main__":
    main()
