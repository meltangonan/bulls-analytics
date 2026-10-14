# Handoff: comment audit follow-up

Written 2026-10-14 at the end of the session that ran the audit. Status: open. Three optional work items
remain; none is urgent and none blocks posts.

## Objective

Finish applying the no-comments principle the user adopted on 2026-10-14 (from
https://x.com/poteto/status/2110149626133438732): agents copy what they read, so a comment that narrates,
excuses a workaround, or explains a surprise in our own code teaches the next agent to write more of the
same. The rule now lives in `AGENTS.md` (Working defaults): comment only what code cannot say (outside-system
quirks, data provenance, run instructions); make our own logic obvious through names, constants, functions
and tests; design decisions belong in `DESIGN.md`/`docs/design/` or Notion; delete a comment that disagrees
with its code. The user chose to do this by hand, without installing poteto's `no-comments` skill.

## Done (on `main`, pushed; `git log 8e04c71^..486141c`)

| Commit | What |
| --- | --- |
| `8e04c71` | Credibility fixes: `get_league_shots` refuses a partial league; team-ranks `pulled.txt`; and-1 test tolerance made exact; a no-op test fixed; wrong docstrings corrected |
| `355abf7` | AGENTS.md rule; ~1,640 mechanical deletions; 131 restored after two independent reviews |
| `4888e89` | Shared `bulls.data.nba_frame` retry helper replaced 7 copies; DEVELOPMENT.md points at it |
| `b619bcd` | `house.GREEN_TEXT` and `house.PORTRAIT_CROP_FRACTION` replaced hand-copied literals |
| `85339b6`, `c66ab3f`, `486141c` | Design reasoning moved into `docs/design/shot-charts.md`, `tables-cards.md`, `docs/reference/shot-analysis.md`, `DESIGN.md` (three user-approved rules) and the recap README, in three user-approved batches |

Full-line comments went 2,924 to 1,203 and docstrings 1,774 to 627. The season-openers Notion page was
corrected (leaguegamefinder vs TeamGameLog before 1983-84).

## Decisions to preserve

- **Published-post scripts stay reproducible.** Where one breaks a later rule, leave it so a re-render matches
  the live post: Taj Gibson's `#3FAE63` win text, rookie leaderboard rank numerals, the rookie chronological
  table's equal widths, bench-points `#DCD6CE` rule, pull-up points' tiebreak to 15 rows. New work follows docs.
- **Published posts' Notion pages are not edited as a side effect**; only on the user's explicit request.
- **Module docstrings of scripts are `--help` text** (`argparse.ArgumentParser(description=__doc__)` in ~40
  scripts). Correct them; never delete them. Test-module docstrings may go.
- **A reshape comment is deleted only when its code fix lands**, never before: surprising code with no
  explanation is worse than either state.
- **Commits and pushes need the user's explicit approval each time** (AGENTS.md). One logical change per commit.
- **The postgame recap pipeline runs live after every Bulls game.** Change it only with its tests
  (`tests/test_postgame_recap.py`) and not close to a game. `build_mockup.py` was deliberately left with a
  literal `0.74` rather than importing `house` (it would pull in matplotlib on the delivery path).
- Tenure zone grids: usually three columns, short last row left-aligned (Rose 2-2-2, LaVine 3-3-2, Hinrich
  3-3-3-1); the code default `ZONEGRID_COLS = 4` is unused by published posts and was left alone.

## Open work

Working files are git-ignored in the primary checkout's `output/comment-audit/` (local to this Mac):
`reshape-todo.tsv`, `check-todo.tsv`, `checks.md` (resolved claims), `all.tsv` (original audit, line numbers
from `e6bafc8`), `rubric.md`, and `tools/` (`apply_kills.py`, `same_code.py`, reviewer briefs). Line numbers in
the to-do files are for `b7d6206`; re-locate by content if files have moved since.

### 1. Reshape pass (604 comments; recommended next)

Each row is a comment explaining our own code plus a proposed fix: a NamedTuple for a positional tuple, a
named constant for a bare number, a unit in a name (`POLL_SECONDS`), an assertion message, a split function.
Counts: 129 shared library/recap pipeline/`make_shot_chart.py`, 256 post scripts, 219 tests. The file is
sorted shared code first.

- Do the 129 shared items first; they are what agents read and copy. Then tests, opportunistically. Leave
  finished post scripts unless already editing one.
- Proposals are suggestions from sub-agents, not decisions. Some say only "delete" (a redundant module
  docstring); some name a constant that should be imported from an existing owner instead (check
  `bulls/graphics/house.py`, `bulls/config.py`, `bulls/analysis/shot_maps.py` first).
- Verify every change: `./run_tests.sh -q` (1,514 passed at `486141c`) plus a render or import of the
  touched script. `tools/same_code.py` proves comment-only edits leave code structure unchanged; a reshape
  changes code on purpose, so list those files as expected.

### 2. Packaging decision (needs the user first)

133 scripts open with a `sys.path.insert` block and `# noqa: E402` imports because the repo is not an
installable package. The fix is a small `pyproject.toml`, `pip install -e .` into the shared `venv`, and
deleting the blocks. Risk: every worktree and the recap routine share that `venv`, and `run_tests.sh` sets
`PYTHONPATH` itself. Recommend: low priority; if approved, do it when no posts are in flight and dry-run the
recap pipeline afterwards. Ask before starting.

### 3. Verify claims about outside data (41)

`check-todo.tsv` lists comments that state a fact about an outside source no saved file confirms (16 post
scripts, 8 shared, 17 tests): e.g. United Center scorer-label rank, NBA cut-out transparency, league BPM
percentiles, a HOU at DAL lead count. Of eight checked so far, five were false (see `checks.md`). For each:
query the source or saved data, then correct the comment, keep it citing the source, or delete it. Best done
when the related post or file is next touched. Also open: whether box-score awards fire in 5-20% of games
(`postgame-recaps/README.md:361`); nothing measures it.

### Housekeeping

- The `comment-audit` and `knicks-top-game-scores` worktrees and branches were removed on 2026-10-14 after
  merging; their unique ignored files were copied into the primary checkout's `output/` and `cache/`.
  `b7d6206` renamed `lakers_top_game_performances.py` to `team_top_game_performances.py`.
- `bulls-scorigami` and `claxton-splitter-draft` predate the audit; expect comment-only conflicts when
  they sync with `main`.

## Lessons from this session

- Sub-agent findings were right most of the time but not always: a claimed stripe alpha (0.12 vs real
  0.09-0.12) and a "4-3-3" grid that came from a generic code comment, not the published post. Check numbers
  against code or data before writing them into a doc.
- Comments flagged "restates code" over three lines often carried real reasoning; hold long blocks for review.
- Delete comments with tokenize/ast (never a `#` regex: colour strings contain `#`), and prove the result
  with an AST comparison plus the full test suite.
