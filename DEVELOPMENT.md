# Development

Read the relevant section when changing code. This is an entry point, not a mandatory reading list.

## Environment and code

Use `venv/bin/python` in the primary checkout. Linked worktrees reuse
`/Users/meltangonan/projects/bulls-analytics/venv/bin/python`; set `PYTHONPATH` to the working tree
when importing its code. `./run_tests.sh` handles this automatically.

- `bulls/data`: fetching and source normalization.
- `bulls/analysis`: calculations and qualifications.
- `bulls/graphics`: reusable chart elements, font helpers and court geometry.
- `scripts/prototypes`: post entry points; find the relevant one in `scripts/prototypes/README.md`.

Reuse an existing family before starting a new renderer. Keep post-specific selection and copy near
the entry point; shared fetching, table cells, boxes and portraits belong in the modules above.
For substantial data pulls, prepare display-ready values before rendering so a spacing change
can reuse the same verified inputs. Simple one-off analyses need no extra layer.

Cache successful requests and use saved data for visual iteration. Refresh when requested, when the
brief requires current facts, or when source/schema changes warrant it. Avoid concurrent NBA
play-by-play requests. Inspect endpoint parameters and response shapes before scaling a fetch.
Unavailable data stays unavailable; reconcile against independent official totals where possible.

## Verification by change

```bash
./run_tests.sh tests/test_scoring_leaps.py -q
./run_tests.sh tests/test_court.py tests/test_zone_charts.py -q
./run_tests.sh  # whole suite, when shared changes justify it
```

Explicit files/node IDs select only those checks. Options alone use `tests/` as the default.

| Change | Check |
| --- | --- |
| Caption/Canva positioning | Changed copy and actual exported page; no Python suite |
| One post's data or chart | Its test file and one rendered/exported result; reconcile changed data |
| Docs/skills | Changed commands, links and instruction consistency; relevant doc/symlink tests |
| Shared fetching/analysis/chart helpers | Module tests and affected families; whole suite once before integration if impact warrants |

Keep tests for formulas, coverage, unavailable data, qualification boundaries, source reconciliation,
publication-data preservation, and meaningful visual regressions. Avoid assertions that simply
repeat styling constants or inspect exact source-code text. Use a real render to judge appearance.
Do not rerun unchanged checks just because another message arrived. Report unrelated baseline
failures separately; don't silently expand the task to fix them. `git diff --check` checks patch hygiene.

## Conditional references

- Source selection, team stints, roster scope, clutch and advanced stats:
  `docs/reference/data-sources.md`.
- Shot coordinates, zone boundaries, chart-family metrics and thresholds:
  `docs/reference/shot-analysis.md`; visual styling is routed by `DESIGN.md`.
- Assist identity resolution, lineups and pbpstats: `docs/reference/play-by-play.md`.
- Source trail and version/data filing: `docs/reference/provenance.md`.
- Task isolation, integration and cleanup: `docs/reference/worktrees.md`.

## Common commands

```bash
venv/bin/python scripts/make_shot_chart.py --help
venv/bin/python scripts/save_visual_version.py --project <slug> <chart.png>
venv/bin/python scripts/save_visual_version.py --project <slug> --data <source.csv>
```

Read the selected renderer's arguments before using it. On supported renderers `--final` means
publish DPI; the archive helper has no `--final` flag. Canva owns page typography, background and
framing; chart labels use `house.helvetica()`. See `DESIGN.md` for the current palette and export contract.

At season rollover, update `CURRENT_SEASON` and `LAST_SEASON` in `bulls/config.py`; fetchers otherwise
continue serving the prior season. Dependency changes need an environment/import check.
