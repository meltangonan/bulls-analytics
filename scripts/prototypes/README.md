# Prototype Mock Generators

One-off scripts behind visual projects tracked in Notion. Production prototypes render
1080x1350 PNGs into `output/` from cached or fetched data; explicitly named spikes may write
additional comparison artifacts there. These are
deliberately prototype-grade — promote a builder into `bulls/graphics` plus a
`scripts/` CLI only once its format repeats.

| Script | Catalog cards |
| --- | --- |
| `bulls_national_tv_history.py` | Bulls national TV games by season — reads the tracked 2010–11 through 2026–27 schedule-release snapshot, validates each total against its included network components, and renders transparent vertical or horizontal bar-chart assets for Canva. The published horizontal treatment orders seasons newest first, keeps historical bars black, and highlights 2026–27 in dark red; no network call is needed because the official Bulls/NBA source files and reconciled CSVs ship with the post. |
| `f5_lineup_table.py` | Bulls Lineup Table — ten most-used 2-man combinations with minutes and off/def/net rating; writes the validated CSV, renders one transparent Canva chart asset, and prints the data-bound page copy (needs network; add `--final` only after draft approval) |
| `summer_league_report.py` | Summer League Report v1 + v2 — run bare to auto-resolve the latest completed Bulls SL game, then re-run with `--carousel --player …` (current v2: team front page with the 35/65 comparison-and-shot-diet panel, shooting splits, and Great Tables player table + one player-focused shot-profile slide per selection) or 1–3 `--player`/`--lens` pairs for the legacy single image (needs network; refuses in-progress games) |
| `summer_league_sticky_stats.py` | 2026 Summer League sticky shot-profile prototype — caches all 94 California, Salt Lake City, and Las Vegas game-level box scores and shot charts, qualifies the all-player pool at 50+ minutes, reconciles shot-detail attempts to official box FGA, then renders one transparent 3PT Attempt Rate-vs-Rim Rate Canva asset for Wilson, Swain, Sellers, and Atwell and prints the authoritative data-bound Canva copy (needs network only on the first run; add `--final` for 2160×2060) |
| `current_roster_darko_landscape.py` | Current Bulls DARKO landscape — refreshes official NBA.com roster membership and full-precision ODPM/DDPM from DARKO on the same run, saves the 16-player validated working table with unavailable rookies left missing, and renders one chart-only Canva asset (needs network; add `--final` only after draft approval) |
| `assisted_buckets.py` | Assisted vs. unassisted buckets — joins the live official Bulls roster to each player's complete 2025-26 NBA.com scoring totals across all teams, qualifies at 100+ FGM, reconciles inferred assisted/unassisted makes to official FGM, writes the full roster audit CSV, and renders one transparent 100% stacked-bar Canva asset with portrait headshots (needs network; add `--final` only after draft approval) |
| `clutch_table.py` | Current Bulls in the clutch — joins the live official roster to complete 2025-26 NBA.com clutch totals across all teams, qualifies at 10+ clutch appearances, validates PTS, MIN, FGM–FGA, FG%, and WIN%, and renders one transparent Basketball University-inspired table asset; FG cell color compares the printed shooting line's FG% with the weighted league clutch average (needs network; add `--final` only after draft approval) |
| `assist_duos.py` + `assist_duos_fetch.py` | Bulls assist duos — which pairs created the most baskets for one another. `assist_duos_fetch.py` caches every assisted Bulls basket since 2000–01 from `PlayByPlayV3` into the post's **tracked** `docs/visuals/<slug>/data/seasons/` (not `cache/`, which is ignored and lost one full 50-minute fetch); strictly serial, since NBA.com throttles concurrent play-by-play hard. `--reconcile` checks each season against official box-score assists *and* every passer's attributed total against his own — currently 26/26 seasons and 476/476 player-seasons exact. `assist_duos.py --mode both` renders three visual projects: `assist-duos` (best connection of every season, newest first, one slide per decade, plus a 2025–26 top-eight slide), `assist-duos-by-decade` (top ten within each decade), and `assist-duos-all-time` (top 15 since 2000 on one board). Bar length is combined assists and the colour break is the split between directions; second column is games played together, since shared minutes do not exist before 2007–08 (needs network only when a season is missing) |
| `current_roster_hex_charts.py` | Current-roster player hex batch — refreshes official NBA.com Bulls membership, joins each player to complete 2025-26 regular-season shots across all teams, qualifies at 250+ FGA, saves a complete roster audit plus each qualifier's raw shots and relative-FG% cell table, and renders one transparent chart asset per qualifier. |
| `current_roster_zone_charts.py` | Current-roster twelve-zone batch — the Bulls team chart first, then the same 250+ FGA roster as the hex batch. Renders `make_shot_chart.py --chart zones` for each subject (colour floor 400 team / 20 player, solved from the band scale; a zone below the floor is hatched — not greyed — and keeps its own colour, with grey reserved for zero attempts), writes each subject's raw shots, the full zone-split table, the possession denominators, and a per-subject summary of rated-vs-grey share for checking before publishing (needs network only when a player or possession cache is missing). |
| `top_game_performances.py` | Top Bulls game performances by decade — caches NBA.com player and team game logs for 2000–01 through 2025–26, reconciles every player-game to the Bulls team score, calculates Hollinger Game Score and single-game TS%, keeps the top ten player-games in each season-defined decade, and renders three transparent table assets for Canva; regular season is the default and `--playoffs` switches the same analysis to postseason games (needs network only when a season cache is missing) |
| `regular_season_gamebook.py` | Four independent regular-season postgame experiments — Game Deciders · Game Fingerprint · Shot Quality vs. Making · Who Drove What? (deterministic rehearsal using the Jul 10 Summer League game plus frozen 2025-26 benchmarks; no live API call) |
| `rim_vs_three_pps_landscape.py` | Rim vs. Three points per shot — one `LeagueDashPlayerShotLocations` call plus Advanced possessions produce both axes on a shared points-per-attempt scale, qualifies the league at 1500+ possessions and 75+ attempts in each zone, highlights the current NBA.com roster (not the season's team field), and renders one transparent scatter plotting the roster as `house.square_headshot_label` faces at the roster-landscape size over a uniform grey league cloud (needs network; add `--final` only after draft approval) |
| `scoring_by_location.py` | Scoring by location — one half court, twelve shot zones, and a face in each. Two slides off the same court: `--mode efficiency` crowns the best points per shot among Bulls with 15%+ of the team's attempts in that zone, `--mode volume` crowns whoever simply shoots it most (no gate — the count is the sample); bare runs write both. Zones are classified from `loc_x`/`loc_y` by the same `zone_of` that draws the outlines, deliberately diverging from NBA's own labels, and every run prints the live agreement rate (needs network on the first run; add `--final` for 300 DPI) |
| `mock_post_demo.py` | A design-preview harness, not a post idea. Renders a full fake post (fictional roster, no network/cache needed) through the real house pipeline so design-system changes can be judged on an actual graphic; also writes a plain-title comparison variant (`-plain.png`, `outlined=False`) |

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
venv/bin/python scripts/prototypes/f5_lineup_table.py
venv/bin/python scripts/prototypes/regular_season_gamebook.py
venv/bin/python scripts/prototypes/payroll_vs_wins.py
```

### Payroll vs wins

`payroll_vs_wins.py` fetches nothing. Salary is not an NBA.com statistic and the sites that compile
it block scripted requests, so it reads the committed snapshot
`docs/visuals/2026-08-08-payroll-vs-wins/data/2026-08-08-bulls-payroll-vs-wins.csv`. Refresh that file once per offseason by repeating the
browser steps in its header comments, then re-run the suite: `tests/test_payroll_vs_wins.py`
re-checks the snapshot against facts the sources publish independently, including a regression guard
for a 2015-16 payroll figure Spotrac still publishes wrong.

### Summer League Report quick start

Run `summer_league_report.py` with no arguments to resolve the latest completed Bulls Summer League
game and print the review table. After choosing the players with the user, render the carousel with
NBA.com spellings from that table. Carousels support up to five featured players; the first-slide
table automatically tightens its headshots, type, and row padding at five rows so it stays clear of
the footer:

```bash
venv/bin/python scripts/prototypes/summer_league_report.py
venv/bin/python scripts/prototypes/summer_league_report.py --carousel \
  --player "<Name>" [--player "<Name>" ...]
```

Use `--final` only after draft approval. The script refuses in-progress games, treats lagging shot
and advanced feeds as unavailable, and notes that point totals reflect the 2026 one-free-throw rule
(the rendered FG% is unaffected by it).
On game night, NBA.com's derived feeds may not populate until morning.

After keeping a visual, save its PNG with `scripts/save_visual_version.py --project <slug>` and keep
the matching Notion page current.
