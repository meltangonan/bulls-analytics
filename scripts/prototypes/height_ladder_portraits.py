"""Build post-local portraits for the Bulls the NBA CDN has no photo for.

Seven rungs of the height ladder are won by players the league serves a generic
silhouette for. These portraits were sourced by hand, so they cannot be refetched
and they belong to exactly one post -- which puts them in this post's tracked
``data/`` rather than the shared, ignored ``cache/`` (``bulls/visuals.py``).

Both the originals and the processed cut-outs are kept. The originals are the
irreplaceable part; the processing is code and can be re-run.
"""
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from bulls.graphics import house

DATA = Path("docs/visuals/2026-08-20-most-ppg-at-each-height/data")
SOURCE_DIR = DATA / "portraits_source"
OUT_DIR = DATA / "portraits"

DOWNLOADS = Path.home() / "Downloads"

# NBA player id -> the supplied file. Ids verified against CommonPlayerInfo.
SUPPLIED = {
    101126: "Nate Robinson.jpg",
    77042: "Wilbur Holland.png",
    769: "BJ Armstrong.png",
    2857: "Andre Barrett.png",
    78615: "Orlando Woolridge.png",
    76362: "Bill Carwright.png",
    77707: "Chuck Nevitt.png",
}

# Sources framed wider than an NBA headshot, cropped to head-and-shoulders
# before processing. Without this the whole torso is scaled to fit the canvas
# and the face lands visibly smaller than every other row's.
# Fractions of the source: (left, top, right, bottom).
PRE_CROP = {
    101126: (0.28, 0.04, 0.74, 0.80),   # Nate Robinson
    769: (0.28, 0.02, 0.76, 0.76),      # B.J. Armstrong
}

# A portrait already this transparent is a cut-out and must not be flood-filled:
# the fill rewrites every alpha to opaque, which would turn its transparent
# surround into a solid black rectangle.
CUT_OUT_THRESHOLD = 0.15


def pre_cropped(path: Path, box) -> Path:
    """Write a head-and-shoulders crop of a wide source to scratch.

    Deliberately not written beside the source: ``portraits_source/`` is
    tracked and holds the irreplaceable originals, and a regenerable
    intermediate landing there dirties the worktree on every re-run.
    """
    image = Image.open(path)
    w, h = image.size
    left, top, right, bottom = box
    cropped = image.crop((int(w * left), int(h * top),
                          int(w * right), int(h * bottom)))
    scratch = Path("output") / "height_ladder_crops"
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / f"{path.stem}-cropped.png"
    cropped.save(out)
    return out


def transparent_fraction(path: Path) -> float:
    alpha = np.array(Image.open(path).convert("RGBA"))[:, :, 3]
    return float((alpha < 16).mean())


def reframe_cut_out(source: Path, destination: Path) -> Path:
    """Paste an existing cut-out into NBA headshot proportions.

    Mirrors the framing half of ``house.cut_out_flat_background`` so a supplied
    cut-out lands under the same face crop as a CDN portrait.
    """
    image = Image.open(source).convert("RGBA")
    bbox = image.getbbox()          # drop the transparent margin first, or the
    if bbox:                        # player is scaled to fit his own padding
        image = image.crop(bbox)

    canvas_w, canvas_h = house.NBA_PORTRAIT_SIZE
    crop_side = int(canvas_h * house.PORTRAIT_CROP_FRACTION)
    scale = min(crop_side / image.width, crop_side / image.height)
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.LANCZOS,
    )
    canvas = Image.new("RGBA", house.NBA_PORTRAIT_SIZE, (0, 0, 0, 0))
    canvas.paste(
        resized,
        ((canvas_w - resized.width) // 2, max(0, crop_side - resized.height)),
        resized,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)
    return destination


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for player_id, filename in SUPPLIED.items():
        incoming = DOWNLOADS / filename
        kept = SOURCE_DIR / filename
        if incoming.is_file():
            shutil.copy2(incoming, kept)
        if not kept.is_file():
            print(f"  {player_id}: MISSING {filename}")
            continue

        out = OUT_DIR / f"{player_id}.png"
        working = kept
        note = ""
        if player_id in PRE_CROP:
            working = pre_cropped(kept, PRE_CROP[player_id])
            note = ", pre-cropped"
        if transparent_fraction(working) >= CUT_OUT_THRESHOLD:
            reframe_cut_out(working, out)
            how = "reframed (already a cut-out)"
        else:
            house.cut_out_flat_background(working, out)
            how = "background removed"
        how += note
        print(f"  {player_id}: {filename} -> {out.name}  [{how}, "
              f"{transparent_fraction(out):.0%} transparent]")


if __name__ == "__main__":
    main()
