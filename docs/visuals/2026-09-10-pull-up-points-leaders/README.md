# Bulls pull-up points season leaders

Posted carousel: cover, top 15 by pull-up points, and top 15 by 3-point pull-up points,
2013–14 through 2025–26 regular season, Chicago production only. The two data slides
use the table-bar hybrid. Hero: PTS. All pull-ups support PTS/G, eFG%, relative eFG,
and FGA/G; 3-point pull-ups support PTS/G, 3P%, relative 3P%, and FGA/G.
Notion brief: https://www.notion.so/3a8e1c13abe6803ba17bc1b25580f5bb

## Reproduce

From this worktree, use the primary checkout's `venv/bin/python`:

```sh
python scripts/prototypes/pull_up_points_data.py
python scripts/prototypes/pull_up_points_bars.py --final --output output/pull-up-points-leaders/bars-top15.png
./run_tests.sh tests/test_pull_up_points_data.py -q
```

Preparation reuses saved raw responses; `--refresh` fetches new snapshots. Each raw JSON
records endpoint, parameters and retrieval time. `all_player_seasons.csv` preserves the
full candidate population; `season_audit.csv` records coverage, baseline and discrepancies.
No tie at tenth. Official Chicago GP matches tracking GP throughout all 13 seasons.

eFG% = 50 × pull-up PTS / FGA. League baseline uses pooled player-level PTS and FGA,
not an average of percentages. Relative eFG subtracts that season's league baseline.
For the 3-point slide, 3P% = FG3M / FG3A and relative 3P% subtracts the pooled league
pull-up 3P% baseline. PTS/G and FGA/G use all official Chicago appearances. Points
exclude free throws.

## Source limitation

The selected source is `LeagueDashPtStats`, Player / PullUpShot / Totals. Earlier
zero-filled seasons are unavailable, not zero shooting. `ShotChartDetail` labels are
not interchangeable. Team/player discrepancies are preserved, not forced to match:
2013–14 through 2017–18 differ on FGA despite equal FGM/PTS; 2024–25 differs on all three.
The alternate `LeagueDashPlayerPtShot` dashboard also differs in 2024–25, including Coby
White. Its response and audit are in `data/raw/alternate_pullups_2024-25*.json`.
The cause is unresolved. These are source-specific design-review drafts, not a claim
that NBA's multiple shooting surfaces have been reconciled.

Transparent 300-DPI assets belong in `assets/`; warm-background 1080px review previews
are provided only to compare legibility. The carousel was posted on 2026-09-10 at
https://www.instagram.com/p/DdHst7hlsAE/?img_index=1.
