# Working Guide

Guidance for AI coding agents (Claude Code, Codex, and others) working in this repository.
This is the single source of truth — `CLAUDE.md` imports it via `@AGENTS.md`, so edit this file
only.

## Scope
Bulls analysis with lightweight social-graphics generation, feeding the `@chicagobullsdata`
Instagram account. Everything runs as scripts — prototype scripts for post mocks, promoted CLIs
for repeating formats. (The old notebook workflow was removed 2026-07-06.)

The account's **strategy** — target problem, audience, key metrics, and the tracks of work — lives
in `STRATEGY.md` at the repo root. Read it for the *why* behind content decisions; this guide is
the *how*.

## Content North Star
- The playbook lives in `bulls-content-playbook.html` (repo root): a "Bulls visual encyclopedia" —
  current, historical, comparative, understandable.
- Common grammar: boards, tables, grids, and shared-scale comparisons. Use the court only when
  location is the actual question.
- Work one post idea at a time: walk it through the clarification gate, mock it, stop.
- Keep qualification thresholds, coverage windows, and sources visible on graphics (fairness
  guardrails in the playbook).

## Priorities
1. Keep solutions simple.
2. Favor analysis quality over presentation polish.
3. Avoid adding automation/pipelines unless explicitly requested.

## Non-Goals (Unless The User Asks)
- No scheduled automation workflows.
- No heavy export pipelines.
- No heavy framework additions.

## Instagram Access
- The user's account is `@chicagobullsdata` ("Chicago Bulls + Data Viz"); they stay logged in on
  Chrome.
- Agents should inspect Instagram in Chrome when the task depends on current saves, the live feed,
  or reference accounts. Use the Chrome/browser capability available in the current runtime: Claude
  may expose Chrome MCP tools (`mcp__claude-in-chrome__*`), while Codex should discover Chrome or
  browser tools with `tool_search` when they are not already visible.
- Treat Instagram access as best-effort and current-session-specific. Use it as a helpful reference
  surface, and avoid presenting old saved-post counts as confirmed-current.
- Useful places to check: the current feed/grid, the saved "Basketball" collection, and reference
  accounts such as Basketball University, Kirk Goldsberry, WNBA Viz Wiz, datakabas, and newer user
  saves that may better match the current direction.
- Read-only use: never post, comment, like, follow, or change settings without explicit per-action
  approval.

## Project Structure

```
STRATEGY.md          # Why the account exists: audience, metrics, tracks (strategy anchor)
bulls-content-playbook.html  # North star: the "Bulls visual encyclopedia" (living doc, revision history at bottom)
idea-catalog.html    # Visual idea catalog: one card per post idea (mock image, status, notes)
bulls/
  config.py          # Team ID, season strings, colors, API delay
  data/fetch.py      # NBA API wrappers (shots, games, box scores, roster, lineups)
  analysis/stats.py  # Statistical functions (zone leaders, PPS, efficiency, trends)
  graphics/feed.py   # Social image builders (1080x1350 Instagram posts)
  graphics/craft.py  # Shared F5-derived helpers (gradient bars, stacked labels, threshold footers, headshot labels)
scripts/             # CLI entrypoints for generating graphics
  make_zone_leaders.py   # Zone leaders PPG + frequency graphics
  make_zone_shooting.py  # Zone shooting stats (team aggregate or volume leaders)
  make_feed_post.py      # General feed post generation
  prototypes/            # One-off mock generators behind idea-catalog cards
docs/
  mocks/             # Committed copies of catalog-referenced mock images (catalog links here as docs/mocks/; output/ gitignored)
  ideation/          # Ideation docs (HTML)
  reference/         # Saved tutorials, inspiration screenshots, F5 technique notes
  archive/           # Superseded planning docs
assets/fonts/        # Academic M54 (titles) + Archivo 400/500/600 (body) + legacy Playfair/DM Sans; Bevan = OFL fallback
assets/img/          # Committed one-off image assets (e.g. Caleb Wilson draft-night crop)
cache/headshots/     # Player headshot PNGs from NBA CDN
output/feed/         # Generated PNG graphics (gitignored)
tests/               # pytest suite (mocked NBA API calls)
```

## Key APIs

### `bulls.data`
- `get_team_shots(last_n_games=)` — shot chart data for all players on the team
- `get_roster()` — current roster from NBA API (use to filter out traded players)
- `get_games(last_n=)`, `get_latest_game()`, `get_box_score(game_id)`
- `get_player_games(player_name, last_n=)`, `get_player_shots(player_id)`
- `get_league_shots(season=)` — all 30 teams (slow, ~30 API calls)
- `get_lineup_stats(min_minutes=)` — Bulls 2-man lineup ratings (Advanced measure: OFF/DEF/NET_RATING)
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
- `save_feed_post(fig, output_path)` — saves to PNG at 150 DPI (pass `dpi=300` for the 2160x2700 export new prototypes use)
- `craft.gradient_bar / stacked_label / threshold_footer / headshot_label` — shared F5-derived helpers; `threshold_footer` renders the fairness guardrails (threshold + coverage + source) on every graphic

