"""Executable house style for current @chicagobullsdata graphics.

``DESIGN.md`` remains the human-readable source of truth. This module is the
small Matplotlib implementation of the rules every current feed post shares:
canvas, type, header, footer, color tokens, and draft/final export behavior.

Post-specific charts, tables, annotations, and story decisions do not belong
here. They stay with the format that needs them until a second real post proves
that the visual grammar repeats.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Theme:
    """A coordinated canvas palette for rendered posts.

    A background is a contract with every other color on the page, so a theme
    carries the full token set, not just the canvas fill. ``jersey`` (warm
    off-white) is the default; ``white`` matches the loose module constants
    above. The palettes mirror the doc-chrome themes on design-system.html,
    promoted to real render options (DESIGN.md §2/§10).
    """

    name: str
    canvas: str  # canvas background
    ink: str  # primary text, data lines
    muted: str  # secondary text, axis labels, watermark
    faint: str  # footer/source credit, quietest tier
    rule: str  # table rules, hairlines
    tick: str  # subtitle separator ticks
    grid: str  # chart gridlines
    accent: str  # the one accent color (red on light canvases)
    contrast: str  # heavy fills opposite the accent (black role)
    band: str  # jersey-stripe band fill
    trim_a: str  # first pinstripe
    trim_b: str  # second pinstripe

    @property
    def stripe_layers(self) -> list[tuple[int, str]]:
        """Top-down stripe layers: band 4 / trim_a 2 / band 4 / trim_b 2 / band 4."""
        return [
            (4, self.band),
            (2, self.trim_a),
            (4, self.band),
            (2, self.trim_b),
            (4, self.band),
        ]


THEMES: dict[str, Theme] = {
    "white": Theme(
        name="white",
        canvas=WHITE,
        ink=INK,
        muted=MUTED,
        faint=FAINT,
        rule=RULE,
        tick=SUBTITLE_RULE,
        grid=GRIDLINE,
        accent=RED,
        contrast=BULLS_BLACK,
        band=RED,
        trim_a=WHITE,
        trim_b=BULLS_BLACK,
    ),
    "jersey": Theme(
        name="jersey",
        canvas="#FAF8F5",
        ink="#141414",
        muted="#5F5B57",
        faint="#A19B92",
        rule="#E6E2DB",
        tick="#D6D0C6",
        grid="#F1EEE8",
        accent=RED,
        contrast="#141414",
        band=RED,
        trim_a=WHITE,
        trim_b="#141414",
    ),
    "newsprint": Theme(
        name="newsprint",
        canvas="#F3EDDF",
        ink="#191713",
        muted="#5D5749",
        faint="#948C79",
        rule="#DCD3BF",
        tick="#CBC1A9",
        grid="#EAE2CE",
        accent="#B5123C",
        contrast="#191713",
        band="#191713",
        trim_a="#F3EDDF",
        trim_b="#B5123C",
    ),
    "blackout": Theme(
        name="blackout",
        canvas="#121214",
        ink="#F1EFEC",
        muted="#A7A39E",
        faint="#6F6B66",
        rule="#2B2B30",
        tick="#3A3A40",
        grid="#1B1B1E",
        accent="#FF3355",
        contrast="#F1EFEC",
        band="#FF3355",
        trim_a="#121214",
        trim_b="#F1EFEC",
    ),
    "hardwood": Theme(
        name="hardwood",
        canvas="#BE0E3B",
        ink="#FDF3EA",
        muted="#FBE8E0",
        faint="#E497A4",
        rule="#D15370",
        tick="#D76A81",
        grid="#A70C34",
        accent="#141414",
        contrast="#FDF3EA",
        band="#141414",
        trim_a="#FDF3EA",
        trim_b="#BE0E3B",
    ),
}

DEFAULT_THEME = THEMES["jersey"]


def get_theme(name: str | Theme | None) -> Theme:
    """Resolve a theme by name; None means the default (jersey)."""
    if name is None:
        return DEFAULT_THEME
    if isinstance(name, Theme):
        return name
    try:
        return THEMES[name]
    except KeyError as error:
        options = ", ".join(THEMES)
        raise ValueError(f"Unknown theme '{name}'; choose one of: {options}.") from error

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


def new_canvas(theme: str | Theme | None = None):
    """Create the fixed 1080x1350 full-bleed house canvas.

    ``theme`` selects a canvas theme by name ("jersey", "white",
    "newsprint", "blackout", "hardwood"); omitted means the jersey default.
    """
    theme = get_theme(theme)
    fig = plt.figure(
        figsize=(CANVAS_WIDTH / DRAFT_DPI, CANVAS_HEIGHT / DRAFT_DPI),
        facecolor=theme.canvas,
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(theme.canvas)
    ax.set_xlim(0, CANVAS_WIDTH)
    ax.set_ylim(0, CANVAS_HEIGHT)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax


def draw_jersey_stripe(ax, theme: str | Theme | None = None):
    """Draw the full-bleed jersey-trim band across the top of the canvas.

    Band with two pinstripes, top-down: band 4, trim 2, band 4, trim 2,
    band 4 (16 px total). On the jersey/white themes that is red with one
    white and one black pinstripe; the other themes use their own band/trim
    tokens. Mirrors the ``.band`` element on design-system.html.
    """
    layers = get_theme(theme).stripe_layers
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
    theme: str | Theme | None = None,
):
    """Draw subtitle parts separated by real vertical ticks, never glyphs."""
    theme = get_theme(theme)
    cursor = SIDE_MARGIN
    artists = []
    for index, part in enumerate(parts):
        text, color = part if isinstance(part, tuple) else (part, theme.muted)
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
                color=theme.tick,
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
    theme: str | Theme | None = None,
):
    """Draw the current stripe, title, subtitle, and optional kicker pattern."""
    theme = get_theme(theme)
    artists = list(draw_jersey_stripe(ax, theme)) if stripe else []
    artists.extend(
        draw_fitted_title(ax, title_segments, base_size=title_base_size, outlined=outlined)
    )
    artists.extend(draw_subtitle(ax, subtitle_parts, weight=subtitle_weight, theme=theme))
    if kicker:
        artists.append(
            ax.text(
                SIDE_MARGIN,
                CANVAS_HEIGHT - 206,
                kicker,
                ha="left",
                va="top",
                fontsize=14,
                color=theme.accent,
                style="italic",
                fontproperties=body_font("medium"),
            )
        )
    return artists


def draw_footer(
    ax,
    *,
    source: str = "Data via nba.com",
    note: str | None = None,
    watermark: str = "@chicagobullsdata",
    theme: str | Theme | None = None,
):
    """Draw the required source/watermark footer pair."""
    theme = get_theme(theme)
    left_text = f"{note} · {source}" if note else source
    source_artist = ax.text(
        SIDE_MARGIN,
        FOOTER_Y,
        left_text,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=theme.faint,
        fontproperties=body_font(),
    )
    watermark_artist = ax.text(
        CANVAS_WIDTH - SIDE_MARGIN,
        FOOTER_Y,
        watermark,
        ha="right",
        va="bottom",
        fontsize=10.5,
        color=theme.muted,
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
