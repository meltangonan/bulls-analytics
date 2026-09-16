# Taj Gibson, Bulls career

A retirement retro. Gibson announced his retirement on September 14, 2026 after
17 seasons and is joining the Bulls staff as an assistant coach. The post covers
only his eight Chicago seasons, 2009-10 through the February 2017 trade to
Oklahoma City.

Five Canva pages from nine assets: per-game season splits (regular season and
playoffs), all-time franchise ranks, career highs, milestone frequencies, top
five games by Game Score, shot diet, and one tenure zone chart.

## Build

```bash
python scripts/prototypes/taj_gibson_retirement_data.py    # six verified CSVs
python scripts/prototypes/taj_gibson_retirement_tables.py  # eight table assets
python scripts/prototypes/taj_gibson_bulls_zone_charts.py  # zone chart + shot diet
```

`--refresh` re-requests NBA.com instead of reading the cached responses;
`--refresh-league` refetches the league shot baseline, roughly 30 requests per
season. `--final` renders at publish resolution.

## Source

Every figure is NBA.com. No Basketball Reference data is used anywhere in this
post.

| Endpoint | What it supplies |
| --- | --- |
| `FranchisePlayers` | All-time Bulls totals, for the rank pools |
| `PlayerCareerStats` | Per-game season splits |
| `PlayerGameLogs` (cached) | Game-level rows for highs, milestones, Game Score |
| `LeagueDashPlayerStats` | Per-season Chicago totals, to reconcile shot counts |
| `ShotChartDetail` | Shot locations and `ACTION_TYPE` for the diet |
| `bulls.data.shots.league_shots` | Pooled league baseline for the zone chart |

`_reconcile()` cross-checks three independent paths against the same four
totals before anything renders: GP 562, PTS 5,280, REB 3,586, BLK 695. The zone
chart independently verifies 4,408 tenure field-goal attempts.

## Scope and qualifications

These shipped as on-asset footnotes. The user cropped them out during Canva
assembly, so the published caption carries them instead.

- **Rank pools are not all one size.** Overall ranks draw on 439 Bulls. Blocks,
  steals, and the offensive/defensive rebound splits draw on the 401 with those
  stats recorded, because the NBA did not track them before 1973-74. A "6th in
  offensive rebounds" is 6th in the tracked era, not in franchise history.
- **Red is a legend, not decoration.** On the rank board red rows are top-10
  finishes: offensive rebounds (6th), blocks (5th), defensive rebounds (10th),
  games played (10th). On the season tables red marks a career best for that
  column.
- **Career highs pool both season types.** The 32-point high came in Game 4 of
  the 2014 first round at Washington; his regular-season high was 26.
- **Milestone denominators are regular season only**, 562 games. The Game Score
  table does include playoffs, labelled `(RD n GMn)`.
- **"Standard jumpers" is a residual bucket.** `Jump Shot` is NBA.com's
  unlabelled default rather than a recorded technique, so the largest family in
  the shot diet, 43.5%, is not a measured shot type. It is kept because dropping
  it would misstate every other share. FG% shows only at 20+ attempts.
- **509 league baseline rows carry no shot zone** across the eight seasons,
  0.03%, and are dropped from the baseline rather than placed by coordinate. All
  4,408 of Gibson's own attempts are labelled.

## Game Score

Hollinger: `PTS + 0.4 FGM - 0.7 FGA - 0.4(FTA-FTM) + 0.7 OREB + 0.3 DREB + STL
+ 0.7 AST + 0.7 BLK - 0.4 PF - TOV`. His best is the 2014 playoff loss at
Washington, 32 points on 13-of-16, Game Score 27.5.

## Files

| File | What it holds |
| --- | --- |
| `data/season-regular.csv`, `data/season-playoffs.csv` | Per-game splits, career row flagged `is_career` |
| `data/franchise-ranks.csv` | 12 categories with total, rank, pool, and `partial_coverage` |
| `data/career-highs.csv` | 8 highs with occurrence count and `in_playoffs` |
| `data/milestones.csv` | 9 frequencies out of 562 |
| `data/top-games.csv` | Top 5 by Game Score, both season types |
| `data/shot-diet.csv` | 10 shot families with share, FG%, and `rated` |
| `data/zone-splits.csv` | Tenure 12-zone splits against the league baseline |
| `data/<season>-*.csv` | Per-season shot and total snapshots behind the above |

`assets/` keeps one render per distinct chart form. The eight shipped assets are
`v16`; the zone chart is `v15`. Earlier versions at `v14` and below are rejected
alternatives retained as direction evidence: the pill cards, the dot-plot rank
board, the striped-red rank table, the pie and 100% bar shot diets, and the two
earlier Game Score forms.
