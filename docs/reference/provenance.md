# Provenance and saved artifacts

Each data-bearing Notion post records a compact source trail as work lands:

1. Source URL/endpoint and exact call parameters, including scope and season type.
2. What one raw row represents, with a real example.
3. Units and coordinate systems where relevant.
4. Measured/provider fields versus our derived fields and their formulas.
5. What the source cannot contain, plus exclusions, unavailable results and coverage gaps.
6. One worked raw row traced into the published figure, and paths to the saved inputs/output.

Record reconciliations and cache/schema changes that affect the result. For example,
`ShotChartDetail` contains field-goal attempts, not free throws; total PPG must use official
`PTS / GP`, not shot-derived points. Parameter names can mislead: `season_type_all_star` selects
ordinary season type, and `context_measure_simple="FGA"` requests attempts rather than makes only.

## File ownership

- A dataset consumed by one post belongs in `docs/visuals/YYYY-MM-DD-<slug>/data/` from the start.
  Preserve raw scope, audit tables and the exact selection behind the chart. Snapshot manual data
  with source URLs, capture date, exclusions and independent reconciliations.
- Shared inputs such as portraits, league shot baselines and season game logs remain in ignored
  `cache/`; preserve unique expensive cache contents before worktree cleanup. Licensed font
  extraction never enters Git. A newly shared dataset needing durable versioning merits an explicit
  shared home, not accidental ownership by one post.
- Render into ignored `output/`. Before showing each render, save it with
  `scripts/save_visual_version.py --project <slug> <files>`. Use `--data` for input/audit tables.
  The project date is fixed on creation; version numbers increase without renumbering history.
- Save publish-resolution assets. Before the logical post commit, prune only superseded cosmetic
  adjustments; keep approved and decision-bearing versions. Data filenames remain stable, so keep
  distinct audit tables for metric/cohort alternatives when overwriting would lose the decision.
- Composed Canva exports are temporary QA files. Preserve the Canva URL in Notion; older `final/`
  archives stay historical. The save helper accepts no `--final` flag.
