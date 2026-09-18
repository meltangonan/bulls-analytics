# Bulls and-1 season leaders

Top Bulls seasons since 1996-97 by and-1s: a made field goal on which the shooter was
fouled and went to the line for one free throw. The red bar carries the total; the support
columns carry that season's NBA rank and and-1s per 100 offensive possessions. Reuses the
pull-up/catch-and-shoot table-bar layout with two support columns instead of three.
Exactly fifteen rows: a tie at the cutoff is broken on and-1s per 100 possessions, so
Luol Deng 2006-07 (0.65) takes the last place from Jalen Rose 2002-03 (0.59).
Notion: https://www.notion.so/3dee1c13abe6813fbb8ced86d77feef2

## Build

```bash
python scripts/prototypes/and_one_leaders_data.py   # count, selection, audits
python scripts/prototypes/and_one_leaders_table.py --final
```

`--refresh` re-fetches instead of reusing saved responses. The first run downloads 2,385
game logs into ignored `cache/nba.com/and-one-pbp/` (~500 MB, roughly 40 minutes); the
tracked artefacts are the per-game count table and the audits, not the raw logs.

## Source and method

and-1s are **counted here** from NBA.com play-by-play (`PlayByPlayV3`), every Chicago
regular-season game, 1996-97 through 2025-26: 2,385 games, 5,077 Chicago and-1s.
NBA.com publishes no season and-1 count in any dashboard, and play-by-play begins in
1996-97 (earlier seasons return empty responses, not errors), which sets the window.

One and-1 is a Chicago `Free Throw 1 of 1` (or `Free Throw Flagrant 1 of 1`) by the same
player, at the same period and clock as his own made field goal, with an opponent foul
logged at that moment. That rule excludes three lookalikes seen in the logs: a technical
free throw after a made basket, an away-from-play foul where a *different* player shoots,
and a one-shot trip with no made field goal.

The flagrant form is included: a made shot, a foul on that shot upgraded on review, and one
free throw. One selected row carries one (DeRozan 2022-23); `and1s_flagrant` records them.
`and1s_made_ft` records how many of the free throws were made, which the post does not use.

`per_100 = 100 × and1s / OffPoss`, where possessions are Chicago offensive possessions with
the player on the floor, from pbpstats. NBA rank comes from Basketball Reference's complete
league play-by-play table, ranking each player's full season across teams; a Chicago-only
count cannot produce a league rank. Tied players share an NBA rank.

Worked example: Michael Jordan 1997-98, 70 and-1s over 5,705 offensive possessions = 1.23
per 100, 3rd in the NBA. Chicago's 82 game logs supply all 70.

`and_ones_by_game.csv` holds every counted and-1 by game and player; `games_counted.csv`
records the games behind each season; `all_player_seasons.csv` holds all 445 Chicago
player-seasons; `top15.csv` is the chart selection, ordered by and-1s then per 100
possessions then the older season, cut at fifteen rows.

## Why not take a provider's column

Both public and-1 columns read the same NBA logs, and both disagree with them, so the count
is made here. `source_audit.csv` compares every Chicago player-season:

| Source | Era | Matched | Exact | Max difference |
| --- | --- | --- | --- | --- |
| Basketball Reference | 1996-97 to 1999-00 | 54 | 52 | 1 |
| Basketball Reference | 2000-01 to 2025-26 | 384 | 364 | 1 |
| pbpstats | 1996-97 to 1999-00 | 54 | 41 | 5 |
| pbpstats | 2000-01 to 2025-26 | 391 | 388 | 2 |

pbpstats is reliable from 2000-01 but misses 19 and-1s across the early seasons, including
**five of Jordan's in 1996-97** (40 against the logs' 45). That is not a stricter definition:
all 45 have a shooting foul logged at the same moment, and 39 of the free throws were made,
so neither a made-free-throw rule nor a missing-foul rule explains it. Basketball Reference
tracks the logs closely in both eras; its known miss is LaVine 2022-23 (51 against 50), an
away-from-play foul that Vučević shot.

`selection_audit.csv` carries both providers' numbers beside every published row.

## Qualifications the page must carry

- **Source and window**: NBA.com play-by-play, 1996-97 through 2025-26 regular seasons.
  Play-by-play does not exist before 1996-97, so Jordan's first three-peat cannot be counted
  from any source. Say "since 1996-97", not "since 2000".
- **Per 100 possessions** uses on-court offensive possessions and is not compared with a
  league average. Basketball Reference's minutes × pace estimate agrees within 0.01.
- **NBA rank** uses Basketball Reference's full-season totals, which differ from the counts
  here by at most one on Chicago rows. Ranks are shown to the reader as approximate standing,
  not a claim about another team's exact total.
- **Shortened seasons** appear in the population (1998-99: 50 games; 2011-12: 66;
  2019-20: 65; 2020-21: 72) but none reaches the table.

## Rejected

- **A three-point and-1 slide** (2026-09-16): too rare to rank. The best Bulls season is five
  (Justin Holiday, 2017-18); a top fifteen would need 24 rows, fifteen tied at two.
  Ben Gordon's three in 2008-09 ranked 2nd in the NBA and remains a caption line.
- **Per-game and games-played columns** (2026-09-16): no selected season came from a
  shortened year, so games added nothing and per game restated the bar.
- **Starting at 2000-01** (2026-09-17): the cautious window cost Jordan's 1997-98, which is
  4th on this list, and his 1996-97, which is 11th.

Elton Brand's portrait is the NBA CDN's only headshot for him and shows a 76ers jersey.

Transparent 300-DPI chart assets and warm-background review previews are in `assets/`.
Canva: https://www.canva.com/design/DAHVfNCTrVw/cOEiUQa2efyGecJ6CiaRRA/edit
The composed page still carries the earlier 2000-01 chart and needs the new asset, a
corrected footer and a corrected window in the cover and subtitle.