## Working Style
- Keep reusable code in `bulls/data` and `bulls/analysis`.
- Keep social image builders in `bulls/graphics` and CLI entrypoints in `scripts/`.
- Post mocks are prototype-script-first (adopted 2026-07-04): one script per idea batch in
  `scripts/prototypes/`, PNGs to `output/feed/`, and a card in `idea-catalog.html` (newest
  first, use the in-file template; statuses: Posted / Mocked / Generated / Parked). Copy each card's
  image into `docs/mocks/` (committed) so the catalog stays portable — `output/` is gitignored.
  Promote a builder into `bulls/graphics` + a `scripts/` CLI only once the format repeats.
- Extract helper functions only when prototype logic repeats 2-3 times.
- Prefer small, test-backed changes.

## Traded Players
- The NBA shot chart API returns all shots taken in a Bulls uniform this season, including traded
  players (e.g. Nikola Vucevic, Coby White, Ayo Dosunmu).
- Use `data.get_roster()` to get the current roster and filter by `player_id` when needed.
- Graphics should show both views (all players + current roster) so the user can compare.
- `min_shots` thresholds scale by timeframe: ~30 for full season, ~10 for last-N games.

## Graphics Generation
- Default format: 1080x1350 PNG (Instagram portrait 4:5) at 150 DPI. New prototypes export at
  300 DPI (2160x2700) so text survives Instagram compression.
- Table-format posts render via `plottable` (matplotlib-native); see
  `scripts/prototypes/f5_lineup_table.py`.
- F5 technique reference (craft patterns + source links): `docs/reference/f5-technique-notes.html`.
- Fonts: see **Design System** below. (Playfair Display + DM Sans remain only in the legacy
  `bulls/graphics/feed.py` zone builders.)
- Court-based graphics use `analysis.detailed_zones()` for the 12-zone breakdown.
- Headshots are auto-downloaded from the NBA CDN and cached in `cache/headshots/`.
- Output goes to `output/feed/` with naming: `YYYY-MM-DD-zone-{mode}-{scope}.png`.
- CLI examples:
  - `venv/bin/python scripts/make_zone_leaders.py --mode ppg|frequency [--last-n-games N]`
  - `venv/bin/python scripts/make_zone_shooting.py --mode team|volume [--last-n-games N] [--min-shots N]`
  - `venv/bin/python scripts/make_feed_post.py --post-type zone-pps [--last-n-games N]`

## Design System (established with the debut post, 2026-07-09)
The account's visual identity, decided with the user over the first shipped post
(`scripts/prototypes/season_shape_post.py` is the reference implementation). Reuse it; don't
re-litigate it per post.

**Type**
- Titles: **Academic M54** (`assets/fonts/AcademicM54.ttf`) — collegiate slab, ALL CAPS,
  auto-fit so left/right margins balance (~60px each side), one accent word in Bulls red.
  ⚠️ License: free for **non-commercial use only**. If the account ever goes commercial,
  license it or swap to `Bevan.ttf` (OFL, kept in `assets/fonts/` as the drop-in fallback).
- Body/labels/annotations: **Archivo** — instanced static weights `Archivo-400/500/600.ttf`.
  matplotlib **ignores the `weight=` kwarg for single-file fonts** (DM Sans was silently
  single-weight for months) — always select the weight by file, not by kwarg. Re-instance
  more weights from the variable font with `fontTools.varLib.instancer` if needed.

**Color**
- Bulls red `#CE1141` for positive/above/accent; rich near-black `#141414` for
  negative/below/heavy fills. Red + black is the team palette — avoid neutral grays for
  *meaningful* areas (gray reads off-brand and flat; grays stay for gridlines/muted text).

**Header pattern**
- Title tight above subtitle; subtitle segments separated by thin light-gray vertical ticks
  (`#CFCFCF`, ~1.3lw) — never "|" or "·" glyphs in rendered text.
- Kicker (red italic) states the metric; if it does, don't repeat the explanation in a footer.
- Footer, every graphic: source credit bottom-left ("Data via NBA.com/Stats" — fairness
  guardrail) and the **watermark bottom-right** ("@chicagobullsdata", muted, ~10.5pt,
  same baseline) so authorship survives reposts/screenshots. Fold both into the shared
  canvas helper when the format is promoted out of prototypes.

**Two visual languages (annotation grammar)**
- *Factual event markers*: gray dashed vertical lines with dated, stacked, muted labels
  (e.g. "TRADE DEADLINE / Feb 5"). Budget: ~1 hero line, at most 1 supporting.
- *Fan-voice callouts*: emotional beats in ink with thin connector lines. Budget: 3-4.
- Every marker/callout must **explain a bend in the data** — if the line doesn't turn there,
  it's trivia; cut it. Alternate emotional beats with factual anchors so it never reads
  as a rant or a spec sheet.
