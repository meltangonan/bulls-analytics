# Bulls Analytics

Lean Python workspace for Chicago Bulls analysis and social-graphics production, feeding the
[@chicagobullsdata](https://www.instagram.com/chicagobullsdata/) Instagram account. Python pulls and
verifies the data and renders the chart; the 1080×1350 post is assembled in Canva, whose Brand Kit
owns the page typography.

Intentionally lean: Notion ideas become one-off prototype scripts; formats that repeat get promoted
into `bulls/graphics` with a CLI.

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run_tests.sh  # verify setup
```

NBA.com blocks datacenter/cloud IPs, so on Cursor Cloud or CI the live API needs a proxy: set the
`NBA_STATS_PROXY` secret to a non-blocked (residential/mobile) proxy URL, then verify with
`venv/bin/python scripts/check_nba_api.py`. On home internet no proxy is needed. See
`DEVELOPMENT.md` → Network Access.

## Layout

```text
bulls-analytics/
├── AGENTS.md         # start here — map, defaults, safety rules (CLAUDE.md points at it)
├── STRATEGY.md       # who the account is for, what winning looks like
├── DESIGN.md         # chart layer, colors, and voice — the canonical record
├── POSTING_WORKFLOW.md         # brief → draft → approval → Notion record
├── DEVELOPMENT.md    # code conventions and data gotchas
├── .agents/skills/   # canonical create / promote / review skills
├── .claude/skills/   # symlinks to the above, for Claude Code discovery
├── bulls/            # data fetchers, analysis, graphics
├── scripts/          # CLI entrypoints; prototypes/ holds one-off mock generators
├── assets/           # local headshot overrides (Summer League report)
├── docs/             # permanent visuals and active handoffs
├── tests/            # pytest, NBA API mocked
└── output/           # generated graphics (gitignored)
```

## Working in this repo

Start with **`AGENTS.md`**. It routes to the owner document for whatever you're changing, and each
topic has exactly one owner — visual and voice decisions in `DESIGN.md`, production procedure in
`POSTING_WORKFLOW.md`, code in `DEVELOPMENT.md`, audience and distribution in `STRATEGY.md`.

Reviewed visual work lives in `docs/visuals/YYYY-MM-DD-<slug>/`: `assets/` holds our own renders, one
numbered version per state shown for review, and `data/` holds the numbers behind them. Save with
`scripts/save_visual_version.py`. `output/` is disposable, gitignored scratch. The composed Canva page
is not archived here — Canva holds the editable design, Instagram holds the published post, and QA
still works from a downloaded export that is checked, not filed. Older posts may still carry a
retired `final/` folder; do not create new ones.
Posts are tracked in the Notion `chicagobullsdata posts` database; all preserved graphics live under
`docs/visuals/`.
