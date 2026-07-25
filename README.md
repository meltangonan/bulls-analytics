# Bulls Analytics

Lean Python workspace for Chicago Bulls analysis and social-graphics production, feeding the
[@chicagobullsdata](https://www.instagram.com/chicagobullsdata/) Instagram account. Python pulls and
verifies the data and renders the chart; the 1080×1350 post is assembled in Canva, whose Brand Kit
owns the page typography.

Intentionally lean: prototype scripts plus the idea catalog drive post mocks; formats that repeat get
promoted into `bulls/graphics` with a CLI.

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run_tests.sh  # verify setup
```

## Layout

```text
bulls-analytics/
├── AGENTS.md         # start here — map, defaults, safety rules (CLAUDE.md points at it)
├── STRATEGY.md       # who the account is for, what winning looks like
├── DESIGN.md         # chart layer, colors, and voice — the canonical record
├── design-system.html          # browsable companion (documents the legacy full-layout system)
├── POSTING_WORKFLOW.md         # brief → draft → approval → catalog
├── DEVELOPMENT.md    # code conventions and data gotchas
├── bulls-content-playbook.html # north star: the "Bulls visual encyclopedia"
├── idea-catalog.html           # every post idea as a card
├── .agents/skills/   # canonical create / promote / review skills
├── .claude/skills/   # symlinks to the above, for Claude Code discovery
├── bulls/            # data fetchers, analysis, graphics
├── scripts/          # CLI entrypoints; prototypes/ holds one-off mock generators
├── docs/             # mocks, reference, ideation, handoffs, archive
├── tests/            # pytest, NBA API mocked
└── output/           # generated graphics (gitignored)
```

## Working in this repo

Start with **`AGENTS.md`**. It routes to the owner document for whatever you're changing, and each
topic has exactly one owner — visual and voice decisions in `DESIGN.md`, production procedure in
`POSTING_WORKFLOW.md`, code in `DEVELOPMENT.md`, audience and distribution in `STRATEGY.md`.

Approved final pages are preserved in `docs/mocks/` and tracked as cards in `idea-catalog.html`.
Open `design-system.html` in a browser for the visual companion to `DESIGN.md`.
