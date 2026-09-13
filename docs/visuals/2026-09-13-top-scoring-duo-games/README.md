# Most points by two Bulls in a game

Top fifteen Bulls games since 2000-01 by the combined points of the game's two
highest-scoring Chicago players.

## Build

```bash
python scripts/prototypes/scoring_duo_games_data.py   # selection + audits
python scripts/prototypes/scoring_duo_games_table.py  # chart asset
```

`--refresh` re-requests NBA.com instead of reading the cached season responses.

## Source

NBA.com `PlayerGameLogs` (Chicago player-games) and `LeagueGameFinder` (Bulls
team-games), fetched and reconciled by `scripts/prototypes/top_game_performances.py`
and cached under `cache/nba.com/top-game-performances/`. Regular season only,
2000-01 through 2025-26: 2,089 games across 26 seasons, every season present.

`team_points` is the official team score, not a sum of the player rows, and every
player-game is required to match exactly one Bulls team-game on date, matchup and
result before any selection runs.

## Selection

Each game contributes one duo: its two leading scorers. Rows rank on combined
points, ties broken on the second scorer's points and then game date.

**No both-players qualifier is applied, deliberately.** The two leading scorers
also maximise the lower half of any pair drawn from the same game, and a large
combined total already forces a large second score, so a floor would change
nothing at the top of this list. The audit records the worst case instead: the
lowest second scorer in the fifteen is 22 and the widest gap is 28. Jimmy
Butler's 53-and-17 game ranks 17th and does not appear.

## Qualifications the page must carry

- **Overtime.** Eight of the fifteen went to overtime against 6.7% of all games
  in the period, so extra minutes lift these totals. Each affected row is
  labelled `OT`/`2OT`/`4OT`. Period counts are inferred from the team minute
  budget (240 in regulation, 25 per overtime), not supplied by the source.
  The tag sits in the GAME column as `(OT)` / `(2OT)` / `(4OT)`, in red.
- **Cutoff tie.** Two games finished on 71. The more balanced one (36+35 vs UTA,
  2022-23) takes the fifteenth row; 51+20 at Detroit in 2023-24 is excluded.
- **Shared second place.** At Atlanta in 2018-19, Lauri Markkanen also scored 31.
  The row names Otto Porter Jr. on the minutes tiebreak; either is defensible.
- **Era.** Ten of the fifteen come from 2015-16 onward. League scoring rose over
  the period, so this is partly an era effect rather than only a Bulls one.
- **Regular season only.** No playoff games are included.

## Game column

Date and matchup formatting reuse `_display_date` and `_game_context_parts` from
`top_game_performances.py`, so this table spells a game the same way the
game-score post does: `Mar 17, 2023` over `vs MIN W (2OT)`. The one local change
is a space after `@`, matching the `vs ` the same helper already emits.

## Files

| File | What it holds |
| --- | --- |
| `data/top15.csv` | The fifteen rendered rows |
| `data/all_duo_games.csv` | All 2,089 games, for re-cutting the selection |
| `data/season_audit.csv` | Games seen and best duo total per season |
| `data/selection_audit.csv` | The challengeable facts above, as computed values |
| `data/minutes_reconciliation_exceptions.csv` | Games whose logged minutes miss their period budget |

One known minutes exception: 2003-01-31 at Portland logs 236.9 team minutes
rather than 240. It is a regulation game whose source box score under-reports
about three minutes, and it is far outside the top fifteen.
