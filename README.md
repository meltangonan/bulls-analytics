# Bulls Analytics

Lean Python workspace for Chicago Bulls analysis and lightweight social-graphics generation,
feeding the [@chicagobullsdata](https://www.instagram.com/chicagobullsdata/) Instagram account.

## What This Repo Is For
- Pull Bulls game and shot data from the NBA API.
- Compute reusable analysis metrics (zone leaders, points-per-shot, efficiency, lineups).
- Produce 1080x1350 Instagram graphics, one post idea at a time.
- Track every post idea as a card in the idea catalog.

This repo is intentionally lean: prototype scripts (`scripts/prototypes/`) plus the idea catalog
drive post mocks; formats that repeat get promoted into `bulls/graphics` with a CLI.

**Content north star** — the "Bulls visual encyclopedia" playbook in
`bulls-content-playbook.html` (repo root). Boards, tables, and shared-scale comparisons are the default
grammar; court graphics only when location is the actual question.

**Idea catalog** — every post idea we mock gets a card in `idea-catalog.html` (image, status,
grammar, notes). Open it in a browser to review the shelf.

**Strategy** — who the account is for, what winning looks like, and where effort goes lives in
`STRATEGY.md` at the repo root.

## Project Layout

```text
bulls-analytics/
├── .agents/skills/   # repo-scoped post creation, promotion, and review workflows
├── .claude/skills/   # Claude Code wrappers with links to canonical .agents skill files
├── STRATEGY.md      # why the account exists: audience, metrics, tracks
├── DESIGN.md        # visual system: palette, typography, layout, brand status
├── POSTING_WORKFLOW.md # visual-post gates and catalog-to-post workflow
├── DEVELOPMENT.md   # code, data, graphics, and test reference
├── bulls-content-playbook.html  # north star: the "Bulls visual encyclopedia"
├── idea-catalog.html            # every mocked post idea as a card
├── bulls/
│   ├── data/       # NBA API fetch helpers
│   ├── analysis/   # stat + shot-quality analysis helpers
│   └── graphics/   # social-graphics builders + shared craft helpers
├── scripts/        # CLI entrypoints
│   └── prototypes/ # one-off mock generators behind idea-catalog cards
├── docs/           # mocks, reference, ideation, temporary handoffs, archive
├── tests/          # unit tests with mocked API calls
└── output/         # generated graphics (gitignored)
```

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run_tests.sh  # verify setup
```

## Running Tests

```bash
./run_tests.sh
# or
venv/bin/python -m pytest tests/ -v
```

## Working In This Repo

Start with **`AGENTS.md`** (`CLAUDE.md` is a one-line pointer to it). It routes work to the focused
owner documents: `DEVELOPMENT.md` for code and tests, `DESIGN.md` for visual decisions,
`POSTING_WORKFLOW.md` for visual-post production, and `STRATEGY.md` plus
`bulls-content-playbook.html` for editorial direction. Canonical repo-scoped skills in
`.agents/skills/` guide the recurring create, promote, and review stages without duplicating those
owner documents; `.claude/skills/` contains discovery wrappers with symlinked entrypoints to the
same skills for Claude Code.
