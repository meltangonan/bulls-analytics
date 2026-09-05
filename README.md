# Bulls Analytics

Python analysis and reusable chart assets for
[@chicagobullsdata](https://www.instagram.com/chicagobullsdata/). Canva assembles the page;
[Notion](https://www.notion.so/3a6e1c13abe680a889e5f0bd16dd6867) owns direction, ideas and post history.

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run_tests.sh
```

## Find the right entry point

| Need | Location |
| --- | --- |
| Task rules and selective reading | `AGENTS.md` |
| Current chart contract and reusable formats | `DESIGN.md` |
| Build, QA and post status | `POSTING_WORKFLOW.md` |
| Python environment, targeted tests and data references | `DEVELOPMENT.md` |
| Editorial direction | `STRATEGY.md` links to Notion |
| Existing post renderer and focused tests | `scripts/prototypes/README.md` |
| Fetch / calculate / render | `bulls/data`, `bulls/analysis`, `bulls/graphics` |
| Create / promote / review skills | `.agents/skills` (`.claude/skills` contains symlinks) |
| Preserved chart assets and source data | `docs/visuals/YYYY-MM-DD-<slug>/{assets,data}` |
| Disposable render scratch | `output/` (ignored) |

Use `./run_tests.sh tests/test_scoring_leaps.py -q` for one post. Reuse a chart family before
adding a new renderer. Store post-specific data with the post from the start; shared caches and
licensed font extraction stay ignored. Use a linked worktree for substantial or concurrent work;
small maintenance may use a clean primary checkout. See `docs/reference/worktrees.md`.
