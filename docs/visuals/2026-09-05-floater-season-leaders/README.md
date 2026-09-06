# Bulls single-season floater leaders

Approved chart: `assets/2026-09-06-v01-floater_season_leaders.png` (4400 × 4650,
transparent, 300 DPI), approved on 2026-09-06 at first render. The renderer always
writes publish DPI, so this asset is final as rendered. Canva owns the composed page:
https://www.canva.com/design/DAHUb8lCDWg/edit
The 1080 × 1350 page passed downloaded-page QA on 2026-09-06; see `canva-qa.json`.
That QA caught and corrected a subtitle reading "since 2000", stale from the layup page
the design was assembled from.
Editorial copy and publication status live in Notion.

## Scope and calculations

Bulls regular-season player-seasons ranked by floater FGM. Include NBA action labels
containing floating: `Floating Jump shot`, `Driving Floating Jump Shot` and
`Driving Floating Bank Jump Shot`. These are provider classifications, not video
reclassifications. All cutoff ties are retained (currently 15 rows, nine players).

The ranking window starts at 2015–16. It is not the layup post's 2000–01 window, and
the difference is a data constraint rather than an editorial choice:

- 2000–01 through 2006–07 carry no floating label at all.
- 2007–08 through 2014–15 carry only `Floating Jump shot`, at 39–128 Bulls attempts a
  season.
- Both driving labels first appear in 2015–16, and Bulls attempts jump to 347.

Earlier absence is unavailable classification, not an absence of floaters, so those
seasons are audited for coverage in `data/action_label_audit.csv` and
`data/all_player_seasons.csv` but never ranked. `data/ranked_player_seasons.csv` holds
the 224 ranked player-seasons in the published window. Stable label names from 2015–16
onward still do not remove subjective scorekeeper classification.

- FGA counts included shot rows; FGM sums made flags.
- ATT/G divides floater attempts by all official Bulls games played in that
  player-season.
- FG% = floater FGM / floater FGA; PPS = 2 × FG%, retained in data only.
- % OF FGA = floater FGA / all official Bulls FGA, including two- and three-point
  attempts.
- rFG% = player floater FG% minus the same season's aggregate NBA floater FG%, in
  percentage points. The baseline is within-season, which is the control that matters
  here: league floater volume roughly doubles between 2016–17 and 2018–19 as the labels
  are adopted, so cross-season FG% levels are not comparable but same-season ones are.
  Rates are calculated before rounding; the display uses one decimal.

A floating label on a three-point attempt is a long heave, not a floater. Seventeen such
Bulls attempts in the published window are excluded from the count and retained in
`EXCLUDED_HEAVES` in `data/all_player_seasons.csv`; the only make is Josh Giddey's
46-foot winner against the Lakers on 2025-03-27 (game 0022401063, event 668), which
moves his 2024–25 line from 89/187 to 88/186. The same rule removes 615 league
attempts from the baselines, counted in `data/league_floater_baselines.csv`.

`data/player_reconciliation.csv` covers 476 player-seasons. Floater plus other FGA
equals all official FGA exactly. `data/season_coverage.csv` reconciles total FGA, FGM
and games in all 26 Bulls seasons. `data/league_team_reconciliation.csv` independently
reconciles FGA, FGM and GP for 270 team-seasons across the nine seasons represented in
the top 15. All differences are zero.

## Reproduce

From the primary repository, using its Python environment:

```sh
venv/bin/python scripts/prototypes/floater_season_leaders.py --prepare
venv/bin/python scripts/prototypes/floater_season_leaders.py --relative-fg
venv/bin/python scripts/prototypes/floater_season_leaders.py --render
./run_tests.sh tests/test_floater_season_leaders.py -q
```

Existing snapshots are reused; absent snapshots are fetched from NBA.com. Raw snapshots
are lossless `.csv.gz`, with endpoint parameters and retrieval time in adjacent `.json`
files. League-wide snapshots are not post-specific, so `--relative-fg` reads an existing
snapshot from the layup post's `league_raw` where one exists and stores only genuinely
new pulls here; six of the nine seasons were already on disk. Fonts and portraits use
the shared cache.
