# Bulls Analytics

Lean Python workspace for Chicago Bulls analysis in Jupyter notebooks.

## What This Repo Is For
- Pull Bulls game and shot data from the NBA API
- Compute reusable analysis metrics in `bulls/analysis`
- Build charts directly in notebooks with `matplotlib`

This repo is intentionally notebook-first and does not include a file-export/chart-render pipeline.

## Project Layout

```text
bulls-analytics/
├── bulls/
│   ├── data/       # NBA API fetch helpers
│   ├── analysis/   # stat + shot-quality analysis helpers
│   └── viz/        # matplotlib chart helpers for notebooks
├── notebooks/
│   ├── active/     # current idea notebooks
│   ├── archive/    # older/frozen notebooks
│   ├── templates/  # notebook starter templates
│   └── INDEX.md    # notebook catalog + workflow rules
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

## Keep It Simple Rules
- Start analysis in notebooks.
- Move code to `bulls/` only after repeating it 2-3 times.
- Prefer short markdown cells: title + one-liner context.
