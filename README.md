# NC-1 Redistricting, 2024 vs. 2026

How the October 2025 redraw changed North Carolina's 1st Congressional District, where Don Davis (D) and Laurie Buckhout (R) meet again on Nov 3, 2026 after Davis won their 2024 race by 1.7 points.

The project builds one self-contained page, `site/index.html`, with:

- before-and-after maps of the 2024 and 2026 districts, by county (the default) or by precinct, colored by the House race or the 2024 presidential vote
- 2024 statewide results rebuilt inside each version of the district
- the counties traded in the redraw and how they voted

## Findings so far

On the 2024 lines, Trump won District 1 by 3.1 points. With the same 2024 votes counted inside the 2026 lines, he wins by 11.6. Every 2024 statewide race shifts 6 to 9 points toward Republicans. Davis ran 4.8 points ahead of Harris in 2024; that same edge on the new lines would lose by about 6.9.

The redraw removed Greene, Lenoir, Wayne and Wilson counties (Trump +9 combined) and added Beaufort, Carteret, Craven, Dare, Hyde and Pamlico, plus part of Swansboro precinct in Onslow (Trump +29). Both versions draw the same line through Granville County.

Among voting-age citizens (2020-2024 Census Bureau estimates), Black residents are 40% of the 2024 district and 32% of the 2026 one. In the areas added, 79% of voting-age citizens are white; in the areas removed, 54%.

## Data

| Input | Source |
|---|---|
| 2023 congressional plan, used in 2024 (S.L. 2023-145) | [NC General Assembly](https://www.ncleg.gov/Redistricting) |
| 2025 congressional plan, used in 2026 (S.L. 2025-95) | NC General Assembly |
| Precinct shapefiles, July 23, 2024 and Aug 24, 2026 | [NCSBE](https://dl.ncsbe.gov/?prefix=PrecinctMaps/) |
| Precinct results, Nov 5, 2024 (certified) and Nov 3, 2026 | [NCSBE](https://dl.ncsbe.gov/?prefix=ENRS/) |
| 2020 census redistricting data (P.L. 94-171), tables P1-P4 by block | [Census Bureau](https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html) |
| 2020 census block shapes, by county | [Census TIGER/Line](https://www2.census.gov/geo/tiger/TIGER2020PL/) |
| Citizen voting-age population by race and block group, 2020-2024 ACS special tabulation | [Census Bureau](https://www.census.gov/programs-surveys/decennial-census/about/voting-rights/cvap.html) |
| County boundaries cut at the shoreline (2020, 1:500,000), for the maps' water | [Census cartographic boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) |

Raw data isn't committed. `scripts/fetch_data.py` downloads all of it into `data/raw/`.

## Method

Both versions of District 1 are whole counties plus a few precincts. Both plans draw the same line through five Granville precincts, and the 2026 plan also takes part of Swansboro (SW19) in Onslow County. The lines split Salem (SALM), where about 55% of registered voters are in District 1, and Swansboro, where 4,853 of 7,450 residents are. Precinct results can't be divided, so all of their votes are counted. A district's rebuilt total is every 2024 vote in its whole counties, including early voting, absentee and provisional ballots, plus those precincts; Granville and Onslow report every vote by precinct, so nothing is lost there. `scripts/rebuild.py` checks the precinct lists against the 2024 House results and against the precincts NCSBE lists for the NC-1 race in its 2026 results file. The maps clip these precincts to the district line.

West Oxford Elementary (WOEL) is wholly in District 13 according to the plan shapefiles and the NCSBE voter file, but one 2024 WOEL ballot was counted in the NC-1 race. It's left out of the rebuild; the House check allows for that one vote. `scripts/rebuild.py` checks the method by rebuilding the 2024 House race on the old lines, which must match its official total.

The county view uses every vote, the same rows as the rebuilt totals. The precinct view can only shade votes reported by precinct. Some counties report early votes by voting site, so 52% to 78% of their votes can't be placed in a precinct; the precinct view hatches those counties. NCSBE's later precinct-sort files would assign those votes to precincts, but NCSBE adds statistical noise to them and says they shouldn't be used for reporting, so they aren't used here.

Margins are the Democrat's share minus the Republican's share of all votes in the race, third parties included.

The race maps show voting-age citizens, the people who can vote. The Census Bureau publishes them by block group (2020-2024 ACS special tabulation); `scripts/build_race_data.py` splits each block group's count for a group among its 2020 census blocks in proportion to the block's adults of that group (P.L. 94-171 table P4). Groups: non-Hispanic white alone, non-Hispanic Black alone, and everyone else (Hispanic residents of any race plus all other groups). Each block goes to a district by a point inside it. The script checks that both versions come to within one person of the ideal total population, 745,671, and that the 2024 district's voting-age citizens match the Census Bureau's own figure for NC-1 (they agree within 0.1%). Each dot stands for 5 voting-age citizens of one group, placed at random inside its block. The 2026 district also takes in part of Swansboro precinct in Onslow County (4,853 residents).

## Running it

```
pip install -r requirements.txt
python scripts/fetch_data.py
python scripts/rebuild.py
python scripts/build_map_data.py
python scripts/build_race_data.py
python scripts/build_page.py
```

Then open `site/index.html`.

After Nov 3, 2026, refresh the 2026 results and rebuild; the 2026 map switches from "pending" to precinct results on its own:

```
python scripts/fetch_data.py --only results_2026
python scripts/build_map_data.py
python scripts/build_page.py
```
