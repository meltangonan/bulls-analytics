"""Shared chart utilities and compatibility helpers for older full-page posts.

Current charts use Helvetica, export DPI, portraits, and table/card helpers.
Canva owns page layout. Theme palettes, canvas, header, and footer functions
remain for historical renderers; they are not the starting point for new posts.
See DESIGN.md for the current chart contract.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageFilter


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
BLACK = "#242424"  # Current chart black.
# Compatibility palette for historical renderers; new charts use BLACK/RED.
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
    above. The palettes retain the earlier full-layout themes,
    promoted to real render options (DESIGN.md (Color and hierarchy)).
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

def display_font() -> fm.FontProperties:
    """Compatibility alias for legacy layouts; repository text is Helvetica."""
    return helvetica("bold")


def body_font(weight: str = "regular") -> fm.FontProperties:
    """Compatibility alias for legacy layouts; medium maps to Helvetica Bold."""
    if weight not in {"regular", "medium", "bold"}:
        raise ValueError("Unsupported Helvetica weight; choose regular, medium, or bold.")
    return helvetica("regular" if weight == "regular" else "bold")


_HELVETICA_TTC = Path("/System/Library/Fonts/Helvetica.ttc")
# Face index within Helvetica.ttc. Oblique is Helvetica's italic — the family
# has no true italic, and asking matplotlib for style="italic" by family name
# silently renders upright, exactly as asking for bold does.
_HELVETICA_FACES = {
    "regular": 0,
    "bold": 1,
    "oblique": 2,
    "bold_oblique": 3,
}
_FONT_CACHE_DIR = REPO_ROOT / "cache" / "fonts"


def _helvetica_fallback(weight: str) -> fm.FontProperties:
    """Installed-sans fallback that still honours slant (non-macOS)."""
    return fm.FontProperties(
        family=["Helvetica", "Arial", "DejaVu Sans"],
        weight="bold" if weight.startswith("bold") else "normal",
        style="italic" if weight.endswith("oblique") else "normal",
    )


def helvetica(weight: str = "regular") -> fm.FontProperties:
    """Return a Helvetica face for chart assets, extracting real Bold.

    Helvetica Bold is the account's body face; charts are assembled into Canva
    pages that use it, so chart labels must match. matplotlib registers only the
    Regular face of ``Helvetica.ttc``, so asking for ``weight="bold"`` by family
    name silently renders regular. Split the requested face out of the
    collection once into the ignored cache directory and load it by filename
    instead. Extraction stays in ``cache/`` so the licensed system font is never
    copied into the repository. Falls back to an installed sans-serif when
    Helvetica is unavailable (non-macOS).

    Accepts ``regular``, ``bold``, ``oblique`` and ``bold_oblique``. Helvetica
    has no true italic; Oblique is its slanted face and is what "italic" means
    for this account.
    """
    if not _HELVETICA_TTC.exists():
        return _helvetica_fallback(weight)
    extracted = _FONT_CACHE_DIR / f"Helvetica-{weight}.ttf"
    if not extracted.exists():
        try:
            from fontTools.ttLib import TTCollection

            collection = TTCollection(str(_HELVETICA_TTC))
            _FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            collection.fonts[_HELVETICA_FACES.get(weight, 0)].save(str(extracted))
        except Exception:
            return _helvetica_fallback(weight)
    return fm.FontProperties(fname=str(extracted))


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
    tokens. Retained for older full-layout renders.
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
    """Draw a multi-color Helvetica title fitted to the house margins.

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


HEADSHOT_CACHE = REPO_ROOT / "cache" / "headshots"

# NBA.com serves this exact generic silhouette for players it has no portrait
# for. It is also the honest mark for a player whose only available photograph
# still has its background: consistent, obviously a placeholder, and never
# mistaken for the player himself.
NBA_PLACEHOLDER_SHA256 = (
    "e366885fc4212e3a4100f49ed48ad866fd05b32e2d25898c2c24205e789e2632"
)
SILHOUETTE_PATH = HEADSHOT_CACHE / "_silhouette.png"
SILHOUETTE_SOURCE_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/1.png"
# Cut-out portraits run 45-65% transparent; a photograph with its background
# intact is 0%. Nothing observed on historical Bulls players falls between.
MIN_TRANSPARENT_FRACTION = 0.15
_BACKGROUND_REMOVED_CACHE: dict[Path, bool] = {}


