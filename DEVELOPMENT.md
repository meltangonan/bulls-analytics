# Development Reference

Read this before changing data fetchers, analysis code, graphics builders, scripts, or tests. For
post-production procedure, read `POSTING_WORKFLOW.md`; for visual decisions, read `DESIGN.md` before
building a graphic.

## Project Structure

```text
STRATEGY.md                 # Account purpose, audience, metrics, and work tracks
DESIGN.md                   # Palette, type, layout, annotation grammar, and brand status
POSTING_WORKFLOW.md         # Visual-post gates and catalog-to-post workflow
bulls-content-playbook.html # Editorial north star and fairness guardrails
idea-catalog.html           # One card per post idea
bulls/
  config.py                 # Team ID, season strings, colors, and API delay
  data/fetch.py             # NBA API wrappers
  analysis/stats.py         # Statistical functions
  graphics/feed.py          # Legacy zone-post builders
  graphics/craft.py         # Shared F5-derived helpers
scripts/                    # Reusable CLIs and one-off prototypes
  prototypes/               # One script per idea batch
docs/
  mocks/                    # Committed copies of catalog images
  handoffs/                 # Temporary cross-session notes; compact when closed
  ideation/                 # Ideation artifacts
  reference/                # Tutorials, inspiration, and craft notes
  archive/                  # Superseded plans and references
assets/fonts/                # Academic M54, Archivo, and legacy font files
assets/img/                  # Committed one-off image assets
cache/headshots/             # Downloaded NBA CDN headshots
tests/                       # Pytest suite; NBA API calls mocked
output/feed/                 # Generated PNGs; gitignored
```

## Key APIs

### `bulls.data`

- `get_team_shots(last_n_games=)` — all team shot-chart data
- `get_game_shots(game_id)` — one game's team shots, any league; derives `league_id` from the
  game-ID prefix via `league_for_game` (`00` NBA, `15` Summer League), so Summer League works
- `get_roster()` — current roster; use it to filter traded players
- `get_games(last_n=)`, `get_latest_game()`, `get_box_score(game_id)`
- `get_player_games(player_name, last_n=)`, `get_player_shots(player_id)`
- `get_league_shots(season=)` — all 30 teams; slow, about 30 API calls
- `get_lineup_stats(min_minutes=)` — Bulls two-player lineup ratings
- `get_roster_efficiency(last_n_games=, min_fga=)`
- `get_player_headshot(player_id)` — downloads and caches NBA CDN headshots

### `bulls.analysis`

- `detailed_zones(team_shots)` — six basic zones to 12 granular zones
- `zone_leaders(team_shots, min_shots=)` — PPG leader per zone
- `zone_leaders_by_frequency(team_shots, min_shots=)` — FGA/game leader per zone
- `zone_volume_leaders(team_shots, min_shots=)` — top-volume shooter per zone
- `points_per_shot(team_shots, by_zone=)` — overall and per-zone PPS
- `league_pps_by_zone(league_shots)`, `high_value_zone_usage(league_shots)`
- `season_averages()`, `efficiency_metrics()`, `scoring_trend()`, `rolling_averages()`

### `bulls.graphics`

- `build_zone_leaders_post(team_shots, ...)` — PPG court map
- `build_zone_frequency_post(team_shots, ...)` — frequency court map
- `build_zone_pps_post(team_shots, ...)` — PPS bar chart
- `build_zone_team_stats_post(team_shots, ...)` — team zone shooting court map
- `build_zone_volume_leaders_post(team_shots, ...)` — volume-leader court map
- `save_feed_post(fig, output_path)` — saves at 150 DPI; pass `dpi=300` for final prototypes
- `craft.gradient_bar`, `stacked_label`, `threshold_footer`, `headshot_label` — shared helpers;
  `threshold_footer` shows qualification, coverage, and source

## Development Conventions

- Keep reusable fetching and analysis logic in `bulls/data` and `bulls/analysis`.
- Keep reusable graphics builders in `bulls/graphics`; keep entry points in `scripts/`.
- Start new formats as one script per idea batch in `scripts/prototypes/`; promote a builder to a
  reusable graphics module and CLI only after it repeats.
- Add the new card at the top of `idea-catalog.html`, then copy its image to `docs/mocks/` so the
  catalog remains portable. `output/` is gitignored.
- Extract helpers only after the same logic appears in 2–3 prototypes. Prefer small, test-backed
  changes; do not add automation, export pipelines, or heavy frameworks unless requested.

## Data and Graphics Guardrails

- `ShotChartDetail` filters by `league_id` server-side and defaults to the regular NBA, so it
  silently returns zero rows for Summer League games. Use `get_game_shots`, which derives the
  league from the game ID, instead of calling the endpoint directly. Prefer the NBA's own
  `shot_zone` labels over re-deriving zones from distance or coordinates.
- Summer League's traditional box score may finalize hours before its shot-chart and advanced-box
  feeds. `summer_league_report.py` treats empty or all-zero derived feeds as unavailable instead of
  printing false values; use its review pass and expect a morning-after render when NBA.com lags.
- Shot-chart data includes everyone who took a Bulls shot that season, including traded players.
  Use `get_roster()` and player IDs to create a current-roster view when relevant, and show both
  all-player and current-roster views for a fair comparison.
- Set `min_shots` by timeframe: about 30 for a season and 10 for a recent-games view.
- Standard output is 1080×1350 at 150 DPI. New prototypes should export 2160×2700 at 300 DPI for
  Instagram compression; use 150 DPI only for fast draft iteration.
- Table posts use `plottable` (see `scripts/prototypes/f5_lineup_table.py`) or Great Tables when
  the table engine should own row rhythm, image cells, and a single color-emphasized column —
  `summer_league_report.py` renders its player table with Great Tables to a cropped PNG and
  composites it into the matplotlib canvas (`gtsave` needs a headless browser). `gt_extras` stays
  environment-only; only the spike script uses it. Craft patterns and source links are in
  `docs/reference/f5-technique-notes.html`.
- `DESIGN.md` owns typography. `Playfair Display` and `DM Sans` remain only in legacy
  `bulls/graphics/feed.py` zone builders.
- Court graphics use `analysis.detailed_zones()`; headshots are cached in `cache/headshots/`.
- Name outputs `YYYY-MM-DD-zone-{mode}-{scope}.png` in `output/feed/`.

Useful CLIs:

```bash
venv/bin/python scripts/make_zone_leaders.py --mode ppg|frequency [--last-n-games N]
venv/bin/python scripts/make_zone_shooting.py --mode team|volume [--last-n-games N] [--min-shots N]
venv/bin/python scripts/make_feed_post.py --post-type zone-pps [--last-n-games N]
```

## Tests

Run the project suite with `./run_tests.sh` or `venv/bin/python -m pytest tests/ -v`.
`test_data.py`, `test_analysis.py`, `test_graphics.py`, and `test_config.py` mock all NBA API calls.
