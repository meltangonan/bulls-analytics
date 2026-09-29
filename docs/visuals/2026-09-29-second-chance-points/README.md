# Bulls single-season second chance points leaders

Top fifteen Bulls player-seasons by second chance points from 1996-97 through 2025-26, in the
fast break points table layout: the red bar carries the season total; support
columns show its NBA rank, per game and the share of the player's points.

Notion: https://www.notion.so/3eae1c13abe681fb9d4ad15ac32b2013

## Build

```bash
python scripts/prototypes/second_chance_points_data.py
python scripts/prototypes/second_chance_points_table.py --final
```

Use `--refresh` on the data command to replace the saved NBA responses.

## Source and selection

NBA.com `LeagueDashPlayerStats`, regular season, totals. Per season: a
Chicago-filtered `Misc` call (`PTS_2ND_CHANCE`), a Chicago-filtered `Base` call (`PTS`),
and an unfiltered `Misc` call for the league population. Misc and Scoring
responses are the same requests the fast break points post captured on
2026-09-29 and were copied from it. The series begins in 1996-97; earlier
seasons return no rows, so they are unavailable, not zero.

Share of points is `PTS_2ND_CHANCE / PTS` (Base). NBA.com publishes no share for this stat, so it is derived only.

Rows are ordered by second chance points, then per game, then the older season. The 15th total (203) has no tie outside the table.
NBA rank is competition rank against every player's full-season total;
`data/selection_audit.csv` confirms no displayed player was traded mid-season
and every calculated rank matches NBA.com's.

The bar column starts at 1100 px rather than the fast break board's 1050 so the
widest names on these boards clear it at the approved 41.5 pt.

## Portraits

NBA.com serves a silhouette for Donyell Marshall (923). The user supplied a headshot;
the original is in `data/portraits_source/` (see `SOURCES.md`) and the renderer rebuilds
`data/portraits/923.png` from it.
