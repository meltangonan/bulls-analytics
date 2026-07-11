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
| `summer_league_report.py` | Summer League Report — run bare to auto-resolve the latest completed Bulls SL game, then re-run with `--carousel --player …` (the game-night format: team front page with an embedded Great Tables player comparison + one C2-structure slide per player) or 1–3 `--player`/`--lens` pairs for the legacy single image (needs network; refuses in-progress games) |
| `summer_league_anatomy_wireframes.py` | Structure study only — the A/B/C/C2/D wireframes behind `docs/ideation/summer-league-anatomy-study.html`; not a posting format |
| `summer_league_great_tables_spike.py` | Great Tables / gt-extras feasibility spike behind the anatomy study; the production table now lives in `summer_league_report.py` |

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

### Summer League Report quick start

Run `summer_league_report.py` with no arguments to resolve the latest completed Bulls Summer League
game and print the review table. After choosing the players with the user, render the carousel with
NBA.com spellings from that table:

```bash
venv/bin/python scripts/prototypes/summer_league_report.py
venv/bin/python scripts/prototypes/summer_league_report.py --carousel \
  --player "<Name>" [--player "<Name>" ...]
```

Use `--final` only after draft approval. The script refuses in-progress games, treats lagging shot
and advanced feeds as unavailable, and automatically prints the 2026 one-free-throw TS% disclosure.
On game night, NBA.com's derived feeds may not populate until morning.

After keeping a mock, copy its PNG into `docs/mocks/` and add a catalog card
(template in `idea-catalog.html` source).
