"""Where a post's images live, for both the scratch and the tracked copy.

One post gets one dated folder, `YYYY-MM-DD-<slug>`, and two kinds of image
inside it:

    docs/posts/2026-08-07-shot-value-ladder/
        assets/   our own renders, versioned v01, v02, ... as each is reviewed
        final/    the page(s) downloaded from Canva once it publishes

The split is not filing for its own sake -- the two have different lifetimes and
different reasons to exist.

**Assets are versioned because they cannot be regenerated.** A chart rebuilt in
October is not the same chart: the season has more games in it, and the code has
moved. The PNG is the only record of what a given version actually showed, so
every state put in front of someone is kept.

**Finals are a single snapshot because Canva is a live surface.** The design keeps
being editable after the post goes out, so its link answers "what does this look
like now", never "what did we publish". One downloaded page per slide settles
that, and it costs nothing: a full export is already pulled for QA.

The folder's date is fixed when the post starts and never moves. Re-dating it per
save would scatter a post that spans three days across three folders, so lookup
matches on the slug and ignores whatever date is already attached.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ASSETS, FINAL = "assets", "final"
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def slugify(text: str) -> str:
    """A folder-safe slug. Raises rather than silently producing an empty name."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        raise ValueError("post name needs at least one alphanumeric character")
    return slug


def strip_date(name: str) -> str:
    return _DATE_PREFIX.sub("", name)


def find_post_dir(base: Path, slug: str) -> Path | None:
    """An existing folder for this post, whatever date it carries."""
    if not base.is_dir():
        return None
    matches = sorted(d for d in base.iterdir()
                     if d.is_dir() and strip_date(d.name) == slug)
    return matches[0] if matches else None


def post_dir(base: Path, post: str, when: str | None = None,
             create: bool = True) -> Path:
    """The dated folder for ``post`` under ``base``, reusing one if it exists.

    Reuse is what keeps a post's history in one place. Only the first save
    decides the date; every later one finds that folder by slug.
    """
    slug = slugify(post)
    existing = find_post_dir(base, slug)
    if existing is not None:
        return existing
    target = base / f"{when or date.today().isoformat()}-{slug}"
    if create:
        target.mkdir(parents=True, exist_ok=True)
    return target
