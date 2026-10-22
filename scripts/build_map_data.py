"""
Build SVG path data for the before/after maps.

Both maps share one frame (the union of the two District 1 versions' bounds,
in NC State Plane) so the districts are drawn at the same scale and position.

Layers
- house24:  2024 precincts in the 2024 district, 2024 NC-1 House result
- pres_old: 2024 precincts in the 2024 district, 2024 presidential result
- pres_new: 2024 precincts in the 2026 district, 2024 presidential result
- house26:  2026 precincts on the 2026 NC-1 ballot; all zeros until results
            are posted (rerun scripts/fetch_data.py --only results_2026)

Granville precincts are clipped to the district line, so a split precinct only
shades its District 1 part.

Only votes reported by precinct can be mapped. `county_unmapped` gives each
county's share of 2024 presidential votes in administrative units (early
voting sites, absentee, provisional).

Writes data/processed/map_data.json.

Usage:
    python scripts/build_map_data.py
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiPolygon, Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    CONTEXT_COUNTIES, CRS, GRANVILLE_PRECINCTS, GRANVILLE_SPLIT, HOUSE_CONTEST, NEW_COUNTIES, OLD_COUNTIES, PLAN_2023,
    PLAN_2025, PRECINCTS_2024, PRECINCTS_2026, PROCESSED, RESULTS_2024, RESULTS_2026,
)
from rebuild import load_results  # noqa: E402

WIDTH = 1000
SIMPLIFY_METERS = 120


def district_one(path, column):
    plan = gpd.read_file(path).to_crs(CRS)
    return plan[plan[column].astype(str).str.lstrip("0") == "1"]


class Frame:
    """Projects State Plane coordinates into a WIDTH-wide SVG viewBox."""

    def __init__(self, gdfs):
        minx, miny, maxx, maxy = pd.concat(gdfs).total_bounds
        pad = (maxx - minx) * 0.02
        self.minx, self.maxy = minx - pad, maxy + pad
        self.scale = WIDTH / (maxx - minx + 2 * pad)
        self.height = round((maxy - miny + 2 * pad) * self.scale)

    def bounds(self):
        return box(self.minx, self.maxy - self.height / self.scale, self.minx + WIDTH / self.scale, self.maxy)

    def xy(self, x, y):
        return round((x - self.minx) * self.scale, 1), round((self.maxy - y) * self.scale, 1)

    def path(self, geom):
        geom = geom.simplify(SIMPLIFY_METERS, preserve_topology=True)
        polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom] if isinstance(geom, Polygon) else []
        rings = []
        for poly in polys:
            rings.append(poly.exterior.coords)
            rings.extend(interior.coords for interior in poly.interiors)
        return "".join("M" + "L".join("%s,%s" % self.xy(x, y) for x, y in ring) + "Z" for ring in rings)


def load_precincts(path):
    precincts = gpd.read_file(path).to_crs(CRS)
    precincts["county"] = precincts["county_nam"].str.upper().str.strip()
    precincts["prec"] = precincts["prec_id"].astype(str).str.upper().str.strip()
    return precincts.dissolve(by=["county", "prec"], aggfunc="first")


def precinct_results(contest_rows):
    real = contest_rows[contest_rows["Real Precinct"] == "Y"]
    out = {}
    for key, rows in real.groupby(["County", "Precinct"]):
        by_party = rows.groupby("Choice Party")["votes"].sum()
        out[key] = {"d": int(by_party.get("DEM", 0)), "r": int(by_party.get("REP", 0)), "t": int(rows["votes"].sum())}
    return out


def layer(frame, precincts, results, district, counties):
    results = {key: res for key, res in results.items() if in_district(key, counties)}
    missing = [key for key in results if key not in precincts.index]
    if missing:
        raise ValueError(f"{len(missing)} results precincts have no polygon, e.g. {missing[:5]}")

    features = []
    for key, res in results.items():
        geometry = precincts.loc[key, "geometry"]
        if key[0] == "GRANVILLE":
            geometry = geometry.intersection(district)
        feature = {"c": key[0].title(), "n": str(precincts.loc[key, "enr_desc"]).title(), "p": frame.path(geometry), **res}
        if key[0] == "GRANVILLE" and key[1] in GRANVILLE_SPLIT:
            feature["split"] = 1
        features.append(feature)
    return features


def in_district(key, counties):
    county, precinct = key
    return county in counties or (county == "GRANVILLE" and precinct in GRANVILLE_PRECINCTS)


def granville_callout(frame, county, district):
    """Place Granville's label below the county, with an arrow up to its District 1 part.

    Most of Granville is outside the frame, so a label inside it would crowd Vance's.
    """
    inside = county.intersection(district)
    # Keep the centered label clear of the map's left edge
    half = 42
    x = max(frame.xy(inside.centroid.x, 0)[0], half + 2)
    px = frame.minx + x / frame.scale
    top, low = frame.maxy, frame.maxy - frame.height / frame.scale
    column = LineString([(px, top), (px, low)])
    tip = frame.xy(px, column.intersection(inside).bounds[1])[1] + 4
    # The county's lowest point anywhere under the label, so no border runs through it
    under = box(px - half / frame.scale, low, px + half / frame.scale, top)
    bottom = frame.xy(px, county.intersection(under).bounds[1])[1]
    return {"x": x, "y": round(bottom + 20, 1), "tip": [x, round(tip, 1)]}


def county_outlines(frame, precincts, counties, district=None):
    outlines = precincts.reset_index().dissolve(by="county")
    outlines = outlines[outlines.index.isin(counties)]
    features = []
    for county, row in outlines.iterrows():
        feature = {"c": county.title()}
        # Granville gets a callout and no outline; the district line marks its District 1 part
        if county == "GRANVILLE":
            feature.update(granville_callout(frame, row.geometry, district))
        else:
            feature["p"] = frame.path(row.geometry)
            feature["x"], feature["y"] = frame.xy(*row.geometry.representative_point().coords[0])
        # Which versions of the district include the county, so each map hatches only its own
        feature["old"], feature["new"] = int(county in OLD_COUNTIES), int(county in NEW_COUNTIES)
        features.append(feature)
    return features


def unmapped_share(contest_rows, counties):
    rows = contest_rows[contest_rows["County"].isin(counties)]
    total = rows.groupby("County")["votes"].sum()
    admin = rows[rows["Real Precinct"] == "N"].groupby("County")["votes"].sum()
    return {county.title(): round(float(admin.get(county, 0) / total[county]), 3) for county in total.index}


def main():
    old_d1 = district_one(PLAN_2023, "DISTRICT")
    new_d1 = district_one(PLAN_2025, "ID")
    frame = Frame([old_d1, new_d1])
    old_shape, new_shape = old_d1.geometry.union_all(), new_d1.geometry.union_all()

    results24, results26 = load_results(RESULTS_2024), load_results(RESULTS_2026)
    p24, p26 = load_precincts(PRECINCTS_2024), load_precincts(PRECINCTS_2026)

    house24 = precinct_results(results24[results24["Contest Name"] == HOUSE_CONTEST])
    pres = results24[results24["Contest Name"] == "US PRESIDENT"]
    pres_by_precinct = precinct_results(pres)
    house26 = precinct_results(results26[results26["Contest Name"] == HOUSE_CONTEST])

    counties = sorted(set(OLD_COUNTIES) | set(NEW_COUNTIES) | {"GRANVILLE"})

    out = {
        "w": WIDTH,
        "h": frame.height,
        "old_outline": frame.path(old_shape),
        "new_outline": frame.path(new_shape),
        "counties": county_outlines(frame, p26, counties, old_shape | new_shape),
        "context": county_outlines(frame, p26, CONTEXT_COUNTIES),
        "layers": {
            "house24": layer(frame, p24, house24, old_shape, OLD_COUNTIES),
            "pres_old": layer(frame, p24, pres_by_precinct, old_shape, OLD_COUNTIES),
            "pres_new": layer(frame, p24, pres_by_precinct, new_shape, NEW_COUNTIES),
            "house26": layer(frame, p26, house26, new_shape, NEW_COUNTIES),
        },
        "county_unmapped": unmapped_share(pres, counties),
    }

    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "map_data.json"
    path.write_text(json.dumps(out, separators=(",", ":")))

    counts = {name: len(features) for name, features in out["layers"].items()}
    votes26 = sum(f["t"] for f in out["layers"]["house26"])
    print(f"Wrote {path} ({path.stat().st_size / 1024:,.0f} KB): {counts}; 2026 NC-1 votes so far: {votes26:,}")


if __name__ == "__main__":
    main()
