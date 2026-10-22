"""
Shared paths and district definitions for the NC-1 redraw analysis.

Both versions of District 1 are whole-county districts except Granville, whose
District 1 slice is the same six precincts in both plans. The county lists below
were read off the plan shapefiles; scripts/rebuild.py checks them against the
2024 House results.
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
GRANVILLE_PRECINCTS = {"ANTI", "CRDL", "EAOX", "SALM", "SOOX", "WOEL"}

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
