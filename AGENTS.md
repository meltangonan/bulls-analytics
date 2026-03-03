# AGENTS.md

Guidance for Codex and other coding agents working in this repo.

## Project Intent
- Bulls analytics workspace for notebook-driven exploration plus social graphics generation.
- Primary outputs: analysis in Jupyter notebooks and 1080x1350 Instagram graphics.

## Non-Goals (Unless User Asks)
- No scheduled automation workflows.
- No heavy export pipelines.
- No heavy framework additions.

## Engineering Rules
1. Keep it simple; avoid over-engineering.
2. Prioritize reusable analysis helpers over presentation helpers.
3. Keep notebooks concise: headings + one-liner context.
4. Extract helper functions only when notebook logic repeats 2-3 times.
5. Prefer small, test-backed changes.
6. Use one notebook per idea with consistent section structure.
7. Before building any visual/graphic, run the Clarification Gate below.

## Repo Conventions
- `bulls/config.py`: Team ID, season strings, colors, API delay
- `bulls/data/fetch.py`: NBA API wrappers (shots, games, box scores, roster)
- `bulls/analysis/stats.py`: Statistical functions (zone leaders, PPS, efficiency, trends)
- `bulls/graphics/feed.py`: Single-image social graphics builders (1080x1350 Instagram)
- `bulls/viz/charts.py`: Matplotlib chart helpers for notebooks
- `scripts/`: CLI entrypoints for generating graphics
- `notebooks/active/`: Current idea notebooks (`YYYY-MM-DD-topic-slug.ipynb`)
- `notebooks/archive/`: Frozen/older notebooks
- `notebooks/templates/`: Starter notebooks
- `notebooks/INDEX.md`: Notebook catalog + workflow rules
- `assets/fonts/`: Playfair Display + DM Sans for graphics
- `output/feed/`: Generated PNG graphics
- `cache/headshots/`: Player headshot PNGs from NBA CDN
- `tests/`: 112 unit tests with mocked API calls

## Traded Players
The NBA shot chart API returns all shots taken in a Bulls uniform this season, including traded players (e.g. Nikola Vucevic, Coby White, Ayo Dosunmu).

Pattern for handling this:
- Use `data.get_roster()` to fetch the current roster from the NBA API.
- Filter shot data by `player_id` to get current-roster-only views.
- Notebooks and graphics should show **both views** (all players + current roster) so the user can compare.
- `min_shots` thresholds scale by timeframe: ~30 for full season, ~10 for last-N games.

## Graphics Generation
- Format: 1080x1350 PNG (Instagram portrait 4:5) at 150 DPI.
- Fonts: Playfair Display (titles), DM Sans (body) from `assets/fonts/`.
- Court-based graphics use `analysis.detailed_zones()` for 12-zone breakdown.
- Headshots auto-download from NBA CDN and cache in `cache/headshots/`.
- Output naming: `output/feed/YYYY-MM-DD-zone-{mode}-{scope}.png`.
- Available builders: `build_zone_leaders_post()`, `build_zone_frequency_post()`, `build_zone_pps_post()`.
- CLI: `venv/bin/python scripts/make_zone_leaders.py --mode ppg|frequency [--last-n-games N]`.

## Clarification Gate (Required for Visual Requests)
- Ask focused clarification questions before implementation.
- Ask one question at a time when possible.
- Do not generate final visuals until all required fields below are clear.
- If the runtime supports AskUserTool, use it; otherwise ask directly in chat.

Required fields:
- `insight_goal`: What the visual should prove.
- `scope`: Team/player and season vs last N games.
- `visual_type`: Chart/card type.
- `style_direction`: Visual direction (clean, bold, editorial, etc.).
- `output_text`: Exact title/subtitle/footnote copy.

Defaults (if user says "pick for me"):
- `size`: 1080x1350 (Instagram feed portrait)
- `format`: PNG

After clarifying:
- Re-state the agreed brief in 3-6 bullet points.
- Then implement data/analysis changes, add tests, and generate the image.

## Validation
Run before finishing:

```bash
./run_tests.sh
```

## Documentation Sync
If behavior changes, update:
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
