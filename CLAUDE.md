# CLAUDE.md

Guidance for AI edits in this repository.

## Scope
Bulls analysis with notebook exploration plus lightweight social graphics generation, feeding the `@chicagobullsdata` Instagram account.

## Content North Star
- The playbook lives in `docs/bulls-content-playbook.html`: a "Bulls visual encyclopedia" — current, historical, comparative, understandable.
- Default grammar: boards, tables, grids, and shared-scale comparisons (Basketball University style). Use the court only when location is the actual question.
- Work one post idea at a time: walk it through the clarification gate, mock it in a notebook, stop.
- Keep qualification thresholds, coverage windows, and sources visible on graphics (fairness guardrails in the playbook).

## Instagram Access
- The user's account is `@chicagobullsdata` ("Chicago Bulls + Data Viz"); they stay logged in on Chrome.
- Claude can browse it via the Chrome MCP tools (`mcp__claude-in-chrome__*`): check the current feed/grid, the saved "Basketball" collection (curated reference posts the north star doc is built on), and reference accounts (Basketball University, Kirk Goldsberry, WNBA Viz Wiz, datakabas).
- Read-only use: never post, comment, like, follow, or change settings without explicit per-action approval.

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
  make_zone_shooting.py  # Zone shooting stats (team aggregate or volume leaders)
  make_feed_post.py      # General feed post generation
  prototypes/            # One-off mock generators behind idea-catalog cards
notebooks/
  templates/idea_template.ipynb  # Starting point for new notebooks
  active/                        # Work in progress
  archive/                       # Completed notebooks
  INDEX.md                       # Registry of all notebooks
docs/
  idea-catalog.html  # Visual idea catalog: one card per post idea (mock image, status, notes)
  ideation/          # North star + ideation docs (HTML)
  reference/         # Saved tutorials, inspiration screenshots
  archive/           # Superseded planning docs (e.g. pre-north-star CONTENT_IDEAS.md)
assets/fonts/        # Playfair Display + DM Sans for graphics
output/feed/         # Generated PNG graphics (gitignored)
tests/               # pytest suite (120 tests)
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
- `zone_volume_leaders(team_shots, min_shots=)` — highest-FGA shooter per zone (returns FGM, FGA, FG%)
- `points_per_shot(team_shots, by_zone=)` — PPS overall and per zone
- `league_pps_by_zone(league_shots)`, `high_value_zone_usage(league_shots)`
- `season_averages()`, `efficiency_metrics()`, `scoring_trend()`, `rolling_averages()`

### `bulls.graphics`
- `build_zone_leaders_post(team_shots, title=, subtitle=, footnote=, min_shots=)` — PPG court map
- `build_zone_frequency_post(team_shots, ...)` — frequency court map
- `build_zone_pps_post(team_shots, ...)` — horizontal bar chart of PPS by zone
- `build_zone_team_stats_post(team_shots, ...)` — court map with team FGM/FGA + FG% per zone
- `build_zone_volume_leaders_post(team_shots, ...)` — court map with top volume shooter per zone
- `save_feed_post(fig, output_path)` — saves to PNG at 150 DPI

## Working Style
- Keep reusable code in `bulls/data`, `bulls/analysis`, and `bulls/viz`.
- Keep social image builders in `bulls/graphics` and CLI entrypoints in `scripts/`.
- Post mocks are prototype-script-first (adopted 2026-07-04): one script per idea batch in `scripts/prototypes/`, PNGs to `output/feed/`, and a card in `docs/idea-catalog.html` (newest first, use the in-file template; statuses: Posted / Mocked / Generated / Parked). Copy each card's image into `docs/mocks/` (committed) so the catalog stays portable — `output/` is gitignored. Promote a builder into `bulls/graphics` + a `scripts/` CLI only once the format repeats.
- Notebooks are optional — reserve them for analysis whose tables/narrative matter beyond one graphic. When used: one idea per notebook in `notebooks/active/` (`YYYY-MM-DD-topic-slug.ipynb`), start from `notebooks/templates/idea_template.ipynb`, keep them concise, archive when done, keep `notebooks/INDEX.md` updated.
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
- Zone shooting stats: `venv/bin/python scripts/make_zone_shooting.py --mode team|volume [--last-n-games N] [--min-shots N]`.

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
- 120 tests across: `test_data.py`, `test_analysis.py`, `test_viz.py`, `test_graphics.py`, `test_config.py`

## Docs
Update `README.md`, `CLAUDE.md`, and `AGENTS.md` when behavior or workflow changes.