- Faces (headshots) are the highest-stopping-power object: use sparingly, red border ring
  = "the payoff." Position so geometry does the pointing (e.g. line ends at the face).

**Voice**
- Annotations are written "fan in the stands": first-person, wry, a notch above meme-page
  ("5-0 start, we were so back", "Tank for Caleb begins"). Names/context/thesis live in the
  IG caption, not on the graphic. The user writes or heavily owns captions.

## Clarification Gate (Required for Visual Requests)
- Before creating a new visual, clarify the request first.
- Ask one focused question at a time.
- If AskUserTool is available in the runtime, use it; otherwise ask directly in chat.
- Do not start implementation until these fields are clear:
  - `insight_goal`: what the post should prove
  - `scope`: team/player + season or last N games
  - `visual_type`: chart/card style
  - `style_direction`: clean, bold, editorial, etc.
  - `output_text`: exact title/subtitle/footnote copy
- Defaults if the user says "pick for me": 1080x1350 Instagram feed portrait, PNG export.
- After clarifying: re-state the agreed brief in 3-6 bullets, then implement data/analysis changes,
  add tests, and generate the image.

### Refinement Gates (post-draft, before final render — added 2026-07-09)
Once a draft image exists, walk these in order; each is one focused question round:
1. **Voice dial** — how much fan-voice for this post's annotations (sets register for all copy).
2. **Event lines** — which real-world events earn a vertical marker ("explains a bend" test),
   then **source the real dates before drawing** (see fact rule below).
3. **Copy deck** — present every annotation as a before→after table; get redlines or approval.
4. **Title/subtitle** — confirm or tweak.
5. **Caption + hashtags** — draft for the catalog card unless the user writes their own.
6. **Render** — iterate at 150 DPI (fast), export final at 300 DPI (`--final` flag pattern).

**Fact rule:** anything printed on a graphic (dates, picks, trades, injuries) must be verified —
web-search anything past the model's knowledge cutoff; never draw a guessed date. **Image rule:**
NBA CDN headshots for new rookies are often the gray silhouette (~12KB file = silhouette; real
headshots are 50-200KB) — check visually, and fall back to the team's own CDN (nba.com/bulls
article images are clean/unwatermarked); crop square around the face for the circular helper, and
flag wire-photo licensing to the user before using non-NBA sources.

## Session Entry Points (Posting Workflow)
The goal is to post regularly and often. Sessions typically open one of three ways — recognize
which one it is and run the matching flow:

1. **"I want to post X from the catalog."** Pull up the card in `idea-catalog.html` and treat
   it as a pre-filled brief. Run an abbreviated clarification gate: only ask about fields the card
   leaves open (usually exact timeframe and title/subtitle/footnote copy — one question at a time).
   Then refresh data, run or adapt the prototype script, render at 300 DPI, and iterate with the
   user. When they approve it for posting: copy the final PNG to `docs/mocks/`, update the card
   (status → Mocked), and add a copy-paste caption + hashtag block to the card so posting from the
   phone is trivial (the playbook's "Ship-Ready Caption Blocks" thread — its wake condition is any
   post that ships). The user posts manually; never post for them. After they confirm it went up,
   flip the card to Posted.

2. **"I have a new idea / question."** Full clarification gate, then the standard prototype-first
   flow: script in `scripts/prototypes/`, PNG to `output/feed/`, card in the catalog.

3. **"I have no ideas but need to post."** Surface 2-3 concrete candidates, favoring: Parked
   catalog cards whose data is ready today, then the playbook's Guided Idea Bank lanes, then
   anything timely (latest game via `get_latest_game()`, roster news, dates/anniversaries). Present
   them as a short reaction round with a one-line pitch each; the user picks; continue as flow 1
   or 2. Don't invent a new format when a Parked card already covers the idea.

Card status flow: Parked → Mocked → Posted (Generated is legacy, pre-playbook). Whichever entry
point, the per-post rule from the north star still holds: one idea at a time, thresholds and
sources visible on the graphic.

Season rollover: every fetcher defaults to `CURRENT_SEASON` in `bulls/config.py`. When a new
season starts (typically late October), bump `CURRENT_SEASON`/`LAST_SEASON` first — otherwise
"current" posts silently render last season's frozen data.

## Tests
Run with the project venv:
- `./run_tests.sh`
- or `venv/bin/python -m pytest tests/ -v`

Suites: `test_data.py`, `test_analysis.py`, `test_graphics.py`, `test_config.py` — all NBA API
calls are mocked.

## Docs
The repo's three root anchors are `STRATEGY.md` (why — audience, metrics, tracks),
`bulls-content-playbook.html` (visual north star), and `idea-catalog.html` (the idea shelf).
Update `README.md` and this file when behavior or workflow changes. `CLAUDE.md` is a one-line
pointer (`@AGENTS.md`) — don't add content there.
