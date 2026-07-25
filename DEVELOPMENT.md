# Development Reference

Read before changing fetchers, analysis, graphics builders, scripts, or tests. `DESIGN.md` owns
visual decisions; `POSTING_WORKFLOW.md` owns post production.

Code lives in `bulls/data` (NBA API wrappers), `bulls/analysis` (stat functions), and
`bulls/graphics` (`house.py` tokens/themes/fonts, `craft.py` shared helpers, `feed.py` legacy zone
builders). Read the modules for signatures — this file covers only what the code can't tell you.

## Conventions

- Keep reusable fetching and analysis in `bulls/data` and `bulls/analysis`; reusable builders in
  `bulls/graphics`; entry points in `scripts/`.
- Start new formats as one script per idea batch in `scripts/prototypes/`. Promote to a reusable
  module and CLI only after the format repeats. Extract a helper only after the same logic appears
  in 2–3 prototypes.
- **For a format that fetches substantial raw data, prepare display-ready content before drawing.**
  Calculations, editorial selections, labels, images, and shot marks belong in a preparation step;
  the renderer receives that prepared object instead of understanding NBA API columns. This keeps
  analytical truth and visual composition independently testable. Keep the prepared shape
  format-specific — don't invent a universal post schema, and let simple one-off prototypes stay
  direct.
- Never rebuild analytical logic in Canva, and never recompute a number that the chart already
  proved. Canva is layout only.
- Add each new catalog card at the top of `idea-catalog.html`; copy approved final pages to
  `docs/mocks/`. `output/` is gitignored and disposable only after that promotion.
- Name outputs `YYYY-MM-DD-zone-{mode}-{scope}.png` in `output/feed/`.
- Prefer small, test-backed changes. No automation, export pipelines, or heavy frameworks unless
  requested.

## Data Guardrails

These are the traps that produce silently wrong numbers rather than errors.

- **`ShotChartDetail` filters by `league_id` server-side and defaults to the regular NBA**, so it
  returns zero rows for Summer League games without complaining. Use `get_game_shots`, which derives
  the league from the game-ID prefix (`00` NBA, `15` Summer League). Prefer the NBA's own `shot_zone`
  labels over re-deriving zones from distance or coordinates.
- **Summer League's traditional box score can finalize hours before its shot-chart and advanced-box
  feeds.** `summer_league_report.py` treats empty or all-zero derived feeds as unavailable rather
  than printing false values. Expect a morning-after render when NBA.com lags.
- **Shot-chart data includes everyone who took a Bulls shot that season, including traded players.**
  Use `get_roster()` and player IDs for a current-roster view, and show both views when the
  comparison needs to be fair.
- **NBA.com's team-filtered player endpoints can attach a traded player's *later* team abbreviation**
  even while games, minutes, and ratings remain scoped to the team you requested. Treat the request's
  `team_id_nullable` filter as the stint scope; never infer scope from the returned abbreviation.
- **The Advanced endpoint reports minutes per game even when `PerMode=Totals`.** For total player
  minutes paired with advanced ratings, use `get_team_player_advanced_stats()`, which joins
  Traditional totals to the Advanced ratings.
- `get_league_shots()` hits all 30 teams — about 30 API calls, slow.
- Set `min_shots` by timeframe: roughly 30 for a season, 10 for a recent-games view.
- Treat NBA response caches, reconciled analysis caches, and extracted font caches as expensive
  reusable inputs, not cleanup targets. Headshots cache in `cache/headshots/`.

## Graphics Notes

- **New work builds chart assets, not full pages.** Export transparent at a size comfortably larger
  than the placed size; the Canva page supplies the `#FAF8F5` background and all typography. The
  full-layout helpers in `house.py` (`draw_header`, `draw_jersey_stripe`, `draw_footer`, `save_post`)
  are legacy — see `DESIGN.md`.
- Chart text uses `house.helvetica()` / `house.helvetica("bold")`, which extracts the real Bold face
  from the macOS system `Helvetica.ttc` into `cache/fonts/` — matplotlib silently renders regular if
  you ask for bold by family name. The extraction stays in `cache/` so the licensed system font is
  never committed; it falls back to Archivo off macOS.
- Pull chart colors from the `Theme` tokens (`theme.ink`, `theme.accent`, `theme.grid`, …) rather
  than the white-canvas module constants.
- Prototypes should print a Canva copy block of the exact strings to paste, so the page's numbers and
  the chart's numbers come from the same run.
- Building from an F5 or similar tutorial: reproduce its styling and structure closely, swapping in
  our palette and Helvetica (`DESIGN.md` §6).
- `summer_league_report.py` calls `GT.as_raw_html()`, embeds the local Archivo fonts, renders through
  `nokap.from_html`, and composites the cropped PNG into the Matplotlib canvas. **This browser-backed
  step is part of the live report path**, not the rejected full-slide HTML renderer (`DESIGN.md`,
  Settled). `gt_extras` stays limited to the separate Great Tables spike.
- Court graphics use `analysis.detailed_zones()`.
- `save_feed_post(..., dpi=...)` is retained only for older `feed.py` builders.

## CLIs

```bash
venv/bin/python scripts/make_zone_leaders.py --mode ppg|frequency [--last-n-games N]
venv/bin/python scripts/make_zone_shooting.py --mode team|volume [--last-n-games N] [--min-shots N]
venv/bin/python scripts/make_feed_post.py --post-type zone-pps [--last-n-games N]
```

## Tests

```bash
./run_tests.sh
```

All NBA API calls are mocked. `test_design_tokens.py` is the token drift alarm: it fails when hex
values in `DESIGN.md`, `design-system.html`, or `bulls/config.py` stop matching
`bulls/graphics/house.py`. It parses the §2 table rows by token name, so keep that table's format
intact when editing `DESIGN.md`.
