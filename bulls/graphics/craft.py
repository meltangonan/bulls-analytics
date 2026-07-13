"""Shared craft helpers for feed-post builders.

Small structural techniques — magnitude-colored bars, stacked labels,
threshold footers, headshot annotations — reusable across post builders.
Data fetching stays out of this layer: callers pass values and image
paths (resolve player ids via bulls.data.fetch.get_player_headshot).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import numpy as np
from matplotlib.colors import Colormap, LinearSegmentedColormap
from matplotlib.image import AxesImage
from matplotlib.patches import Rectangle

from bulls.graphics.house import FAINT, INK, MUTED, RED, RULE, body_font

# Light neutral at vmin -> Bulls red -> deep Bulls red at vmax.
MAGNITUDE_CMAP = LinearSegmentedColormap.from_list(
    "bulls_magnitude", ["#F2EAE8", "#CE1141", "#7E0C2B"]
)

# Names longer than this collapse to "F. Lastname" (impact_board rule).
_MAX_NAME_LEN = 16

# Matches the short side of NBA CDN headshots so zoom behaves the same
# for placeholders and real photos.
_PLACEHOLDER_PX = 190


def _truncate_name(name: str) -> str:
    """Collapse names longer than 16 characters to 'F. Lastname'."""
    if len(name) > _MAX_NAME_LEN and " " in name:
        first, rest = name.split(" ", 1)
        name = f"{first[0]}. {rest}"
    return name


def gradient_bar(
    ax: plt.Axes,
    y: float,
    value: float,
    vmin: float,
    vmax: float,
    x0: float = 0.0,
    length: float = 1.0,
    height: float = 0.6,
    cmap: Optional[Colormap] = None,
) -> Rectangle:
    """Draw a horizontal stat bar whose solid fill color encodes magnitude.

    The bar grows from x0 in data coordinates: zero width at vmin, full
    length at vmax. Fill is sampled from a light-neutral-to-deep-Bulls-red
    colormap at the same normalized position.

    Args:
        ax: Target axes
        y: Vertical center of the bar (data coords)
        value: Stat value to encode
        vmin: Value mapped to the light end (zero width)
        vmax: Value mapped to the dark end (full length)
        x0: Left edge of the bar
        length: Bar length at vmax
        height: Bar height
        cmap: Override colormap (defaults to MAGNITUDE_CMAP)

    Returns:
        The Rectangle patch added to the axes.
    """
    cmap = cmap or MAGNITUDE_CMAP
    span = vmax - vmin
    frac = 0.0 if span <= 0 else (value - vmin) / span
    frac = min(max(frac, 0.0), 1.0)

    bar = Rectangle(
        (x0, y - height / 2), frac * length, height,
        facecolor=cmap(frac), edgecolor="none", zorder=2,
    )
    ax.add_patch(bar)
    return bar


def stacked_label(
    ax: plt.Axes,
    x: float,
    y: float,
    primary: str,
    secondary: str,
    ha: str = "left",
    gap: float = 0.04,
    primary_size: float = 15,
    secondary_size: float = 11,
    primary_color: str = INK,
    secondary_color: str = MUTED,
) -> tuple[mtext.Text, mtext.Text]:
    """Draw a two-line label: bold primary line above a muted secondary line.

    Primary names longer than 16 characters collapse to "F. Lastname" so
    all builders share identical name handling.

    Args:
        ax: Target axes
        x: Horizontal anchor (data coords)
        y: Vertical center between the two lines (data coords)
        primary: Player name (bold, ink)
        secondary: Context line (muted)
        ha: Horizontal alignment for both lines
        gap: Vertical offset of each line from y

    Returns:
        (primary_text, secondary_text) artists.
    """
    primary_text = ax.text(
        x, y + gap, _truncate_name(primary),
        ha=ha, va="center", fontsize=primary_size, color=primary_color,
        fontproperties=body_font("bold"),
    )
    secondary_text = ax.text(
        x, y - gap, secondary,
        ha=ha, va="center", fontsize=secondary_size, color=secondary_color,
        fontproperties=body_font("medium"),
    )
    return primary_text, secondary_text


def threshold_footer(
    fig: plt.Figure,
    qualification: str,
    coverage: str,
    source: str = "data: stats.nba.com",
    x: float = 0.055,
    y: float = 0.03,
    ha: str = "left",
    fontsize: float = 8.5,
) -> mtext.Text:
    """Render the fairness-guardrail footer at the bottom of a figure.

    One line joining qualification rule, coverage window, and source,
    e.g. "Min. 20 games | 2025-26 season through Jul 4 | data: stats.nba.com".

    Args:
        fig: Target figure
        qualification: Qualification rule (e.g. "Min. 20 games")
        coverage: Coverage window (e.g. "2025-26 season through Jul 4")
        source: Data source credit
        x: Horizontal position (figure fraction)
        y: Vertical position (figure fraction)

    Returns:
        The Text artist added to the figure.
    """
    line = " | ".join(part for part in (qualification, coverage, source) if part)
    return fig.text(
        x, y, line,
        ha=ha, va="bottom", fontsize=fontsize, color=FAINT,
        fontproperties=body_font(),
    )


def _make_circular_headshot(
    img_path: Path,
    border_color: Optional[tuple] = None,
    border_frac: float = 0.035,
) -> Optional[np.ndarray]:
    """Load an image, crop to circle, optionally add a colored border ring."""
    try:
        img = mpimg.imread(str(img_path))
    except Exception:
        return None

    h, w = img.shape[:2]
    sq = min(h, w)
    x_start = (w - sq) // 2
    img = img[:sq, x_start:x_start + sq]

    h, w = img.shape[:2]
    Y, X = np.ogrid[:h, :w]
    center = h // 2
    outer_mask = ((X - center) ** 2 + (Y - center) ** 2) <= center ** 2

    # Ensure RGBA
    if img.shape[2] == 3:
        if img.dtype == np.uint8:
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        else:
            alpha = np.ones((h, w, 1), dtype=img.dtype)
        img = np.concatenate([img, alpha], axis=2)

    # Paint border ring
    if border_color is not None:
        border_px = max(int(center * border_frac), 2)
        inner_radius = center - border_px
        inner_mask = ((X - center) ** 2 + (Y - center) ** 2) <= inner_radius ** 2
        ring = outer_mask & ~inner_mask
        if img.dtype == np.uint8:
            img[ring] = [int(c) for c in border_color[:3]] + [255]
        else:
            img[ring] = [c / 255 for c in border_color[:3]] + [1.0]

    # Transparency outside circle
    if img.dtype == np.uint8:
        img[~outer_mask, 3] = 0
    else:
        img[~outer_mask, 3] = 0.0

    return img


def _placeholder_disc(size: int = _PLACEHOLDER_PX) -> np.ndarray:
    """RGBA disc (light gray fill, muted ring) for missing headshots."""
    Y, X = np.ogrid[:size, :size]
    center = size // 2
    dist_sq = (X - center) ** 2 + (Y - center) ** 2
    outer = dist_sq <= center ** 2
    ring_px = max(int(center * 0.06), 2)
    ring = outer & (dist_sq >= (center - ring_px) ** 2)

    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[outer] = [232, 232, 232, 255]
    img[ring] = [119, 119, 119, 255]
    return img


def headshot_label(
    ax: plt.Axes,
    image_path: Optional[Path | str],
    x: float,
    y: float,
    radius: float = 34.0,
    border_color: Optional[tuple] = None,
) -> AxesImage:
    """Place a circular headshot centered at (x, y).

    Sized by ``radius`` in the axes' data coordinates, so the rendered
    size is independent of the source image's pixel dimensions (NBA CDN
    photos and the placeholder disc differ). When image_path is None,
    missing, or unreadable, a neutral placeholder disc is drawn instead
    of raising, so builders never break on a player without a cached
    photo.

    Args:
        ax: Target axes
        image_path: Path to a headshot image, or None
        x: Horizontal center (data coords)
        y: Vertical center (data coords)
        radius: Half the rendered diameter (data coords)
        border_color: Optional RGB tuple (0-255) for a border ring

    Returns:
        The AxesImage artist added to the axes.
    """
    circular = None
    if image_path is not None:
        path = Path(image_path)
        if path.exists():
            circular = _make_circular_headshot(path, border_color=border_color)
    if circular is None:
        circular = _placeholder_disc()

    return ax.imshow(
        circular,
        extent=[x - radius, x + radius, y - radius, y + radius],
        zorder=3,
        interpolation="bilinear",
    )
