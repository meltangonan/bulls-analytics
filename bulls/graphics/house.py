"""Executable house style for current @chicagobullsdata graphics.

``DESIGN.md`` remains the human-readable source of truth. This module is the
small Matplotlib implementation of the rules every current feed post shares:
canvas, type, header, footer, color tokens, and draft/final export behavior.

Post-specific charts, tables, annotations, and story decisions do not belong
here. They stay with the format that needs them until a second real post proves
that the visual grammar repeats.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
DRAFT_DPI = 150
FINAL_DPI = 300
SIDE_MARGIN = 60
FOOTER_Y = 40
STRIPE_HEIGHT = 16  # full-bleed jersey-trim band at the very top of the canvas

# Jersey-lettering title: ink fill, white gap, red outer stroke. Flip to False
# (or pass outlined=False per post) to return to the plain fitted title.
OUTLINED_TITLE = True

WHITE = "#FFFFFF"
RED = "#CE1141"
BULLS_BLACK = "#141414"
INK = "#1A1A1A"
MUTED = "#777777"
FAINT = "#AAAAAA"
RULE = "#DDDDDD"
SUBTITLE_RULE = "#CFCFCF"
GRIDLINE = "#F0F0F0"

_DISPLAY_FONT = REPO_ROOT / "assets" / "fonts" / "AcademicM54.ttf"
_BODY_FONTS = {
    "regular": REPO_ROOT / "assets" / "fonts" / "Archivo-400.ttf",
    "medium": REPO_ROOT / "assets" / "fonts" / "Archivo-500.ttf",
    "bold": REPO_ROOT / "assets" / "fonts" / "Archivo-600.ttf",
}


def display_font() -> fm.FontProperties:
    """Academic M54 display face.

    The font is free for non-commercial use only. If the account becomes
    commercial, license it or replace it with the documented Bevan fallback.
    """
    return fm.FontProperties(fname=str(_DISPLAY_FONT))


def body_font(weight: str = "regular") -> fm.FontProperties:
    """Return the explicit Archivo file for a supported weight."""
    try:
        path = _BODY_FONTS[weight]
    except KeyError as error:
        supported = ", ".join(_BODY_FONTS)
        raise ValueError(f"Unsupported Archivo weight '{weight}'; choose {supported}.") from error
    return fm.FontProperties(fname=str(path))


def rendered_width(ax, text_artist) -> float:
    """Rendered text width in the axes' pixel-like data coordinates."""
    ax.figure.canvas.draw()
    bbox = text_artist.get_window_extent()
    inverse = ax.transData.inverted()
    x0, _ = inverse.transform((bbox.x0, bbox.y0))
    x1, _ = inverse.transform((bbox.x1, bbox.y0))
    return x1 - x0


def new_canvas():
    """Create the fixed 1080x1350 full-bleed house canvas."""
    fig = plt.figure(
        figsize=(CANVAS_WIDTH / DRAFT_DPI, CANVAS_HEIGHT / DRAFT_DPI),
        facecolor=WHITE,
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, CANVAS_WIDTH)
    ax.set_ylim(0, CANVAS_HEIGHT)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax


def draw_jersey_stripe(ax):
    """Draw the full-bleed jersey-trim band across the top of the canvas.

    Red with one white and one black pinstripe, top-down: red 4, white 2,
    red 4, black 2, red 4 (16 px total). Mirrors the ``.band`` element on
    design-system.html.
    """
    layers = [(4, RED), (2, WHITE), (4, RED), (2, BULLS_BLACK), (4, RED)]
    artists = []
    y = CANVAS_HEIGHT
    for height, color in layers:
        y -= height
        artists.append(
            ax.add_patch(
                plt.Rectangle(
                    (0, y),
                    CANVAS_WIDTH,
                    height,
                    facecolor=color,
                    edgecolor="none",
                    zorder=5,
                )
            )
        )
    return artists