def ensure_silhouette(path: Path = SILHOUETTE_PATH) -> Path:
    """Cache the league's generic silhouette, verified by its exact digest."""
    if path.exists():
        return path
    response = requests.get(
        SILHOUETTE_SOURCE_URL,
        headers={"User-Agent": "bulls-analytics/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    if digest != NBA_PLACEHOLDER_SHA256:
        raise ValueError(f"NBA silhouette digest changed: {digest}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return path


def background_removed(path: str | Path) -> bool:
    """Report whether a portrait is a cut-out rather than a flat photograph.

    Mixing the two in one chart is what makes a row or a dot look pasted in:
    a rectangle of background reads as a different kind of mark, not as the
    same mark with a worse source photo.
    """
    path = Path(path)
    cached = _BACKGROUND_REMOVED_CACHE.get(path)
    if cached is not None:
        return cached
    try:
        alpha = np.array(Image.open(path).convert("RGBA"))[:, :, 3]
    except (FileNotFoundError, OSError, ValueError):
        result = False
    else:
        result = bool((alpha < 16).mean() >= MIN_TRANSPARENT_FRACTION)
    _BACKGROUND_REMOVED_CACHE[path] = result
    return result


def portrait_path(player_id: int) -> Path:
    """Give a player his cut-out portrait, or the silhouette when he has none."""
    path = HEADSHOT_CACHE / f"{int(player_id)}.png"
    return path if background_removed(path) else SILHOUETTE_PATH



def square_headshot_label(
    ax,
    image_path: str | Path,
    x: float,
    y: float,
    half_size: float,
    *,
    zorder: float = 8,
    face_fraction: float | None = None,
):
    """Place a square center crop of a headshot, with no border ring.

    ``face_fraction`` takes the square from the top of the portrait instead of
    its middle, keeping the given fraction of the image height. Small marks
    need it: a centre crop of an NBA portrait is mostly jersey, and at 40px the
    face is the only part a reader can still identify.

    The landscape scatter family plots players as bare square faces; the red
    ring in ``craft.headshot_label`` means "this is the payoff" and would read
    as an emphasis that a whole-roster layer does not intend (docs/design/tables-cards.md (Portraits)).

    Returns the placed artist so the caller can set a per-player draw order.
    A missing or unreadable file becomes a neutral placeholder square, so a
    builder never breaks on one absent portrait.
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            FancyBboxPatch(
                (x - half_size, y - half_size),
                2 * half_size,
                2 * half_size,
                boxstyle="square,pad=0",
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=zorder,
            )
        )

    height, width = image.shape[:2]
    if face_fraction is None:
        side = min(height, width)
        top = max(0, (height - side) // 2)
    else:
        side = min(int(height * face_fraction), width)
        top = 0
    left = max(0, (width - side) // 2)
    square = image[top:top + side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )


def ensure_headshots(nba_ids) -> None:
    """Populate the shared NBA CDN cache for every id that is not cached yet."""
    from bulls.data.fetch import get_player_headshot

    for nba_id in nba_ids:
        nba_id = int(nba_id)
        if not (HEADSHOT_CACHE / f"{nba_id}.png").exists():
            get_player_headshot(nba_id)


# --- Conditional-fill scale for table posts (DESIGN.md) ------------------------
#
# The red-white-green cell scale shared by the Assist Leaders, Most Impactful and
# rookie tables. The midpoint is the canvas colour rather than a yellow, so a
# cell that says nothing remarkable disappears into the page.
HEAT_RED = "#D64545"
HEAT_MID = DEFAULT_THEME.canvas
HEAT_GREEN = "#3FAE63"


def _heat_mix(base: str, target: str, strength: float) -> tuple[float, float, float]:
    """Blend two scale colours by a 0-1 strength."""
    amount = min(max(float(strength), 0.0), 1.0)
    base_rgb = np.array(to_rgb(base))
    target_rgb = np.array(to_rgb(target))
    return tuple(base_rgb * (1 - amount) + target_rgb * amount)


def heat_fill(
    value: float,
    red_at: float,
    neutral_low: float,
    neutral_high: float,
    green_at: float,
) -> tuple[float, float, float]:
    """Colour one cell against a fixed reference, not against its own column.

    Anything between ``neutral_low`` and ``neutral_high`` stays the page colour.
    That band is the point: with a single midpoint every cell except an exact
    tie takes some tint, so a table shimmers at values that mean nothing.

    Outside the band a value ramps toward whichever end it heads for, and the
    ends may sit on either side of it — so a column where low is good runs green
    downward with no separate inverted code path. Collapsing the band onto
    ``red_at`` makes a column sequential, with no red end at all.

    Calibrate the four numbers from the population the chart is about, never
    from the chart's own minimum and maximum: a scale anchored on one outlier
    describes the outlier rather than the field.
    """
    value = float(value)
    green_span = green_at - neutral_high
    red_span = red_at - neutral_low
    green_offset = value - neutral_high
    red_offset = value - neutral_low
    if green_span and green_offset * green_span > 0:
        return _heat_mix(HEAT_MID, HEAT_GREEN, min(green_offset / green_span, 1.0))
    if red_span and red_offset * red_span > 0:
        return _heat_mix(HEAT_MID, HEAT_RED, min(red_offset / red_span, 1.0))
    return to_rgb(HEAT_MID)


def heat_text_color(fill: tuple[float, float, float]) -> str:
    """Black or white text, whichever survives on this fill."""
    red, green, blue = fill
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#FFFFFF" if luminance < 0.47 else DEFAULT_THEME.ink


# --- Accent card behind a table's hero column (DESIGN.md) ---------------------
#
# The continuous rounded block the game-score table runs behind Game Score, and
# the rookie leaderboard runs behind PRA/75. It marks the one column the table
# is sorted by, so a reader knows what the ranking means before reading a label.
ACCENT_CARD_OUTSET_X = 8
ACCENT_CARD_OUTSET_Y = 9
ACCENT_CARD_OVERLAP_Y = 7
ACCENT_CARD_ROUNDING = 18
ACCENT_CARD_SHADOW = "#8A1737"


def accent_card_bounds(
    left: float,
    right: float,
    first_row_y: float,
    row_count: int,
    row_height: float,
    outset_y: float = ACCENT_CARD_OUTSET_Y,
    overlap_y: float = ACCENT_CARD_OVERLAP_Y,
) -> tuple[float, float, float, float]:
    """Footprint of the hero card: one block spanning every row, slightly out.

    It reaches a little past the column on all four sides, and further at the
    top, so it overlaps the header rule instead of butting against it. That
    overlap is what makes it read as a card sitting on the table rather than as
    one more cell in it.
    """
    return (
        left - ACCENT_CARD_OUTSET_X,
        right + ACCENT_CARD_OUTSET_X,
        first_row_y - (row_count - 1) * row_height - row_height / 2 - outset_y,
        first_row_y + row_height / 2 + outset_y + overlap_y,
    )


def draw_accent_card(
    ax,
    left: float,
    right: float,
    first_row_y: float,
    row_count: int,
    row_height: float,
    theme: str | Theme | None = None,
    zorder: float = 4,
    outset_y: float = ACCENT_CARD_OUTSET_Y,
    overlap_y: float = ACCENT_CARD_OVERLAP_Y,
) -> tuple[float, float, float, float]:
    """Draw the rounded, shadowed accent card and return its bounds.

    The fill is flat accent. What reads as a gradient is the drop shadow, offset
    down-right and darkened toward a deeper red, which lifts the card off the
    page without a second colour.
    """
    resolved = get_theme(theme)
    bounds = accent_card_bounds(
        left, right, first_row_y, row_count, row_height, outset_y, overlap_y
    )
    card_left, card_right, bottom, top = bounds
    ax.add_patch(
        FancyBboxPatch(
            (card_left, bottom),
            card_right - card_left,
            top - bottom,
            boxstyle=f"round,pad=0,rounding_size={ACCENT_CARD_ROUNDING}",
            facecolor=resolved.accent,
            edgecolor="none",
            linewidth=0,
            path_effects=[
                pe.withSimplePatchShadow(
                    offset=(2, -2),
                    shadow_rgbFace=ACCENT_CARD_SHADOW,
                    alpha=0.22,
                    rho=0.8,
                ),
                pe.Normal(),
            ],
            zorder=zorder,
        )
    )
    return bounds


# --- Turning a flat portrait into a usable cut-out ----------------------------
#
# A portrait only earns a place beside NBA CDN cut-outs if its background is
# genuinely gone (see `background_removed`). Some good historical photographs
# arrive as a clean subject on flat white instead, which reads as pasted-in.
# This converts one into the shape the renderer expects.
NBA_PORTRAIT_SIZE = (1040, 760)
# The face crop takes the top 74% of an NBA headshot, so a supplied portrait is
# scaled into that square and the rest of the canvas left empty.
PORTRAIT_CROP_FRACTION = 0.74


def cut_out_flat_background(
    source: str | Path,
    destination: str | Path,
    tolerance: int = 18,
) -> Path:
    """Make a portrait's flat surround transparent and frame it like an NBA one.

    The background is found by flooding inward from the edges rather than by
    erasing every pale pixel, so teeth, eyes and jersey highlights survive — a
    plain "white becomes transparent" rule punches holes through the player.

    The result is pasted into a canvas with NBA headshot proportions so the same
    face crop that works on CDN portraits frames this one the same way.
    """
    from collections import deque

    image = Image.open(source).convert("RGBA")
    pixels = np.array(image)
    height, width = pixels.shape[:2]
    rgb = pixels[:, :, :3].astype(int)

    pale = (rgb.min(axis=2) >= 255 - tolerance) & (np.ptp(rgb, axis=2) <= tolerance)
    background = np.zeros((height, width), dtype=bool)
    queue = deque()
    for x in range(width):
        for y in (0, height - 1):
            if pale[y, x] and not background[y, x]:
                background[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if pale[y, x] and not background[y, x]:
                background[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and pale[ny, nx] and not background[ny, nx]:
                background[ny, nx] = True
                queue.append((ny, nx))

    pixels[:, :, 3] = np.where(background, 0, 255)
    cut_out = Image.fromarray(pixels)
    # Feather the boundary so the edge does not read as cut with scissors.
    alpha = cut_out.getchannel("A").filter(ImageFilter.GaussianBlur(0.8))
    cut_out.putalpha(alpha)

    canvas_w, canvas_h = NBA_PORTRAIT_SIZE
    crop_side = int(canvas_h * PORTRAIT_CROP_FRACTION)
    scale = min(crop_side / cut_out.width, crop_side / cut_out.height)
    resized = cut_out.resize(
        (max(1, int(cut_out.width * scale)), max(1, int(cut_out.height * scale))),
        Image.LANCZOS,
    )
    canvas = Image.new("RGBA", NBA_PORTRAIT_SIZE, (0, 0, 0, 0))
    canvas.paste(
        resized,
        ((canvas_w - resized.width) // 2, max(0, crop_side - resized.height)),
        resized,
    )
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)
    return destination


def top_anchored_headshot_label(ax, image_path, x, y, half_size, *, crop_fraction=0.68, scale=1.0, zorder=5):
    """Draw a transparent portrait cropped from the top of its source frame.

    ``crop_fraction`` selects the source square; ``scale`` changes its drawn
    size when a wider crop needs to retain the same face size. A missing image
    keeps the standard placeholder footprint. Coordinates use the axes' units.
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            FancyBboxPatch(
                (x - half_size, y - half_size),
                2 * half_size,
                2 * half_size,
                boxstyle="square,pad=0",
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=zorder,
            )
        )

    height, width = image.shape[:2]
    side = max(1, round(min(height, width) * crop_fraction))
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    drawn = half_size * scale
    return ax.imshow(
        square,
        extent=[x - drawn, x + drawn, y - drawn, y + drawn],
        interpolation="bilinear",
        zorder=zorder,
    )
