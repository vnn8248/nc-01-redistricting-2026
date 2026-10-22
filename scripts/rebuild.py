"""
Rebuild 2024 results inside the 2024 (S.L. 2023-145) and 2026 (S.L. 2025-95)
versions of District 1.

A district total = every row for its whole counties (precinct and
administrative: early voting sites, absentee, provisional) + the six Granville
precincts. Because the counties are whole, early and absentee votes are fully
counted, which a precinct-only rebuild couldn't do.

Writes data/processed/rebuild.json.

Usage:
    python scripts/rebuild.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    GRANVILLE_PRECINCTS, HOUSE_CONTEST, NEW_COUNTIES, OLD_COUNTIES, PROCESSED,
    RESULTS_2024, STATEWIDE_CONTESTS,
)


def load_results(path):
    df = pd.read_csv(path, dtype=str)
    df["votes"] = pd.to_numeric(df["Total Votes"])
    df["Precinct"] = df["Precinct"].str.strip().str.upper()
    return df


def district_rows(df, counties):
    whole = df["County"].isin(counties)
    granville = (df["County"] == "GRANVILLE") & df["Precinct"].isin(GRANVILLE_PRECINCTS)
    return df[whole | granville]


def two_party(df):
    """
    Democratic and Republican votes, total votes (third parties included) and
    the Democratic margin in points of the total.
    """

    by_party = df.groupby("Choice Party")["votes"].sum()
    total = int(df["votes"].sum())
    dem, rep = int(by_party.get("DEM", 0)), int(by_party.get("REP", 0))

    return {
        "dem": dem,
        "rep": rep,
        "total": total,
        "dem_pct": dem / total * 100,
        "rep_pct": rep / total * 100,
        "margin": (dem - rep) / total * 100,
    }


def check_old_lines(house):
    """
    The 2024 House race only ran inside the old lines, so rebuilding it from
    OLD_COUNTIES + Granville must reproduce its full total.
    """

    assert set(house["County"]) == set(OLD_COUNTIES) | {"GRANVILLE"}, "county list doesn't match 2024 NC-1"
    assert district_rows(house, OLD_COUNTIES)["votes"].sum() == house["votes"].sum(), "rebuild misses NC-1 votes"


def build(results):
    house = results[results["Contest Name"] == HOUSE_CONTEST]
    check_old_lines(house)

    contests = []
    for contest, label in STATEWIDE_CONTESTS.items():
        rows = results[results["Contest Name"] == contest]
        old = two_party(district_rows(rows, OLD_COUNTIES))
        new = two_party(district_rows(rows, NEW_COUNTIES))
        contests.append({"contest": label, "old": old, "new": new, "shift": new["margin"] - old["margin"]})

    pres = results[results["Contest Name"] == "US PRESIDENT"]
    counties = []
    for county in sorted(set(OLD_COUNTIES) | set(NEW_COUNTIES)):
        in_old, in_new = county in OLD_COUNTIES, county in NEW_COUNTIES
        status = "kept" if in_old and in_new else "removed" if in_old else "added"
        counties.append({"county": county.title(), "status": status, **two_party(pres[pres["County"] == county])})

    granville = pres[(pres["County"] == "GRANVILLE") & pres["Precinct"].isin(GRANVILLE_PRECINCTS)]
    counties.append({"county": "Granville (6 precincts)", "status": "kept", **two_party(granville)})

    return {"house_2024": two_party(house), "contests": contests, "counties": counties}


def main():
    out = build(load_results(RESULTS_2024))

    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "rebuild.json").write_text(json.dumps(out, indent=1))

    house = out["house_2024"]
    print(f"2024 NC-1: Davis {house['dem_pct']:.2f}%, Buckhout {house['rep_pct']:.2f}% (D{house['margin']:+.2f})")
    for row in out["contests"]:
        print(f"  {row['contest']:<20} 2024 lines D{row['old']['margin']:+6.2f}   "
              f"2026 lines D{row['new']['margin']:+6.2f}   shift {row['shift']:+.2f}")

    over = house["margin"] - out["contests"][0]["old"]["margin"]
    print(f"Davis ran {over:+.2f} pts ahead of Harris; same edge on 2026 lines: "
          f"D{out['contests'][0]['new']['margin'] + over:+.2f}")


if __name__ == "__main__":
    main()
