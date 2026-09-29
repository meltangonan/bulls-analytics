# Bulls single-season fast break points leaders

Top fifteen Bulls player-seasons by fast break points from 1996-97 through
2025-26. The red bar carries season fast break points; support columns show that
total's NBA rank, fast break points per game and the share of the player's
points that came on fast breaks.

Notion: https://www.notion.so/3eae1c13abe681f38f52eb34c8e8d4bc

## Build

```bash
python scripts/prototypes/fast_break_points_data.py
python scripts/prototypes/fast_break_points_table.py --final
```

Use `--refresh` on the data command to replace the saved NBA responses.

## Source and selection

NBA.com `LeagueDashPlayerStats`, regular season, totals. Per season: a
Chicago-filtered `Misc` call (`PTS_FB`), a Chicago-filtered `Scoring` call
(`PCT_PTS_FB`, plus overall `FG_PCT` kept but not shown), and an unfiltered
`Misc` call for the league population. `PTS_FB` begins in 1996-97; a 1995-96
request returns no rows, so earlier seasons are unavailable, not zero.

Fast break points are a scorer's flag in the NBA play-by-play, not a tracking or
video measure. NBA.com publishes no fast break FG% for this window, which is why
the table shows share of points rather than a shooting column.

Rows are ordered by fast break points, then per game, then the older season.
The 15th total (220) has no tie outside the table. NBA rank is competition rank
against every player's full-season total; `data/selection_audit.csv` confirms
no displayed player was traded mid-season and every calculated rank matches
NBA.com's. `data/season_audit.csv` records row and point totals per season;
`data/source.json` records the request contract and cutoff audit.

## Portraits

NBA.com returns only a silhouette for Ron Mercer (player id 1500). Source a
portrait before publishing.
