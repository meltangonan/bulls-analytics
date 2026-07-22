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
  graphics/house.py         # Current canvas, fonts, header/footer, tokens, export contract
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

- `house.new_canvas`, `draw_header`, `draw_footer`, `save_post` — executable current-design
  foundation; `DESIGN.md` remains the human-readable owner of the decisions. Each draw
  function takes an optional `theme=` (a `house.THEMES` name: `jersey` default, `white`,
  `newsprint`, `blackout`, `hardwood`); themed posts should pull chart colors from the `Theme` tokens
  (`theme.ink`, `theme.accent`, `theme.grid`, …) instead of the white-canvas module constants
- `build_zone_leaders_post(team_shots, ...)` — PPG court map
- `build_zone_frequency_post(team_shots, ...)` — frequency court map
- `build_zone_pps_post(team_shots, ...)` — PPS bar chart
- `build_zone_team_stats_post(team_shots, ...)` — team zone shooting court map
- `build_zone_volume_leaders_post(team_shots, ...)` — volume-leader court map
- `save_feed_post(fig, output_path)` — legacy save API retained for older builders
- `craft.gradient_bar`, `stacked_label`, `threshold_footer`, `headshot_label` — shared helpers;
  `threshold_footer` shows qualification, coverage, and source

## Development Conventions

- Keep reusable fetching and analysis logic in `bulls/data` and `bulls/analysis`.
- Keep reusable graphics builders in `bulls/graphics`; keep entry points in `scripts/`.
- Use `bulls.graphics.house` for the current Python-composed canvas, fonts, header/footer, tokens,
  and export behavior. For Canva-composed posts, generate verified chart/data assets in Python and
  mirror the canonical `DESIGN.md` tokens in Canva; do not rebuild analytical logic or invent a
  separate visual system in the external layout tool.
- For a format that fetches substantial raw data, prepare display-ready content before drawing it:
  calculations, editorial selections, labels, images, and shot marks belong in a preparation step;
  the renderer should receive that prepared object instead of understanding NBA API columns. Keep
  the prepared shape format-specific rather than inventing a universal post schema.
- Start new formats as one script per idea batch in `scripts/prototypes/`; promote a builder to a
  reusable graphics module and CLI only after it repeats.
- Add the new card at the top of `idea-catalog.html`, then copy the approved final page or carousel
  pages to `docs/mocks/` so the catalog remains portable. For Canva work, preserve the downloaded
  1080×1350 pages, not only the Python chart asset. `output/` is gitignored and is disposable only
  after approved manual artifacts have been promoted to `docs/mocks/`.
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
- Python full-layout drafts use a 1080×1350 logical canvas at 150 DPI; approved posts export
  2160×2700 at 300 DPI for Instagram compression through `house.save_post(..., final=False|True)`.
  Canva-composed posts use sufficiently large Python assets for their placed size, then export the
  complete final page at exactly 1080×1350. DPI metadata does not make Canva-rendered text sharper;
  inspect the downloaded page at feed size. Retain `save_feed_post(..., dpi=...)` only for older
  builders until they are reused.
- Table posts use `plottable` (see `scripts/prototypes/f5_lineup_table.py`) or Great Tables when
  the table engine should own row rhythm and image cells. `summer_league_report.py` calls
  `GT.as_raw_html()`, embeds the local Archivo fonts, renders the HTML through `nokap.from_html`,
  and composites the cropped PNG into the Matplotlib canvas. This browser-backed step is part of
  the live report path, not the rejected full-slide HTML renderer. `gt_extras` remains limited to
  the separate Great Tables spike. Craft patterns and source links are in
  `docs/reference/f5-technique-notes.html`.
- `DESIGN.md` owns typography. `Playfair Display` and `DM Sans` remain only in legacy
  `bulls/graphics/feed.py` zone builders.
- Court graphics use `analysis.detailed_zones()`; headshots are cached in `cache/headshots/`.
  Treat NBA response caches, reconciled analysis caches, and locally extracted font caches as
  expensive reusable inputs, not generic cleanup targets.
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
`test_design_tokens.py` is the token drift alarm: it fails when the hex values documented in
`DESIGN.md`, `design-system.html`, or `bulls/config.py` stop matching `bulls/graphics/house.py`.
When a palette decision changes, update `house.py` and the docs together; the test enforces the
"keep both in sync" rule so it never depends on memory.
