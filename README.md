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
`docs/bulls-content-playbook.html`. Boards, tables, and shared-scale comparisons are the default
grammar; court graphics only when location is the actual question.

**Idea catalog** — every post idea we mock gets a card in `docs/idea-catalog.html` (image, status,
grammar, notes). Open it in a browser to review the shelf.

## Project Layout

```text
bulls-analytics/
├── bulls/
│   ├── data/       # NBA API fetch helpers
│   ├── analysis/   # stat + shot-quality analysis helpers
│   └── graphics/   # social-graphics builders + shared craft helpers
├── scripts/        # CLI entrypoints
│   └── prototypes/ # one-off mock generators behind idea-catalog cards
├── docs/           # north star playbook, idea catalog, mocks, reference
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

Conventions, the data/analysis/graphics API reference, the graphics-generation workflow, and the
clarification gate for new visual requests live in **`AGENTS.md`** (`CLAUDE.md` is a one-line
pointer to it). Start there before adding data helpers, building a graphic, or mocking a post idea.
