"""Visual project paths: tracked assets/data and ignored output scratch.

Each project keeps a fixed YYYY-MM-DD-<slug> directory. Assets preserve shown and
approved chart versions; data preserves the sources and selections behind them.
Shared caches and licensed font extraction remain ignored. Older final/ folders
are historical only; composed Canva exports are temporary QA files.

See docs/reference/provenance.md for filing and pruning rules. Path helpers keep
existing project dates stable rather than scattering a multi-day post.
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
