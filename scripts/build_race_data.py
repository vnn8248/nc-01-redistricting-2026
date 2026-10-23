"""
Build the race dot maps of voting-age citizens, the population that can vote.

Voting-age citizens (CVAP) come from the Census Bureau's 2020-2024 ACS special
tabulation, published by block group. Each block group's count for a group is
split among its 2020 census blocks in proportion to the block's adults of that
group (P.L. 94-171 table P4). Groups: non-Hispanic white alone, non-Hispanic
Black alone, and everyone else (Hispanic of any race plus every other group).

Each block in either version of District 1 then gets one dot per DOT_PEOPLE
voting-age citizens of each group, placed at random inside the block.

Blocks are assigned to a district by a point inside them. The plans were drawn
from 2020 blocks, so each district's total population should be within a
person of the ideal size; the build checks that. It also checks the 2024
district's voting-age citizens against the Census Bureau's own figure for it.

Dots share the vote maps' frame. Each is packed into two uint16 values: x, and
y with the group in its top two bits. They're sorted by district status (kept,
old only, new only) and shuffled within each status so no group is always
drawn on top.

Writes data/processed/race_data.json.

Usage:
    python scripts/build_race_data.py
"""

import base64
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CENSUS_BLOCKS, CENSUS_PL, CRS, CVAP_BLOCK_GROUPS, CVAP_DISTRICTS, PLAN_2023, PLAN_2025, PROCESSED,
)
from build_map_data import Frame, district_one  # noqa: E402

DOT_PEOPLE = 5
GROUPS = ["black", "white", "other"]
STATUSES = ["kept", "old", "new"]
# 2020 apportionment population of NC divided by its 14 House seats
IDEAL_DISTRICT = 745_671
SEED = 2020


def read_segment(name, first):
    """Logical record, the first table's total, and the second table's total, white alone and Black alone
    (non-Hispanic). Segments 1 and 2 share a layout: P1/P2 for everyone, P3/P4 for adults."""

    seg = pd.read_csv(CENSUS_PL / name, sep="|", header=None, usecols=[4, 5, 76, 80, 81], dtype={4: str}, encoding="latin-1")
    assert (seg[5] == seg[76]).all(), f"{name}: table totals disagree; check segment column positions"
    return seg.rename(columns={4: "logrecno", 76: first, 80: f"{first}_white", 81: f"{first}_black"}).drop(columns=5)


def load_blocks():
    """Block shapes with total population and adults by group, for every downloaded county."""

    # Geographic header: summary level, logical record number, GEOID
    geo = pd.read_csv(CENSUS_PL / "ncgeo2020.pl", sep="|", header=None, usecols=[2, 7, 9], dtype=str, encoding="latin-1")
    geo = geo[geo[2] == "750"].rename(columns={7: "logrecno", 9: "GEOID20"})
    pop = geo.merge(read_segment("nc000012020.pl", "total"), on="logrecno").merge(read_segment("nc000022020.pl", "adults"), on="logrecno")
    pop["adults_other"] = pop["adults"] - pop["adults_white"] - pop["adults_black"]

    shapes = pd.concat(gpd.read_file(p) for p in sorted(CENSUS_BLOCKS.glob("*/*.shp")))
    blocks = shapes[["GEOID20", "geometry"]].to_crs(CRS).merge(pop, on="GEOID20", how="left")
    assert blocks["total"].notna().all(), "blocks missing from the P.L. 94-171 file"

    return blocks[blocks["total"] > 0].reset_index(drop=True)


def load_cvap(path, key):
    """Voting-age citizens by group for each area in a CVAP file, indexed by `key`(geoid)."""

    cv = pd.read_csv(path, dtype={"geoid": str}).pivot_table(index="geoid", columns="lnnumber", values="cvap_est", aggfunc="sum")
    # Line 1 is the total, 5 is non-Hispanic Black alone, 7 is non-Hispanic white alone
    out = pd.DataFrame({"black": cv[5], "white": cv[7], "other": cv[1] - cv[5] - cv[7]})
    out.index = out.index.map(key)
    return out


def allocate_cvap(blocks):
    """Split each block group's voting-age citizens among its blocks, group by group, by the blocks' 2020 adults."""

    bg = load_cvap(CVAP_BLOCK_GROUPS, lambda g: g[-12:])
    blocks = blocks.assign(bg=blocks["GEOID20"].str[:12])
    group_adults = blocks.groupby("bg")[[f"adults_{g}" for g in GROUPS] + ["adults"]].transform("sum")
    lost = 0.0
    for g in GROUPS:
        cvap = blocks["bg"].map(bg[g]).fillna(0)
        # A group with citizens in the block group but no 2020 adults there is spread by all adults instead
        share = (blocks[f"adults_{g}"] / group_adults[f"adults_{g}"]).where(group_adults[f"adults_{g}"] > 0,
                                                                           blocks["adults"] / group_adults["adults"])
        blocks[g] = cvap * share.fillna(0)
        lost += cvap.where(group_adults["adults"] == 0, 0).groupby(blocks["bg"]).first().sum()
    covered = bg.loc[bg.index.isin(blocks["bg"])].to_numpy().sum()
    assert lost < covered * 0.001, f"{lost:,.0f} voting-age citizens in block groups with no 2020 adults"
    blocks["cvap"] = blocks[GROUPS].sum(axis=1)
    return blocks


