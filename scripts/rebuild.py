"""
Rebuild 2024 results inside the 2024 (S.L. 2023-145) and 2026 (S.L. 2025-95)
versions of District 1.

A district total = every row for its whole counties (precinct and
administrative: early voting sites, absentee, provisional) + its precincts in
partial counties (five in Granville; in 2026, also Swansboro in Onslow). Because
the counties are whole, early and absentee votes are fully counted, which a
precinct-only rebuild couldn't do. Granville and Onslow report every vote by
precinct, so their precinct rows are complete.

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
    HOUSE_CONTEST, NEW_COUNTIES, NEW_PRECINCTS, OLD_COUNTIES, OLD_PRECINCTS, PROCESSED,
    RESULTS_2024, RESULTS_2026, STATEWIDE_CONTESTS, STRAY_HOUSE_PRECINCTS,
)


def load_results(path):
    df = pd.read_csv(path, dtype=str)
    df["votes"] = pd.to_numeric(df["Total Votes"])
    df["Precinct"] = df["Precinct"].str.strip().str.upper()
    return df


def precinct_keys(df):
    return pd.Series(list(zip(df["County"], df["Precinct"])), index=df.index)


def district_rows(df, counties, precincts):
    return df[df["County"].isin(counties) | precinct_keys(df).isin(precincts)]


def partial_counties(precincts):
    return {county for county, _ in precincts}


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
    OLD_COUNTIES + OLD_PRECINCTS, plus the stray WOEL ballot, must reproduce its
    full total.
    """

    assert set(house["County"]) == set(OLD_COUNTIES) | partial_counties(OLD_PRECINCTS), "county list doesn't match 2024 NC-1"
    stray = house[precinct_keys(house).isin(STRAY_HOUSE_PRECINCTS)]["votes"].sum()
    assert stray <= 1, f"{stray} NC-1 votes in precincts outside the district"
    total = district_rows(house, OLD_COUNTIES, OLD_PRECINCTS)["votes"].sum() + stray
    assert total == house["votes"].sum(), "rebuild misses NC-1 votes"


def check_new_lines(house26):
    """
    NCSBE's 2026 results file lists every precinct with the NC-1 race on its
    ballot, even before results. Its counties and partial-county precincts must
    match NEW_COUNTIES + NEW_PRECINCTS. WOEL is listed too, though no District 1
    voter lives there (see STRAY_HOUSE_PRECINCTS).
    """

    partial = partial_counties(NEW_PRECINCTS)
    assert set(house26["County"]) == set(NEW_COUNTIES) | partial, "county list doesn't match the 2026 NC-1 ballot"
    listed = set(precinct_keys(house26[house26["County"].isin(partial)]))
    assert listed - STRAY_HOUSE_PRECINCTS == NEW_PRECINCTS, f"2026 NC-1 precincts differ: {sorted(listed ^ NEW_PRECINCTS)}"


def build(results, results26):
    house = results[results["Contest Name"] == HOUSE_CONTEST]
    check_old_lines(house)
    check_new_lines(results26[results26["Contest Name"] == HOUSE_CONTEST])

    contests = []
    for contest, label in STATEWIDE_CONTESTS.items():
        rows = results[results["Contest Name"] == contest]
        old = two_party(district_rows(rows, OLD_COUNTIES, OLD_PRECINCTS))
        new = two_party(district_rows(rows, NEW_COUNTIES, NEW_PRECINCTS))
        contests.append({"contest": label, "old": old, "new": new, "shift": new["margin"] - old["margin"]})

    pres = results[results["Contest Name"] == "US PRESIDENT"]
    counties = []
    for county in sorted(set(OLD_COUNTIES) | set(NEW_COUNTIES)):
        in_old, in_new = county in OLD_COUNTIES, county in NEW_COUNTIES
        status = "kept" if in_old and in_new else "removed" if in_old else "added"
        counties.append({"county": county.title(), "status": status, **two_party(pres[pres["County"] == county])})

    # Partial counties: one row each for their District 1 precincts, flagged so text can count whole counties
    for county in sorted(partial_counties(OLD_PRECINCTS | NEW_PRECINCTS)):
        old = {p for c, p in OLD_PRECINCTS if c == county}
        new = {p for c, p in NEW_PRECINCTS if c == county}
        assert not old or not new or old == new, f"{county}: the two versions take different precincts"
        status = "kept" if old and new else "removed" if old else "added"
        names = old | new
        rows = pres[(pres["County"] == county) & pres["Precinct"].isin(names)]
        label = f"{len(names)} precincts" if len(names) > 1 else "Swansboro" if names == {"SW19"} else next(iter(names))
        counties.append({"county": f"{county.title()} ({label})", "status": status, "part": True, **two_party(rows)})

    return {"house_2024": two_party(house), "contests": contests, "counties": counties}


def main():
    out = build(load_results(RESULTS_2024), load_results(RESULTS_2026))

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
