# CLAUDE.md

Guidance for AI edits in this repository.

## Scope
Bulls analysis with notebook exploration plus lightweight social graphics generation.

## Priorities
1. Keep solutions simple.
2. Favor analysis quality over presentation polish.
3. Avoid adding automation/pipelines unless explicitly requested.

## Project Structure

```
bulls/
  config.py          # Team ID, season strings, colors, API delay
  data/fetch.py      # NBA API wrappers (shots, games, box scores, roster)
  analysis/stats.py  # Statistical functions (zone leaders, PPS, efficiency, trends)
  graphics/feed.py   # Social image builders (1080x1350 Instagram posts)
  viz/charts.py      # Matplotlib chart helpers (bar, line, shot chart, radar, etc.)
scripts/             # CLI entrypoints for generating graphics
  make_zone_leaders.py   # Zone leaders PPG + frequency graphics
  make_feed_post.py      # General feed post generation
notebooks/
  templates/idea_template.ipynb  # Starting point for new notebooks
  active/                        # Work in progress
  archive/                       # Completed notebooks
  INDEX.md                       # Registry of all notebooks
assets/fonts/        # Playfair Display + DM Sans for graphics
output/feed/         # Generated PNG graphics
tests/               # pytest suite (112 tests)
```

## Key APIs

### `bulls.data`
- `get_team_shots(last_n_games=)` — shot chart data for all players on the team
- `get_roster()` — current roster from NBA API (use to filter out traded players)
- `get_games(last_n=)`, `get_latest_game()`, `get_box_score(game_id)`
- `get_player_games(player_name, last_n=)`, `get_player_shots(player_id)`
- `get_league_shots(season=)` — all 30 teams (slow, ~30 API calls)
- `get_roster_efficiency(last_n_games=, min_fga=)`
- `get_player_headshot(player_id)` — downloads + caches from NBA CDN

### `bulls.analysis`
- `detailed_zones(team_shots)` — expands 6 basic zones into 12 granular zones
- `zone_leaders(team_shots, min_shots=)` — PPG leader per zone
- `zone_leaders_by_frequency(team_shots, min_shots=)` — FGA/game leader per zone
- `points_per_shot(team_shots, by_zone=)` — PPS overall and per zone
- `league_pps_by_zone(league_shots)`, `high_value_zone_usage(league_shots)`
- `season_averages()`, `efficiency_metrics()`, `scoring_trend()`, `rolling_averages()`

### `bulls.graphics`
- `build_zone_leaders_post(team_shots, title=, subtitle=, footnote=, min_shots=)` — PPG court map
- `build_zone_frequency_post(team_shots, ...)` — frequency court map
- `build_zone_pps_post(team_shots, ...)` — horizontal bar chart of PPS by zone
- `save_feed_post(fig, output_path)` — saves to PNG at 150 DPI

## Working Style
- Keep reusable code in `bulls/data`, `bulls/analysis`, and `bulls/viz`.
- Keep social image builders in `bulls/graphics` and CLI entrypoints in `scripts/`.
- Use one notebook per idea in `notebooks/active/` with file name format `YYYY-MM-DD-topic-slug.ipynb`.
- Start new work from `notebooks/templates/idea_template.ipynb`.
- Move completed notebooks to `notebooks/archive/` and keep `notebooks/INDEX.md` updated.
- Keep notebooks concise (short markdown, focused code/plots).
- Do not add large export pipelines by default; keep graphics generation script-based and simple.

## Traded Players
- The NBA shot chart API returns all shots taken in a Bulls uniform, including traded players.
- Use `data.get_roster()` to get the current roster and filter by `player_id` when needed.
- Graphics and notebooks should show both views (all players + current roster) so the user can compare.
- `min_shots` thresholds scale by timeframe: 30 for full season, 10 for last-N games.

## Graphics Generation
- Default format: 1080x1350 PNG (Instagram portrait 4:5).
- Fonts: Playfair Display (titles), DM Sans (body) from `assets/fonts/`.
- Court-based graphics use `detailed_zones()` for 12-zone breakdown.
- Headshots are auto-downloaded from the NBA CDN and cached in `cache/headshots/`.
- Output goes to `output/feed/` with naming: `YYYY-MM-DD-zone-{mode}-{scope}.png`.
- To generate via CLI: `venv/bin/python scripts/make_zone_leaders.py --mode ppg|frequency [--last-n-games N]`.

## Clarification Gate (Visual Requests)
- Before creating a new visual, clarify request details first.
- Ask one focused question at a time.
- If AskUserTool is available in the runtime, use it; otherwise ask directly.
- Do not start implementation until these are clear:
  - insight goal
  - scope/timeframe (team/player, season or last N games)
  - visual type
  - style direction
  - output text (title/subtitle/footnote)
- If user wants defaults: 1080x1350 PNG.

## Tests
- Run tests with the project venv:
  - `./run_tests.sh`
  - or `venv/bin/python -m pytest tests/ -v`
- 112 tests across: `test_data.py`, `test_analysis.py`, `test_viz.py`, `test_graphics.py`, `test_config.py`

## Docs
Update `README.md`, `CLAUDE.md`, and `AGENTS.md` when behavior or workflow changes.