def draw_fitted_title(
    ax,
    segments: Sequence[tuple[str, str]],
    *,
    x: float = SIDE_MARGIN,
    y: float = CANVAS_HEIGHT - 66,
    max_width: float = CANVAS_WIDTH - 2 * SIDE_MARGIN,
    base_size: float = 90,
    outlined: bool | None = None,
):
    """Draw a multi-color Academic M54 title fitted to the house margins.

    ``outlined`` defaults to the module-level ``OUTLINED_TITLE`` switch. When
    on, each glyph gets jersey-lettering strokes: red outer, white gap, then
    the segment's fill color.
    """
    if outlined is None:
        outlined = OUTLINED_TITLE
    font = display_font()
    probe = ax.text(
        x,
        y,
        "".join(text for text, _ in segments),
        ha="left",
        va="top",
        fontsize=base_size,
        fontproperties=font,
        alpha=0,
    )
    width = rendered_width(ax, probe)
    probe.remove()
    size = base_size if width <= 0 else base_size * max_width / width

    artists = []
    cursor = x
    for text, color in segments:
        artist = ax.text(
            cursor,
            y,
            text,
            ha="left",
            va="top",
            fontsize=size,
            color=color,
            fontproperties=font,
        )
        if outlined:
            artist.set_path_effects([
                pe.withStroke(linewidth=7, foreground=RED),
                pe.withStroke(linewidth=3.5, foreground=WHITE),
                pe.Normal(),
            ])
        artists.append(artist)
        cursor += rendered_width(ax, artist)
    return artists


def draw_subtitle(
    ax,
    parts: Sequence[str | tuple[str, str]],
    *,
    y: float = CANVAS_HEIGHT - 168,
    weight: str = "medium",
):
    """Draw subtitle parts separated by real vertical ticks, never glyphs."""
    cursor = SIDE_MARGIN
    artists = []
    for index, part in enumerate(parts):
        text, color = part if isinstance(part, tuple) else (part, MUTED)
        artist = ax.text(
            cursor,
            y,
            text,
            ha="left",
            va="top",
            fontsize=18,
            color=color,
            fontproperties=body_font(weight),
        )
        artists.append(artist)
        cursor += rendered_width(ax, artist)
        if index < len(parts) - 1:
            cursor += 13
            line = ax.plot(
                [cursor, cursor],
                [y - 21, y - 5],
                color=SUBTITLE_RULE,
                lw=1.3,
                zorder=6,
            )[0]
            artists.append(line)
            cursor += 13
    return artists


def draw_header(
    ax,
    title_segments: Sequence[tuple[str, str]],
    subtitle_parts: Sequence[str | tuple[str, str]],
    *,
    kicker: str | None = None,
    subtitle_weight: str = "medium",
    title_base_size: float = 90,
    stripe: bool = True,
    outlined: bool | None = None,
):
    """Draw the current stripe, title, subtitle, and optional kicker pattern."""
    artists = list(draw_jersey_stripe(ax)) if stripe else []
    artists.extend(
        draw_fitted_title(ax, title_segments, base_size=title_base_size, outlined=outlined)
    )
    artists.extend(draw_subtitle(ax, subtitle_parts, weight=subtitle_weight))
    if kicker:
        artists.append(
            ax.text(
                SIDE_MARGIN,
                CANVAS_HEIGHT - 206,
                kicker,
                ha="left",
                va="top",
                fontsize=14,
                color=RED,
                style="italic",
                fontproperties=body_font("medium"),
            )
        )
    return artists


def draw_footer(
    ax,
    *,
    source: str = "Data via NBA.com/Stats",
    note: str | None = None,
    watermark: str = "@chicagobullsdata",
):
    """Draw the required source/watermark footer pair."""
    left_text = f"{note} · {source}" if note else source
    source_artist = ax.text(
        SIDE_MARGIN,
        FOOTER_Y,
        left_text,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=FAINT,
        fontproperties=body_font(),
    )
    watermark_artist = ax.text(
        CANVAS_WIDTH - SIDE_MARGIN,
        FOOTER_Y,
        watermark,
        ha="right",
        va="bottom",
        fontsize=10.5,
        color=MUTED,
        fontproperties=body_font("medium"),
        zorder=8,
    )
    return source_artist, watermark_artist


def export_dpi(final: bool) -> int:
    return FINAL_DPI if final else DRAFT_DPI


def save_post(fig, output_path: str | Path, *, final: bool = False) -> Path:
    """Save a house post at draft or final resolution."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=export_dpi(final), facecolor=fig.get_facecolor())
    return output
