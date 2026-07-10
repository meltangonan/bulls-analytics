# Prototype Mock Generators

One-off scripts behind the cards in `idea-catalog.html`. Each renders
1080x1350 PNGs into `output/feed/` from cached season data. These are
deliberately prototype-grade — promote a builder into `bulls/graphics` plus a
`scripts/` CLI only once its format repeats.

| Script | Catalog cards |
| --- | --- |
| `impact_board.py` | Most Impactful Bulls |
| `three_options.py` | Impact vs. Availability · The Season, Month by Month · The Shape of the Season · The Shape of the Record |
| `f5_leaderboard.py` | F5 Leaderboard — Bulls Scoring Leaders (exports at 300 DPI / 2160x2700; change `STAT_COL` + labels for new topics) |
| `f5_lineup_table.py` | Bulls Lineup Table — 2-man combos by net rating (needs network for lineup data; 300 DPI) |
| `summer_league_report.py` | Summer League Report — post-game player cards; run bare to auto-resolve the latest completed Bulls SL game, then re-run with `--carousel --player …` (team front page + one slide per player, the chosen game-night format) or 1–3 `--player`/`--lens` pairs for the single image (needs network; refuses in-progress games) |

## Season cache

Scripts read CSVs from `cache/` (gitignored). Rebuild them with the project venv
(~82 rate-limited API calls, a few minutes):

```python
import pandas as pd
from bulls.data import fetch

games = fetch.get_games(season="2025-26")
games.to_csv("cache/games_2025-26.csv", index=False)

frames = []
for gid in games["GAME_ID"].unique():
    b = fetch.get_box_score(gid)
    if not b.empty:
        b["game_id"] = gid
        frames.append(b)
pd.concat(frames, ignore_index=True).to_csv("cache/box_scores_2025-26.csv", index=False)

fetch.get_roster().to_csv("cache/roster_2025-26.csv", index=False)
```

## Run

```bash
venv/bin/python scripts/prototypes/impact_board.py
venv/bin/python scripts/prototypes/three_options.py
venv/bin/python scripts/prototypes/f5_leaderboard.py
venv/bin/python scripts/prototypes/f5_lineup_table.py
```

After keeping a mock, copy its PNG into `docs/mocks/` and add a catalog card
(template in `idea-catalog.html` source).
