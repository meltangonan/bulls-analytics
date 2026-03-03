# Notebook Index

This workspace uses a one-notebook-per-idea workflow.

## Rules
- New notebooks go in `notebooks/active/`.
- File names must follow `YYYY-MM-DD-topic-slug.ipynb`.
- Start from `notebooks/templates/idea_template.ipynb`.
- Move completed notebooks to `notebooks/archive/`.
- If logic repeats in 2+ notebooks, move it into `bulls/` and add/update tests.

## Notebook Section Contract
- `Objective` (one sentence)
- `Data Pull` (imports + fetch only)
- `Analysis` (2-4 focused blocks)
- `Output` (1-2 key charts/tables)
- `Takeaways` (3 bullets)
- `Next Question` (one line)

## New Notebook Command
```bash
cp notebooks/templates/idea_template.ipynb notebooks/active/$(date +%F)-topic-slug.ipynb
```

## Active Notebooks
- `2026-03-02-zone-leaders-analysis.ipynb` — Full player-by-zone tables behind the zone leaders graphics, with PPG/frequency breakdowns and social commentary insights.

## Archive
- `efficiency_matrix.ipynb`
- `points_per_shot.ipynb`
- `points_per_shot_last_season.ipynb`
- `postgame_shot_charts.ipynb`
- `shooting_matrices.ipynb`
- `shot_selection_analysis.ipynb`
- `zone_leaders.ipynb`
