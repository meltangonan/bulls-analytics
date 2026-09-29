# Bulls single-season points off turnovers leaders

Top fifteen Bulls player-seasons by points off turnovers from 1996-97 through 2025-26, in the
fast break points table layout: the red bar carries the season total; support
columns show its NBA rank, per game and the share of the player's points.

Notion: https://www.notion.so/3eae1c13abe681369592d4fb567a5f54

## Build

```bash
python scripts/prototypes/points_off_turnovers_data.py
python scripts/prototypes/points_off_turnovers_table.py --final
```

Use `--refresh` on the data command to replace the saved NBA responses.

## Source and selection

NBA.com `LeagueDashPlayerStats`, regular season, totals. Per season: a
Chicago-filtered `Misc` call (`PTS_OFF_TOV`), a Chicago-filtered `Base` call (`PTS`), a Chicago-filtered `Scoring` call (`PCT_PTS_OFF_TOV`, check only),
and an unfiltered `Misc` call for the league population. Misc and Scoring
responses are the same requests the fast break points post captured on
2026-09-29 and were copied from it. The series begins in 1996-97; earlier
seasons return no rows, so they are unavailable, not zero.

Share of points is `PTS_OFF_TOV / PTS` (Base); it matches NBA.com's published `PCT_PTS_OFF_TOV` within 0.0005 for every displayed row.

Rows are ordered by points off turnovers, then per game, then the older season. The 15th total (256) has no tie outside the table.
NBA rank is competition rank against every player's full-season total;
`data/selection_audit.csv` confirms no displayed player was traded mid-season
and every calculated rank matches NBA.com's.

The bar column starts at 1100 px rather than the fast break board's 1050 so the
widest names on these boards clear it at the approved 41.5 pt.
