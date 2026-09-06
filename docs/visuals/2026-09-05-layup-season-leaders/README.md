# Bulls single-season layup leaders

Approved chart: `assets/2026-09-05-v09-layup_season_leaders.png` (4400 × 4650,
transparent, 300 DPI). Canva owns the composed page:
https://www.canva.com/design/DAHUbfjgsjY/boFI8TtNlNTfBlmp_1sZTg/edit
The 1080 × 1350 page passed downloaded-page QA on 2026-09-06; see `canva-qa.json`.
Editorial copy and publication status live in Notion, page `3bae1c13abe68070a0fefe44674b6a9a`.

## Scope and calculations

Bulls regular-season player-seasons, 2000–01 through 2025–26, ranked by layup FGM.
Include NBA action labels containing layup or finger roll, including putback layups;
exclude tips, dunks and floating shots. These are provider classifications, not video
reclassifications. Legacy finger-roll labels and the later tip-label split are audited.
All cutoff ties are retained (currently 15 rows, six players).

- FGA counts included shot rows; FGM sums made flags.
- ATT/G divides layup attempts by all official Bulls games played in that player-season.
- FG% = layup FGM / layup FGA; PPS = 2 × FG%, retained in data only.
- % OF FGA = layup FGA / all official Bulls FGA, including two- and three-point attempts.
- rFG% = player layup FG% minus the same season's aggregate NBA layup FG%, in percentage
  points. Rates are calculated before rounding; the display uses one decimal.

`data/player_reconciliation.csv` covers 476 player-seasons. Layup plus other FGA equals
all official FGA exactly. `data/season_coverage.csv` reconciles total FGA, FGM and games
in all 26 Bulls seasons. `data/league_team_reconciliation.csv` independently reconciles
FGA, FGM and GP for 390 team-seasons across the 13 seasons represented in the top 15.
All differences are zero. League action/value conflicts (layup labels on non-two-point
shots) are excluded from the baseline and counted in `league_layup_baselines.csv`.

## Reproduce

From the primary repository, using its Python environment:

```sh
venv/bin/python scripts/prototypes/layup_season_leaders.py --prepare
venv/bin/python scripts/prototypes/layup_season_leaders.py --relative-fg
venv/bin/python scripts/prototypes/layup_season_leaders.py --render
./run_tests.sh tests/test_layup_season_leaders.py -q
```

Existing snapshots are reused; absent snapshots are fetched from NBA.com. Raw snapshots
are lossless `.csv.gz`, with endpoint parameters and metadata in adjacent `.json` files.
`data/snapshot_compression_audit.json` records byte equality and original content hashes.
Original league shot retrieval timestamps were not retained and are explicitly unavailable;
new official team-total snapshots have recorded retrieval times. Fonts and portraits use the
shared cache. The final rebuild was pixel-identical to v09 after the coverage safeguards.

Retained decision-bearing alternatives: v02 initial table, v03 rejected bar treatment,
v05 addition of shot share, v09 approved table with relative finishing. Superseded cosmetic
iterations and low-resolution review images are excluded from the tracked archive.
