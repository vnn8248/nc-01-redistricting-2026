"""
Shared paths and district definitions for the NC-1 redraw analysis.

Both versions of District 1 are whole counties plus a few precincts. Both plans
draw the same line through Granville: four whole precincts and part of a fifth.
The 2026 plan also takes part of one Onslow precinct, Swansboro. The lists below
were read off the plan shapefiles; scripts/rebuild.py checks them against the
2024 House results and NCSBE's 2026 ballot template.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SITE = ROOT / "site"

PLAN_2023 = RAW / "plans" / "plan_2023_SL2023-145" / "SL 2023-145.shp"
PLAN_2025 = RAW / "plans" / "plan_2025_SL2025-95" / "SL 2025-95.shp"
PRECINCTS_2024 = RAW / "precincts" / "SBE_PRECINCTS_20240723" / "SBE_PRECINCTS_20240723.shp"
PRECINCTS_2026 = RAW / "precincts" / "SBE_PRECINCTS_20260824" / "SBE_PRECINCTS_20260824.shp"
RESULTS_2024 = RAW / "results" / "results_pct_20241105.csv"
RESULTS_2026 = RAW / "results" / "results_pct_20261103.csv"
# Census cartographic county boundaries, cut at the shoreline; the maps draw water as everything else
LAND = RAW / "census" / "cb_2020_us_county_500k" / "cb_2020_us_county_500k.shp"
CENSUS_PL = RAW / "census" / "nc2020.pl"
CENSUS_BLOCKS = RAW / "census" / "blocks"
# Citizen voting-age population by race, 2020-2024 ACS special tabulation (NC rows only)
CVAP_BLOCK_GROUPS = RAW / "census" / "cvap_2020_2024_blockgr_nc.csv"
CVAP_DISTRICTS = RAW / "census" / "cvap_2020_2024_cd_nc.csv"

# NC State Plane (meters), the plans' own projection
CRS = 32119

HOUSE_CONTEST = "US HOUSE OF REPRESENTATIVES DISTRICT 01"

OLD_COUNTIES = [
    "BERTIE", "CAMDEN", "CHOWAN", "CURRITUCK", "EDGECOMBE", "GATES", "GREENE",
    "HALIFAX", "HERTFORD", "LENOIR", "MARTIN", "NASH", "NORTHAMPTON", "PASQUOTANK",
    "PERQUIMANS", "TYRRELL", "VANCE", "WARREN", "WASHINGTON", "WAYNE", "WILSON",
]
NEW_COUNTIES = [
    "BEAUFORT", "BERTIE", "CAMDEN", "CARTERET", "CHOWAN", "CRAVEN", "CURRITUCK",
    "DARE", "EDGECOMBE", "GATES", "HALIFAX", "HERTFORD", "HYDE", "MARTIN", "NASH",
    "NORTHAMPTON", "PAMLICO", "PASQUOTANK", "PERQUIMANS", "TYRRELL", "VANCE",
    "WARREN", "WASHINGTON",
]
# Precincts in District 1 outside its whole counties, as (county, precinct)
GRANVILLE_PRECINCTS = {("GRANVILLE", p) for p in ("ANTI", "CRDL", "EAOX", "SALM", "SOOX")}
OLD_PRECINCTS = GRANVILLE_PRECINCTS
NEW_PRECINCTS = GRANVILLE_PRECINCTS | {("ONSLOW", "SW19")}
# The plan lines run through these. Precinct results can't be divided, so all of
# their votes are counted: about 55% of Salem's voters and 65% of Swansboro's
# residents are in District 1.
SPLIT_PRECINCTS = {("GRANVILLE", "SALM"), ("ONSLOW", "SW19")}
# Counties with only some precincts in District 1
PARTIAL_COUNTIES = sorted({county for county, _ in OLD_PRECINCTS | NEW_PRECINCTS})

# WOEL is wholly in District 13 (plan shapefiles; NCSBE voter file), but one 2024
# WOEL ballot was counted in the NC-1 race. The House check allows for it.
STRAY_HOUSE_PRECINCTS = {("GRANVILLE", "WOEL")}

# Counties in neither version that the district wraps around; the maps outline
# and label them so the hole reads as a county, not missing data
CONTEXT_COUNTIES = ["PITT"]

# 2024 statewide races used to compare the two versions of the district
STATEWIDE_CONTESTS = {
    "US PRESIDENT": "President",
    "NC LIEUTENANT GOVERNOR": "Lieutenant governor",
    "NC SUPREME COURT ASSOCIATE JUSTICE SEAT 06": "Supreme Court",
    "NC ATTORNEY GENERAL": "Attorney general",
    "NC GOVERNOR": "Governor",
}
