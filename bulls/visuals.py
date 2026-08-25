"""Where a visual project's images live, for scratch and the tracked copy.

One project gets one dated folder, `YYYY-MM-DD-<slug>`, holding three kinds of
thing:

    docs/visuals/2026-08-07-shot-value-ladder/
        assets/   our own renders, versioned v01, v02, ... as each is reviewed
        data/     the numbers the renders were built from

The split is not filing for its own sake -- the two have different lifetimes and
different reasons to exist.

A third folder, `final/`, once held the composed page downloaded from Canva. That
was retired on 2026-08-22 as duplicated effort: Canva holds the editable design
and Instagram holds the published post, while the publish-DPI chart already
lands in `assets/` with a `-final` suffix. Fourteen older projects still carry a
`final/` folder; they stay as they are. Don't create new ones.

**Assets are versioned because they cannot be regenerated.** A chart rebuilt in
October is not the same chart: the season has more games in it, and the code has
moved. The PNG is the only record of what a given version actually showed.

Every render shown to the user is saved here at that moment, because whether a
render was "only an adjustment" is settled by what replaces it and so cannot be
judged when it is made. What does not survive is pruned before the post's single
commit, in hindsight, where the whole sequence is visible: adjustments -- moved,
resized, recolored, re-cropped -- are deleted, and versions carrying a decision
or approved by the user are kept. Saved versions stay at publish DPI so any one
of them can go into Canva without a rebuild.
``scripts/save_visual_version.py`` carries the full rule and the two ways it has
already failed.

**Finals are a single snapshot because Canva is a live surface.** The design keeps
being editable after the post goes out, so its link answers "what does this look
like now", never "what did we publish". One downloaded page per slide settles
that, and it costs nothing: a full export is already pulled for QA.

**Data is tracked because it is not always reproducible.** `cache/` is ignored on
the assumption that a fetch is cheap to repeat -- true for a one-request endpoint,
false for the 2,132 rate-limited play-by-play requests behind the assist-duos post,
which took fifty minutes and were destroyed by a routine worktree cleanup after the
graphic had already shipped. Anything a published number rests on that costs real
time, or that a provider could change or retire, is written here from the start
rather than copied here later: a tracked folder needs no one to remember it, and a
worktree holding one is dirty, which is already protected.

## Which folder a dataset belongs in

Two independent questions, and conflating them is what put fifty minutes of
play-by-play in an ignored folder:

**Scope decides where.** A dataset with exactly one consumer belongs in that
post's `data/`. A dataset many posts share has no single owner, and filing it
under one of them is arbitrary — the next post would either duplicate it or
reach sideways into a sibling's folder, which is worse. Shared material stays in
`cache/`: portraits (17 scripts), the font extraction (22), the league shot
baseline, the season game logs.

**Cost decides how much the choice matters.** Single-owner data ships with its
post whether or not it was expensive, because a graphic's inputs are what make
its numbers auditable a year later without refetching anything. Cost only raises
the stakes: cheap single-owner data in `cache/` is untidy, expensive
single-owner data in `cache/` is a loss waiting to happen.

`cache/` therefore holds shared, cheap, licensed, or third-party material only —
never the record behind a published number. The test is not "is this derived?"
but "who owns this, and what does it cost to get back — if it can be got back at
all?"

**Known gap: shared *and* expensive has no home.** `cache/` is ignored and post
`data/` folders are single-owner, so a costly dataset feeding three posts would
have nowhere safe to sit. Nothing qualifies today. The answer when something does
is a tracked shared folder, not squeezing it into whichever post got there first.

The folder's date is fixed when the post starts and never moves. Re-dating it per
save would scatter a post that spans three days across three folders, so lookup
matches on the slug and ignores whatever date is already attached.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ASSETS, DATA = "assets", "data"
FINAL = "final"  # legacy: read by older projects, never written to now
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def slugify(text: str) -> str:
    """A folder-safe slug. Raises rather than silently producing an empty name."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        raise ValueError("project name needs at least one alphanumeric character")
    return slug


def strip_date(name: str) -> str:
    return _DATE_PREFIX.sub("", name)


def find_visual_dir(base: Path, slug: str) -> Path | None:
    """An existing folder for this visual project, whatever date it carries."""
    if not base.is_dir():
        return None
    matches = sorted(d for d in base.iterdir()
                     if d.is_dir() and strip_date(d.name) == slug)
    return matches[0] if matches else None


def visual_dir(base: Path, project: str, when: str | None = None,
               create: bool = True) -> Path:
    """The dated folder for ``project`` under ``base``, reusing one if it exists.

    Reuse is what keeps a project's history in one place. Only the first save
    decides the date; every later one finds that folder by slug.
    """
    slug = slugify(project)
    existing = find_visual_dir(base, slug)
    if existing is not None:
        return existing
    target = base / f"{when or date.today().isoformat()}-{slug}"
    if create:
        target.mkdir(parents=True, exist_ok=True)
    return target
