# NC-1 Redistricting, 2024 vs. 2026

How the October 2025 redraw changed North Carolina's 1st Congressional District, where Don Davis (D) and Laurie Buckhout (R) meet again on Nov 3, 2026 after Davis won their 2024 race by 1.7 points.

The project builds one self-contained page, `site/index.html`, with:

- before-and-after precinct maps of the 2024 and 2026 districts, colored by the House race or the 2024 presidential vote
- 2024 statewide results rebuilt inside each version of the district
- the counties traded in the redraw and how they voted

## Findings so far

On the 2024 lines, Trump won District 1 by 3.0 points. With the same 2024 votes counted inside the 2026 lines, he wins by 11.2. Every 2024 statewide race shifts 6 to 8 points toward Republicans. Davis ran 4.7 points ahead of Harris in 2024; that same edge on the new lines would lose by about 6.5.

The redraw removed Greene, Lenoir, Wayne and Wilson counties (Trump +9 combined) and added Beaufort, Carteret, Craven, Dare, Hyde and Pamlico (Trump +29). Both versions include the same six Granville precincts.

## Data

| Input | Source |
|---|---|
| 2023 congressional plan, used in 2024 (S.L. 2023-145) | [NC General Assembly](https://www.ncleg.gov/Redistricting) |
| 2025 congressional plan, used in 2026 (S.L. 2025-95) | NC General Assembly |
| Precinct shapefiles, July 23, 2024 and Aug 24, 2026 | [NCSBE](https://dl.ncsbe.gov/?prefix=PrecinctMaps/) |
| Precinct results, Nov 5, 2024 (certified) and Nov 3, 2026 | [NCSBE](https://dl.ncsbe.gov/?prefix=ENRS/) |

Raw data isn't committed. `scripts/fetch_data.py` downloads all of it into `data/raw/`.

## Method

Both versions of District 1 are whole-county districts except Granville, where both include the same six precincts. A district's rebuilt total is every 2024 vote in its counties, including early voting, absentee and provisional ballots, plus those six precincts. `scripts/rebuild.py` checks the method by rebuilding the 2024 House race on the old lines, which must match its official total.

The maps can only shade votes reported by precinct. Some counties report early votes by voting site, so 52% to 78% of their votes can't be placed in a precinct; the page hatches those counties. NCSBE's later precinct-sort files would assign those votes to precincts, but NCSBE adds statistical noise to them and says they shouldn't be used for reporting, so they aren't used here.

Margins are the Democrat's share minus the Republican's share of all votes in the race, third parties included.

## Running it

```
pip install -r requirements.txt
python scripts/fetch_data.py
python scripts/rebuild.py
python scripts/build_map_data.py
python scripts/build_page.py
```

Then open `site/index.html`.

After Nov 3, 2026, refresh the 2026 results and rebuild; the 2026 map switches from "pending" to precinct results on its own:

```
python scripts/fetch_data.py --only results_2026
python scripts/build_map_data.py
python scripts/build_page.py
```
