# Bulls Analytics

Lean Python workspace for Chicago Bulls analysis in Jupyter notebooks.

## What This Repo Is For
- Pull Bulls game and shot data from the NBA API
- Compute reusable analysis metrics in `bulls/analysis`
- Build charts directly in notebooks with `matplotlib`

This repo is intentionally lean: notebook-first for exploration, with a lightweight script-based flow for single-image social graphics.

## Project Layout

```text
bulls-analytics/
├── bulls/
│   ├── data/       # NBA API fetch helpers
│   ├── analysis/   # stat + shot-quality analysis helpers
│   ├── viz/        # matplotlib chart helpers for notebooks
│   └── graphics/   # single-image social graphics builders
├── notebooks/
│   ├── active/     # current idea notebooks
│   ├── archive/    # older/frozen notebooks
│   ├── templates/  # notebook starter templates
│   └── INDEX.md    # notebook catalog + workflow rules
├── scripts/        # CLI entrypoints
├── tests/          # focused unit tests with mocked API calls
└── output/         # optional scratch folder (not part of core workflow)
```

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python test_setup.py
```

## Running Tests

```bash
./run_tests.sh
# or
venv/bin/python -m pytest tests/ -v
```

## Notebook Quick Start

```python
from bulls import data, analysis, viz

games = data.get_games(last_n=10)
team_shots = data.get_team_shots(last_n_games=10)

# Current roster (filters out traded players like Vucevic, Coby, Ayo)
roster = data.get_roster()
roster_ids = set(roster['player_id'].tolist())
current_shots = team_shots[team_shots['player_id'].isin(roster_ids)]

# 12-zone breakdown + zone leaders
detailed = analysis.detailed_zones(team_shots)
leaders = analysis.zone_leaders(detailed, min_shots=5)

pps = analysis.points_per_shot(team_shots, by_zone=True)
fig = viz.shot_chart(team_shots, show_zones=False, title="Bulls Shot Chart")
```

## Notebook Workflow (One Notebook Per Idea)
- New notebook location: `notebooks/active/`
- Name format: `YYYY-MM-DD-topic-slug.ipynb`
- Start from template: `notebooks/templates/idea_template.ipynb`
- Move completed notebooks to: `notebooks/archive/`
- Keep notebook list updated in: `notebooks/INDEX.md`

Notebook section contract:
- `Objective` (one sentence)
- `Data Pull` (imports + fetch only)
- `Analysis` (2-4 focused blocks)
- `Output` (1-2 key charts/tables)
- `Takeaways` (3 bullets)
- `Next Question` (one line)

## Graphics Workflow (Single-Image Feed Posts)
- Build one social image at a time from data + reusable graphics helpers.
- Format: 1080x1350 PNG (Instagram portrait 4:5) at 150 DPI.
- Fonts: Playfair Display (titles) + DM Sans (body) from `assets/fonts/`.
- Headshots auto-downloaded from NBA CDN, cached in `cache/headshots/`.
- Output: `output/feed/YYYY-MM-DD-zone-{mode}-{scope}.png`.

### Available graphics

| Graphic | Builder function | Script |
|---------|-----------------|--------|
| Zone PPS bars | `graphics.build_zone_pps_post()` | `scripts/make_feed_post.py --post-type zone-pps` |
| Zone leaders (PPG) | `graphics.build_zone_leaders_post()` | `scripts/make_zone_leaders.py --mode ppg` |
| Zone leaders (frequency) | `graphics.build_zone_frequency_post()` | `scripts/make_zone_leaders.py --mode frequency` |

### Zone leaders (PPG + frequency)

```bash
# Full season
venv/bin/python scripts/make_zone_leaders.py --mode ppg
venv/bin/python scripts/make_zone_leaders.py --mode frequency

# Last 10 games
venv/bin/python scripts/make_zone_leaders.py --mode ppg --last-n-games 10
venv/bin/python scripts/make_zone_leaders.py --mode frequency --last-n-games 10
```

### Current roster filtering

The NBA shot chart API returns all shots taken in a Bulls uniform, including traded players (Vucevic, Coby White, Ayo Dosunmu, etc.). To generate graphics for the current roster only, filter the shots before passing to the builder:

```python
from bulls import data, graphics

shots = data.get_team_shots()
roster = data.get_roster()
roster_ids = set(roster['player_id'].tolist())
current_shots = shots[shots['player_id'].isin(roster_ids)]

fig = graphics.build_zone_leaders_post(current_shots, ...)
```

### Zone PPS bars

```bash
venv/bin/python scripts/make_feed_post.py --post-type zone-pps
venv/bin/python scripts/make_feed_post.py --post-type zone-pps --last-n-games 10
```

## Visual Request Protocol (Agent + User)
For any new visual request, lock these fields first:
- `insight_goal`: what the post should prove
- `scope`: team/player + season or last N games
- `visual_type`: chart/card style
- `style_direction`: clean, bold, editorial, etc.
- `output_text`: exact title/subtitle/footnote

If you do not care about format details, defaults are:
- `1080x1350` feed portrait
- `PNG` export

## Keep It Simple Rules
- Start analysis in notebooks.
- Move code to `bulls/` only after repeating it 2-3 times.
- Prefer short markdown cells: title + one-liner context.
