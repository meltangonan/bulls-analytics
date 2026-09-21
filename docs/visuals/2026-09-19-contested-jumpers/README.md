# Bulls contested jumpers

Top fifteen Bulls regular seasons since 2013-14 by contested jumpers made. The red bar
carries the makes; the support columns carry that season's NBA rank in makes, contested
FG% with its difference from the league average, and uncontested FG% as the comparison.
Reuses the and-1 table-bar layout with three support columns.
Notion: https://www.notion.so/3e0e1c13abe681a6818bea0050b9acd2

## Build

```bash
python scripts/prototypes/contested_jumpers_data.py   # fetch or reuse raw, reconcile, select
python scripts/prototypes/contested_jumpers_table.py --final
```

`--refresh` re-fetches instead of reusing the saved responses in `data/raw/`.

## Source and method

NBA.com player tracking, `https://stats.nba.com/stats/leaguedashplayerptshot` through
`nba_api` `LeagueDashPlayerPtShot`: regular season, totals, `shot_dist_range_nullable=>=10.0`,
one call per closest-defender bucket per season, once with `team_id_nullable=1610612741`
(Chicago games only) and once without a team filter (the league pool). Each raw file stores
its parameters and capture time. One raw row is one player's makes and attempts in one bucket
for one season.

- A **jumper** is a field-goal attempt from 10+ feet. The filter keeps rim attempts out:
  across all shots, tightly guarded attempts convert better than wide-open ones because
  most of them are layups.
- **Contested** = closest defender 0-4 ft at release (`Very Tight` + `Tight`).
  **Uncontested** = 4+ ft (`Open` + `Wide Open`). A player absent from a bucket took no
  shots in it.
- **League average** = all league contested makes / attempts that season (34.5% to 36.3%).
- **NBA rank** ranks each player's full-season contested makes in the league pool; ties
  share a rank. No selected row belongs to a traded player (`partial_season` is false for all
  fifteen), so each Chicago row equals that player's league row.
- **Selection**: most contested makes; a tie goes to the higher contested FG%, then the
  older season. Butler 2014-15 (35.9%) sits above Boozer 2013-14 (35.1%) at 65; Gibson and
  Brooks tie at 57. The fifteenth row (54) is clear of the sixteenth (51).

Worked example: DeMar DeRozan 2021-22, Very Tight 5/14 plus Tight 306/622 = 311/636
(48.9%); Open 190/408 plus Wide Open 34/79 = 224/487 (46.0%). The 2021-22 league made
9,143 of 26,090 contested jumpers (35.0%), so he was +13.9. Nearly all of anyone's contested
attempts sit in the Tight bucket.

`all_player_seasons.csv` holds all 248 Chicago player-seasons; `top15.csv` is the chart
selection; `season_audit.csv` records the league pool and the reconciliation below.

## Reconciliation

Chicago's player rows are summed against `TeamDashPtShots` (`ClosestDefender10ftPlusShooting`),
an independent team total of the same shots. Every season agrees within two makes or
attempts; 2020-21 to 2022-23 and 2025-26 agree exactly. Differences are recorded, never
forced away, and a gap above five shots (or 1%) stops the build.

## Qualifications the page must carry

- **Window**: 2013-14 through 2025-26 regular seasons. Defender-distance tracking starts in
  2013-14, so no earlier season is available from any NBA.com source.
- **Definitions**: 10+ ft field-goal attempts; contested means the closest defender within
  4 ft at release. Distance at release is a snapshot and does not measure a contest's quality.

## Tracing one shot to its bucket

`LeagueDashPlayerPtShot` also accepts `date_from_nullable`/`date_to_nullable`, `period_nullable` and
`shot_clock_range_nullable`, so a single identifiable shot can be traced to a defender-distance
bucket when the filters isolate it. `ShotChartDetail` supplies the shot log used to prove the slice
holds exactly one attempt. Two checks on DeRozan's consecutive 2021-22 buzzer-beaters, each the only
three he attempted in that fourth quarter:

| Game | Shot | Slice (date + period 4) | Bucket |
| --- | --- | --- | --- |
| 2021-12-31 at IND | 27 ft pull-up 3 at 0:00 | FG3M/FG3A 1/1 in `6+ Feet - Wide Open` | not contested |
| 2022-01-01 vs WAS | 23 ft pull-up 3 at 0:00 | FG3M/FG3A 1/1 in `2-4 Feet - Tight` | contested |

The famous Indiana game-winner is therefore **not** among the 311. Do not use it as an illustration
of this post's metric.

Reconciliation of the same two games: at IND the shot log's 10+ ft attempts match the tracking
buckets exactly (15 attempts, 6 makes). At WAS the shot log has 17 attempts and 8 makes against
tracking's 15 and 7, because `SHOT_DISTANCE` is a rounded integer and tracking measures continuously,
so shots logged at 10 or 11 ft can fall below tracking's 10 ft line. Match on counts within a slice,
never assume the two pools are identical.
