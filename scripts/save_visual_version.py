#!/usr/bin/env python3
"""Preserve reviewed visual work in git as a dated, numbered version.

    venv/bin/python scripts/save_visual_version.py --project shot-value-ladder \
        output/2026-08-07-shot-value-ladder/*.png
    venv/bin/python scripts/save_visual_version.py --project shot-value-ladder --final \
        ~/Downloads/slide-1.png

Copies into ``docs/visuals/YYYY-MM-DD-<slug>/assets/`` as ``YYYY-MM-DD-vNN-<name>.png``,
or into ``final/`` with ``--final`` for pages downloaded from Canva. That tree is
**tracked**; ``output/`` is scratch and stays ignored. ``bulls/visuals.py`` explains
why the two kinds are kept differently.

Run this every time a version is shown to the user for review -- that is the unit
of a version, not every render. A render where a label moved two pixels is not a
version anybody wants to scroll past a year from now, but every state that was
actually put in front of someone is part of the record of how the visual was made.

Two things this closes, both of which cost real work once:

* **Images stopped being deletable.** ``output/`` is gitignored, so a worktree
  holding nothing but rendered charts looked clean to the cleanup rule in
  DEVELOPMENT.md and was removed, taking a day of approved renders with it.
  Files under ``docs/visuals/`` make the worktree dirty, and a dirty worktree is
  already protected.
* **Iterations stopped being anonymous.** One flat ``output/`` with
  overwriting filenames kept only the newest state, so "show me what it looked
  like before" had no answer.

Version numbers are per project and never reused: the next number is one past the
highest already on disk, so re-running after a rebuild does not renumber history.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bulls.visuals import ASSETS, FINAL, visual_dir, slugify  # noqa: E402

VISUALS = ROOT / "docs" / "visuals"
VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-v(\d+)-")
# Dated first so the directory sorts chronologically, version zero-padded so
# v10 sorts after v9 rather than between v1 and v2.
STAMP = "{date}-v{version:02d}-{name}"


def next_version(folder: Path) -> int:
    """One past the highest version already saved, so history never renumbers."""
    highest = 0
    for path in folder.glob("*.png"):
        match = VERSION_RE.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def strip_stamp(name: str) -> str:
    """Drop any leading date or version the render already carried.

    The chart CLIs date their own output, so without this a saved file would
    read ``2026-08-07-v03-2026-08-07-ladder-pps-league.png``.
    """
    name = VERSION_RE.sub("", name)
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)


def save(project: str, files: list[Path], when: str | None = None,
         version: int | None = None, final: bool = False) -> list[Path]:
    try:
        slugify(project)
    except ValueError as exc:
        raise SystemExit(str(exc))

    missing = [f for f in files if not f.is_file()]
    if missing:
        raise SystemExit("Not found: " + ", ".join(str(m) for m in missing))

    target = visual_dir(VISUALS, project, when) / (FINAL if final else ASSETS)
    target.mkdir(parents=True, exist_ok=True)
    stamp_date = when or date.today().isoformat()

    saved = []
    if final:
        # Finals are not versioned. One published page is one file; a second
        # download of the same slide replaces it rather than accumulating.
        for src in files:
            dest = target / f"{stamp_date}-{strip_stamp(src.name)}"
            shutil.copy2(src, dest)
            saved.append(dest)
        return saved

    number = version if version is not None else next_version(target)
    for src in files:
        dest = target / STAMP.format(date=stamp_date, version=number,
                                     name=strip_stamp(src.name))
        shutil.copy2(src, dest)
        saved.append(dest)
    return saved


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Save reviewed images to docs/visuals/<slug>/ as a dated version")
    ap.add_argument("--project", required=True,
                    help="visual project slug, e.g. shot-value-ladder")
    ap.add_argument("--date", default="", help="override the date stamp (YYYY-MM-DD)")
    ap.add_argument("--version", type=int, default=None,
                    help="force a version number instead of auto-incrementing")
    ap.add_argument("--final", action="store_true",
                    help="a page downloaded from Canva: goes to final/, unversioned")
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args()

    saved = save(args.project, args.files, args.date or None, args.version, args.final)
    for path in saved:
        print(f"Saved {path.relative_to(ROOT)}")
    match = VERSION_RE.match(saved[0].name)
    what = f"as v{match.group(1)}" if match else "as the published final"
    print(f"\n{len(saved)} file(s) {what}. Commit them — that is what makes them safe.")


if __name__ == "__main__":
    main()