def check_against_census(blocks):
    """The 2024 district's CVAP should match the Census Bureau's tabulation for NC-1 (119th Congress lines)."""

    official = load_cvap(CVAP_DISTRICTS, lambda g: g[-2:]).loc["01"]
    ours = blocks.loc[blocks["status"].isin(["kept", "old"]), GROUPS].sum()
    for g in GROUPS:
        assert abs(ours[g] - official[g]) <= max(official[g] * 0.005, 100), f"2024 NC-1 {g} CVAP {ours[g]:,.0f} vs official {official[g]:,}"
    return {g: int(official[g]) for g in GROUPS}


def assign(blocks, old_shape, new_shape):
    points = blocks.geometry.representative_point()
    xs, ys = points.x.to_numpy(), points.y.to_numpy()
    shapely.prepare(old_shape)
    shapely.prepare(new_shape)
    in_old = shapely.contains_xy(old_shape, xs, ys)
    in_new = shapely.contains_xy(new_shape, xs, ys)

    for name, mask in (("2024", in_old), ("2026", in_new)):
        total = int(blocks.loc[mask, "total"].sum())
        assert abs(total - IDEAL_DISTRICT) <= 1, f"{name} District 1 has {total:,} people, ideal is {IDEAL_DISTRICT:,}"

    status = np.select([in_old & in_new, in_old, in_new], STATUSES, default="")
    return blocks.assign(status=status)[status != ""].reset_index(drop=True)


def place_dots(blocks, rng):
    """Random points inside each block, one per DOT_PEOPLE voting-age citizens of a group."""

    rows = []
    for geom, status, *counts in blocks[["geometry", "status", *GROUPS]].itertuples(index=False):
        # Round each group's dot count up or down at random, so totals stay unbiased
        want = [int(c // DOT_PEOPLE + (rng.random() < c % DOT_PEOPLE / DOT_PEOPLE)) for c in counts]
        need = sum(want)
        if not need:
            continue
        minx, miny, maxx, maxy = geom.bounds
        shapely.prepare(geom)
        xs, ys = [], []
        while len(xs) < need:
            x = rng.uniform(minx, maxx, need * 4)
            y = rng.uniform(miny, maxy, need * 4)
            keep = shapely.contains_xy(geom, x, y)
            xs.extend(x[keep])
            ys.extend(y[keep])
        group = np.repeat(np.arange(len(GROUPS)), want)
        rows.append(pd.DataFrame({"x": xs[:need], "y": ys[:need], "g": group, "s": status}))

    return pd.concat(rows, ignore_index=True)


def pack(dots, frame, rng):
    """Shuffle within each status, then pack into little-endian uint16 pairs."""

    dots = dots.sample(frac=1, random_state=rng.integers(2**32)).sort_values("s", key=lambda s: s.map(STATUSES.index), kind="stable")
    x = (dots["x"] - frame.minx) * frame.scale
    y = (frame.maxy - dots["y"]) * frame.scale
    width, height = frame.bounds().bounds[2] - frame.minx, frame.height
    assert x.between(0, width * frame.scale).all() and y.between(0, height).all(), "dots outside the frame"
    qx = np.round(x / (width * frame.scale) * 65535).astype("<u2")
    qy = np.round(y / height * 16383).astype("<u2") | (dots["g"].to_numpy().astype("<u2") << 14)
    packed = np.column_stack([qx, qy]).astype("<u2").tobytes()
    counts = dots["s"].value_counts().reindex(STATUSES, fill_value=0)
    return base64.b64encode(packed).decode(), [int(n) for n in counts]


def summary(blocks, statuses):
    rows = blocks[blocks["status"].isin(statuses)]
    counts = {g: round(rows[g].sum()) for g in GROUPS}
    return {"total": sum(counts.values()), **counts}


def main():
    old_d1 = district_one(PLAN_2023, "DISTRICT")
    new_d1 = district_one(PLAN_2025, "ID")
    frame = Frame([old_d1, new_d1])
    old_shape, new_shape = old_d1.geometry.union_all(), new_d1.geometry.union_all()

    blocks = assign(allocate_cvap(load_blocks()), old_shape, new_shape)
    official = check_against_census(blocks)
    rng = np.random.default_rng(SEED)
    dots = place_dots(blocks, rng)
    packed, counts = pack(dots, frame, rng)

    out = {
        "people_per_dot": DOT_PEOPLE,
        "groups": GROUPS,
        "statuses": STATUSES,
        "counts": counts,
        "dots": packed,
        "districts": {
            "old": summary(blocks, ["kept", "old"]),
            "new": summary(blocks, ["kept", "new"]),
            "kept": summary(blocks, ["kept"]),
            "removed": summary(blocks, ["old"]),
            "added": summary(blocks, ["new"]),
        },
    }

    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "race_data.json"
    path.write_text(json.dumps(out, separators=(",", ":")))

    shares = {k: {g: f"{v[g] / v['total']:.1%}" for g in GROUPS} for k, v in out["districts"].items()}
    print(f"Wrote {path} ({path.stat().st_size / 1024:,.0f} KB): {len(dots):,} dots, {counts} by status")
    print(f"2024 NC-1 CVAP: ours {out['districts']['old']}, Census Bureau {official}")
    print(json.dumps(shares, indent=1))


if __name__ == "__main__":
    main()
