#!/usr/bin/env python3
"""Save reviewed charts as dated versions, or copy their source/audit tables.

    venv/bin/python scripts/save_visual_version.py --project shot-value-ladder \
        output/2026-08-07-shot-value-ladder/*.png

Images go into docs/visuals/YYYY-MM-DD-<slug>/assets/ with increasing version
numbers; --data keeps source filenames in data/. Save before showing a render;
prune superseded cosmetic adjustments before the logical post commit, preserving
approved and decision-bearing publish-resolution assets. Full filing rules live
in docs/reference/provenance.md. Canva page exports are temporary QA, not archived
here. This helper has no --final flag; supported renderers use it for publish DPI.
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

from bulls.visuals import ASSETS, DATA, visual_dir, slugify  # noqa: E402

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
         version: int | None = None, data: bool = False) -> list[Path]:
    try:
        slugify(project)
    except ValueError as exc:
        raise SystemExit(str(exc))

    missing = [f for f in files if not f.is_file()]
    if missing:
        raise SystemExit("Not found: " + ", ".join(str(m) for m in missing))

    subfolder = DATA if data else ASSETS
    target = visual_dir(VISUALS, project, when) / subfolder
    target.mkdir(parents=True, exist_ok=True)
    stamp_date = when or date.today().isoformat()

    saved = []
    if data:
        # Unversioned, and the name is kept verbatim. Data answers "what are the
        # numbers now" rather than "what did a given draft show" -- the version
        # history of what was *shown* lives in assets/. Keeping the source filename
        # means a rebuild overwrites its own file instead of piling up near-copies.
        for src in files:
            dest = target / src.name
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
    ap.add_argument("--data", action="store_true",
                    help="the numbers behind a render: goes to data/, unversioned")
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args()

    saved = save(args.project, args.files, args.date or None, args.version,
                 args.data)
    for path in saved:
        print(f"Saved {path.relative_to(ROOT)}")
    match = VERSION_RE.match(saved[0].name)
    if match:
        what = f"as v{match.group(1)}"
    else:
        what = "as source data"
    print(f"\n{len(saved)} file(s) {what}. They stay uncommitted until the post is "
          "finished — one post is one commit.")


if __name__ == "__main__":
    main()
