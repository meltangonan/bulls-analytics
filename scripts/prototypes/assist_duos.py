"""Build the Bulls assist-connections tables: who created the most baskets for whom.

Two slides off one analysis, in the settled ladder-table grammar:

- ``--mode season`` — the top eight connections of the 2025-26 Bulls.
- ``--mode history`` — the top ten single-season Bulls connections since 2000-01, each
  labeled with its season.

Every made basket credited with an assist has two authors. Ranking unordered pairs by
``A assists B + B assists A`` gives the most productive connections; ties break on the
points those baskets were worth, which is self-evident because both numbers are printed.

The **direction column is the point of the post.** A combined total alone hides whether a
connection was a one-way creator-to-finisher pipe or a genuinely two-way relationship, and
that varies enormously: Giddey→Buzelis ran 87% one way in 2025-26 while Vučević↔Buzelis
split 35-34. The split bar carries that in one mark — its color break is the boundary
between the two directions.

Volume post: minutes, role, and ballhandling responsibility drive these totals. This is
"most productive connections," not "best chemistry."

Source and identity matching are documented in ``assist_duos_fetch``. Canva owns the title,
subtitle, coverage line, and handle; these are chart assets only.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch, Rectangle
from nba_api.stats.static import players as static_players

from bulls.visuals import visual_dir
from bulls.graphics.house import (
    DEFAULT_THEME,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
)
from scripts.prototypes.assist_duos_fetch import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    bulls_player_game_logs,
    fetch_season,
    load_history,
    load_player_game_logs,
)
from scripts.prototypes.top_game_performances import decade_for_end_year
from scripts.prototypes.top_game_performances import (
    HISTORICAL_HEADSHOT_URLS,
    MIN_USABLE_HEADSHOT_BYTES,
)

CURRENT_SEASON_END_YEAR = 2026
SEASON_TOP_N = 8
HISTORY_TOP_N = 10

# Two visual projects off one analysis, so the yearly post and the decade board keep
# separate folders under output/ and docs/visuals/ rather than sharing a version history.
YEARLY_PROJECT = "assist-duos"
DECADE_PROJECT = "assist-duos-by-decade"
OUTPUT_ROOT = _REPO / "output"


def project_dir(project: str):
    """Scratch folder for one project, mirroring docs/visuals/<date>-<slug>/."""
    folder = visual_dir(OUTPUT_ROOT, project, create=False)
    folder.mkdir(parents=True, exist_ok=True)
    return folder

CHART_WIDTH = 1500
ROW_RULE_LEFT = 24
DUO_HEADER_X = 46      # inset so the label does not hug the canvas edge

# Faces are anchored so their cropped bottom edge sits on the row's bottom rule and their
# tops rise past the row into the one above, the way the other ladder tables stack. They
# also overlap each other horizontally — the left player is drawn last, over the right —
# by less than the portrait's empty margin, so neither face is covered.
FACE_A_X, FACE_B_X = 80, 182
FACE_HALF = 62
NAME_X = 262

SEASON_LEFT, SEASON_RIGHT = 548, 664
BAR_LEFT_WITH_SEASON, BAR_RIGHT = 700, 1150
BAR_LEFT_NO_SEASON = 570
AST_LEFT, AST_RIGHT = 1180, 1312
GAMES_LEFT, GAMES_RIGHT = 1336, 1476

BAR_VERTICAL_INSET = 15  # bar height is the row height less this, top and bottom
BAR_RADIUS = 10

# Vertical sheen on each bar segment and on the total card, clipped to a rounded patch —
# the same layering clutch_table.py uses for its points card. Top colour first.
RED_BAR_GRADIENT = ("#E12C52", "#A80E35")
DARK_BAR_GRADIENT = ("#333333", "#0C0C0C")
TOTAL_CARD_GRADIENT = ("#D8244F", "#9E0C2E")
SWATCH = 11              # colored square linking a name line to its bar segment
MIN_INSIDE_LABEL_WIDTH = 40

AST_CARD_OUTSET_X = 8
AST_CARD_OUTSET_Y = 9
AST_CARD_OVERLAP_Y = 7


@dataclass(frozen=True)
class TableLayout:
    """Row and type sizing, matching the BPM/game-score/scoring-ladder table family."""

    header_from_top: float
    header_rule_from_top: float
    first_row_from_top: float
    bottom_pad: float
    row_height: float
    headshot_rise: float
    header_font_size: float
    name_font_size: float
    value_font_size: float
    ast_font_size: float
    direction_font_size: float


DUO_LAYOUT = TableLayout(
    header_from_top=56,
    header_rule_from_top=88,
    first_row_from_top=162,   # clears the header rule now that faces rise past the row
    bottom_pad=56,
    row_height=116,
    headshot_rise=4,
    header_font_size=15,
    name_font_size=17,
    value_font_size=17,
    ast_font_size=18,
    direction_font_size=16,
)


# ---------------------------------------------------------------- analysis


def player_names() -> dict[int, str]:
    """Player id -> full name, from nba_api's offline static roster.

    Play-by-play gives only surnames, and a since-2000 post spans players long retired.
    The static table ships with the package (5,000+ players), so no request is needed and
    no season endpoint has to be walked to name a row.
    """
    return {int(p["id"]): p["full_name"] for p in static_players.get_players()}


def build_pairs(events: pd.DataFrame, names: dict[int, str]) -> pd.DataFrame:
    """Collapse assisted baskets into unordered pairs per season, both directions kept.

    Orientation is by volume: ``high_*`` is whichever player fed the other more, so the
    color break in a bar moves rightward as a connection gets more lopsided.
    """
    required = {"assister_id", "scorer_id", "shot_value", "season", "season_end_year"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"Assisted-basket rows are missing {sorted(missing)}")

    directional = (
        events.groupby(["season_end_year", "season", "assister_id", "scorer_id"])
        .agg(ast=("shot_value", "size"), pts=("shot_value", "sum"))
        .reset_index()
    )

    rows = []
    for (end_year, season), block in directional.groupby(["season_end_year", "season"]):
        lookup = {
            (int(r.assister_id), int(r.scorer_id)): (int(r.ast), int(r.pts))
            for r in block.itertuples()
        }
        pairs: dict[tuple[int, int], dict[int, tuple[int, int]]] = {}
        for (assister, scorer), totals in lookup.items():
            if assister == scorer:
                # No scorer assists his own basket. If one appeared, the unordered key
                # would collapse onto a single direction and the combined total would
                # double with nothing downstream noticing.
                raise ValueError(f"Player {assister} credited with assisting himself")
            pairs.setdefault(tuple(sorted((assister, scorer))), {})[assister] = totals

        for (a, b), directions in pairs.items():
            a_ast, a_pts = directions.get(a, (0, 0))
            b_ast, b_pts = directions.get(b, (0, 0))
            if a_ast >= b_ast:
                high, low = (a, a_ast, a_pts), (b, b_ast, b_pts)
            else:
                high, low = (b, b_ast, b_pts), (a, a_ast, a_pts)
            rows.append(
                {
                    "season_end_year": int(end_year),
                    "season": season,
                    "high_id": high[0],
                    "high_name": names.get(high[0], str(high[0])),
                    "high_ast": high[1],
                    "high_pts": high[2],
                    "low_id": low[0],
                    "low_name": names.get(low[0], str(low[0])),
                    "low_ast": low[1],
                    "low_pts": low[2],
                    "combined_ast": high[1] + low[1],
                    "combined_pts": high[2] + low[2],
                }
            )

    frame = pd.DataFrame(rows)
    bad = frame[
        (frame.combined_ast != frame.high_ast + frame.low_ast)
        | (frame.combined_pts != frame.high_pts + frame.low_pts)
    ]
    if not bad.empty:
        raise ValueError("Directions do not sum to their combined totals")

    frame["share_high"] = frame.high_ast / frame.combined_ast
    return frame.sort_values(
        ["combined_ast", "combined_pts"], ascending=False
    ).reset_index(drop=True)


def attach_games_together(pairs: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """Add the count of games both players appeared in, and the per-game assist rate.

    Replaces points as the second column. Points were nearly a restatement of the assist
    total — the two run together at roughly 2.3 points per assist for every duo — where
    shared games explain *why* a total is what it is. The 2025-26 Giddey-Vučević number
    is low because they were available together far less, not because the connection
    changed, and no column on the old board could tell you that.
    """
    appeared = logs[logs.MIN.fillna(0) > 0]
    by_player = {
        (int(end_year), int(player_id)): set(block.GAME_ID)
        for (end_year, player_id), block in appeared.groupby(
            ["season_end_year", "PLAYER_ID"]
        )
    }

    together = []
    for row in pairs.itertuples():
        high = by_player.get((int(row.season_end_year), int(row.high_id)), set())
        low = by_player.get((int(row.season_end_year), int(row.low_id)), set())
        together.append(len(high & low))

    result = pairs.copy()
    result["games_together"] = together
    # A duo can share zero games and still hold a pair row — a midseason trade where one
    # arrived as the other left. The rate is undefined there, not zero.
    shared = result.games_together.astype(float)
    result["ast_per_game"] = result.combined_ast / shared.where(shared > 0)
    return result


DECADES = ("2000s", "2010s", "2020s")


def top_by_decade(pairs: pd.DataFrame, top_n: int = HISTORY_TOP_N) -> dict[str, pd.DataFrame]:
    """The best ``top_n`` single-season connections within each decade.

    Decade boundaries come from ``top_game_performances.decade_for_end_year`` rather than
    being redefined here, so the two carousels cut the same seasons the same way.
    """
    labelled = pairs.assign(decade=pairs.season_end_year.map(decade_for_end_year))
    return {
        decade: labelled[labelled.decade == decade].head(top_n).reset_index(drop=True)
        for decade in DECADES
    }


def best_per_season(
    pairs: pd.DataFrame, *, descending: bool = False
) -> dict[str, pd.DataFrame]:
    """Each season's single best connection, grouped into decade slides.

    The alternative to a straight decade leaderboard. One board can be dominated by one
    era's roster — Hinrich appears in three of the 2000s top five — where this guarantees
    every season a row and reads as a timeline instead of a ranking.

    ``descending`` runs newest season first, so a slide opens on the season a reader just
    watched rather than closing on it.
    """
    best = (
        pairs.sort_values(["combined_ast", "combined_pts"], ascending=False)
        .groupby("season_end_year", as_index=False)
        .first()
    )
    labelled = best.assign(decade=best.season_end_year.map(decade_for_end_year))
    return {
        decade: labelled[labelled.decade == decade]
        .sort_values("season_end_year", ascending=not descending)
        .reset_index(drop=True)
        for decade in DECADES
    }


def display_season(season: str) -> str:
    """'2015-16' -> '2015–16', using an en dash as the rest of the account does."""
    return str(season).replace("-", "–")


# nba_api's static table carries a player's *current legal* name, which is wrong for a
# season-labeled historical post: Ron Artest did not become Metta World Peace until 2011,
# and "M. Peace" is not a name anyone recognises. Key on the season the row represents.
ERA_NAMES: dict[int, dict[str, str]] = {
    1897: {"before": 2012, "name": "Ron Artest"},          # Metta World Peace
}


# NBA.com's registered name is not always the one anybody uses on a graphic. Mirrors
# ``top_game_performances._display_name`` so the two carousels label a player the same way.
DISPLAY_NAME_FIXES = {"Jimmy Butler III": "Jimmy Butler"}


def display_name(full_name: str, player_id: int, season_end_year: int) -> str:
    """The name this player went by during the season being displayed."""
    override = ERA_NAMES.get(int(player_id))
    if override and season_end_year < override["before"]:
        return override["name"]
    return DISPLAY_NAME_FIXES.get(str(full_name), str(full_name))


# The NBA CDN answers an unknown player with a generic grey silhouette rather than a 404,
# and returns the same bytes every time. Fingerprinting it is exact; a byte-size threshold
# is not — the silhouette is 12,430 bytes, comfortably above any "too small" cutoff, which
# is why Carlos Boozer rendered as a grey blob without tripping a warning.
CDN_SILHOUETTE_MD5 = "e7f284977a49"


def is_silhouette(path: Path) -> bool:
    """True when a cached portrait is the CDN's placeholder rather than a real face."""
    if not path.exists():
        return True
    if path.stat().st_size < MIN_USABLE_HEADSHOT_BYTES:
        return True
    return hashlib.md5(path.read_bytes()).hexdigest().startswith(CDN_SILHOUETTE_MD5)


def missing_headshots(player_ids) -> list[int]:
    """Ids with no usable portrait.

    A silhouette is not a failure the eye catches in review — it reads as a design choice
    — so it is reported rather than quietly drawn.
    """
    return sorted(
        player_id
        for player_id in {int(p) for p in player_ids}
        if is_silhouette(HEADSHOT_CACHE / f"{player_id}.png")
    )


# Players the NBA CDN has no portrait for, sourced elsewhere and checked by eye against
# the player each one claims to be. Merged with the game-score carousel's own table.
# Promotion candidate: if a third post needs this, the merged map belongs in house.py.
EXTRA_HEADSHOT_URLS = {
    2430: "https://a.espncdn.com/i/headshots/nba/players/full/1703.png",    # Carlos Boozer
    101126: "https://a.espncdn.com/i/headshots/nba/players/full/2782.png",  # Nate Robinson
}
FALLBACK_HEADSHOT_URLS = {**HISTORICAL_HEADSHOT_URLS, **EXTRA_HEADSHOT_URLS}


def ensure_fallback_headshots(player_ids) -> None:
    """Download a replacement for any portrait the CDN could not supply.

    Replaces the game-score carousel's version rather than calling it, because that one
    treats any cached file above a size floor as usable — and the CDN silhouette clears
    the floor, so it would skip a player who visibly needs the fallback.
    """
    import requests

    for player_id in {int(p) for p in player_ids}:
        url = FALLBACK_HEADSHOT_URLS.get(player_id)
        path = HEADSHOT_CACHE / f"{player_id}.png"
        if not url or not is_silhouette(path):
            continue
        response = requests.get(url, timeout=30)
        if not response.ok or len(response.content) < MIN_USABLE_HEADSHOT_BYTES:
            print(f"WARNING: fallback portrait for {player_id} failed ({url})")
            continue
        image = Image.open(BytesIO(response.content)).convert("RGBA")
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, format="PNG")


# ---------------------------------------------------------------- render


def slide_height(row_count: int, layout: TableLayout = DUO_LAYOUT) -> float:
    """Fit exactly the header and requested rows without transparent dead space."""
    return (
        layout.first_row_from_top
        + (row_count - 1) * layout.row_height
        + layout.row_height / 2
        + layout.bottom_pad
    )


def ast_card_bounds(row_count: int, first_row_y: float, layout: TableLayout):
    """The rounded card footprint behind the combined-assist column."""
    top = first_row_y + layout.row_height / 2 + AST_CARD_OUTSET_Y + AST_CARD_OVERLAP_Y
    bottom = (
        first_row_y
        - (row_count - 1) * layout.row_height
        - layout.row_height / 2
        - AST_CARD_OUTSET_Y
    )
    return AST_LEFT - AST_CARD_OUTSET_X, AST_RIGHT + AST_CARD_OUTSET_X, bottom, top


def _draw_ast_card(ax, row_count: int, first_row_y: float, layout: TableLayout) -> None:
    """The red total column: a shadowed rounded card with a vertical colour ramp."""
    left, right, bottom, top = ast_card_bounds(row_count, first_row_y, layout)
    shape = dict(
        boxstyle="round,pad=0,rounding_size=18", edgecolor="none", linewidth=0,
    )
    ax.add_patch(
        FancyBboxPatch(
            (left, bottom), right - left, top - bottom,
            facecolor=DEFAULT_THEME.accent,
            path_effects=[
                PathEffects.withSimplePatchShadow(
                    offset=(2.5, -3), shadow_rgbFace="#7A1230", alpha=0.32, rho=0.85
                ),
                PathEffects.Normal(),
            ],
            zorder=4,
            **shape,
        )
    )
    clip = FancyBboxPatch(
        (left, bottom), right - left, top - bottom,
        facecolor="none", zorder=4, **shape,
    )
    ax.add_patch(clip)
    _vertical_gradient(
        ax, left, right, (top + bottom) / 2, top - bottom,
        TOTAL_CARD_GRADIENT, clip, 4.5,
    )


def _initials(full_name: str) -> str:
    parts = [p for p in str(full_name).split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


NAME_GUTTER = 40         # clear space between the longest name and the next column
FACE_CROP_HEIGHT = 0.74  # share of the portrait's height kept, as a square


def duo_face_label(ax, image_path, x, y, half, *, zorder=4):
    """Place a portrait cropped to the head, with margin at the sides.

    Keeps the same top-74% crop as the rest of the table family, which frames the head
    and leaves shoulders — and therefore whichever team's jersey a player last wore —
    out of the picture. Only the drawn square is larger here.
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return None

    height, width = image.shape[:2]
    side = min(int(height * FACE_CROP_HEIGHT), width)
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half, x + half, y - half, y + half],
        interpolation="bilinear",
        zorder=zorder,
    )


def _draw_face(ax, player_id: int, name: str, x: float, y: float, half: float, zorder):
    """Draw a portrait, or a monogram tile when no usable portrait exists.

    Some players simply have no portrait anywhere licensable — Greg Anthony and Jay
    Williams are on neither the NBA CDN nor ESPN. The CDN's grey silhouette reads as a
    broken image; initials in the house palette read as a deliberate choice, and stay
    honest about who the row is describing.
    """
    path = HEADSHOT_CACHE / f"{player_id}.png"
    if path.exists():
        # Including the CDN's grey silhouette: it is a portrait-shaped placeholder that
        # sits in the layout correctly, which is preferable to a monogram tile. The
        # monogram is only for a player with no cached image at all.
        return duo_face_label(ax, path, x, y, half, zorder=zorder)

    theme = DEFAULT_THEME
    ax.add_patch(
        FancyBboxPatch(
            (x - half * 0.78, y - half * 0.78),
            half * 1.56,
            half * 1.56,
            boxstyle="round,pad=0,rounding_size=14",
            facecolor="#E4DED6",
            edgecolor=theme.rule,
            linewidth=1.0,
            zorder=zorder,
        )
    )
    ax.text(
        x, y, _initials(name),
        ha="center", va="center", fontsize=half * 0.52,
        color="#6F6A63", fontproperties=helvetica("bold"), zorder=zorder + 0.1,
    )


def _rounded(x0: float, x1: float, y: float, height: float, **kwargs) -> FancyBboxPatch:
    """A rounded box whose outer bounds are exactly (x0, x1) and height."""
    return FancyBboxPatch(
        (x0 + BAR_RADIUS, y - height / 2 + BAR_RADIUS),
        max(x1 - x0 - 2 * BAR_RADIUS, 0.1),
        height - 2 * BAR_RADIUS,
        boxstyle=f"round,pad={BAR_RADIUS},rounding_size={BAR_RADIUS}",
        **kwargs,
    )


def _vertical_gradient(ax, x0, x1, y, height, colors, clip, zorder):
    """Paint a top-to-bottom colour ramp across one span, clipped to a shape."""
    top, bottom = (np.array(to_rgb(c)) for c in colors)
    ramp = np.linspace(bottom, top, 256).reshape(256, 1, 3)
    image = ax.imshow(
        ramp,
        extent=(x0, x1, y - height / 2, y + height / 2),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=zorder,
    )
    image.set_clip_path(clip)
    return image


def _draw_split_bar(ax, bar_left, split, bar_end, y, height) -> None:
    """Draw the two-direction bar as one shadowed, gradient-filled shape.

    Clipping both gradients to a single rounded outline is what makes this read as one
    continuous bar broken by colour rather than two pills pushed together: only the outer
    ends round off, and the split stays a hard vertical edge. It also replaces the old
    square-off patches, which could not have carried a gradient.
    """
    shadow = _rounded(
        bar_left, bar_end, y, height,
        facecolor=DARK_BAR_GRADIENT[1], edgecolor="none", zorder=4,
        path_effects=[
            PathEffects.withSimplePatchShadow(
                offset=(1.5, -2), shadow_rgbFace="#5A5048", alpha=0.30, rho=0.9
            ),
            PathEffects.Normal(),
        ],
    )
    ax.add_patch(shadow)

    clip = _rounded(bar_left, bar_end, y, height,
                    facecolor="none", edgecolor="none", zorder=5)
    ax.add_patch(clip)
    _vertical_gradient(ax, bar_left, split, y, height, RED_BAR_GRADIENT, clip, 5)
    _vertical_gradient(ax, split, bar_end, y, height, DARK_BAR_GRADIENT, clip, 5)


def _direction_label(ax, x0, x1, y, value, color, layout, *, align_outside_left) -> None:
    """Print a directional count inside its segment, or just outside when it will not fit.

    A near-one-way pair leaves the minority segment only a few dozen pixels wide, and a
    number crammed into it would either overflow into the other direction's territory or
    be silently clipped.
    """
    if x1 - x0 >= MIN_INSIDE_LABEL_WIDTH:
        ax.text(
            (x0 + x1) / 2, y, f"{int(value)}",
            ha="center", va="center", fontsize=layout.direction_font_size,
            color="#FFFFFF", fontproperties=helvetica("bold"), zorder=8,
        )
        return
    if align_outside_left:
        ax.text(
            x0 - 7, y, f"{int(value)}",
            ha="right", va="center", fontsize=layout.direction_font_size,
            color=color, fontproperties=helvetica("bold"), zorder=8,
        )
    else:
        ax.text(
            x1 + 7, y, f"{int(value)}",
            ha="left", va="center", fontsize=layout.direction_font_size,
            color=color, fontproperties=helvetica("bold"), zorder=8,
        )


def render_table(
    rows: pd.DataFrame,
    output: Path,
    *,
    show_season: bool,
    scale_max: int | None = None,
    canvas_rows: int | None = None,
    layout: TableLayout = DUO_LAYOUT,
    final: bool = False,
) -> Path:
    """Render one transparent duo table in the settled ladder grammar.

    ``canvas_rows`` fixes the exported height to that many rows regardless of how many
    are drawn, so every slide in a carousel is the same size. A 2020s slide holding six
    seasons otherwise exports shorter than a ten-row 2000s slide, and dropping the two
    into the same Canva frame scales them differently.

    ``scale_max`` sets the assist total that fills the bar column. Pass the carousel-wide
    maximum when rendering a set of slides: readers flip between slides and compare bar
    lengths directly, so per-slide scaling would draw the 2020s leader the same width as
    the 2000s leader and quietly erase the gap between the eras. Defaults to this slide's
    own maximum, which is right for a standalone table.
    """
    rows = rows.reset_index(drop=True)
    player_ids = list(rows.high_id) + list(rows.low_id)
    ensure_headshots(player_ids)
    ensure_fallback_headshots(player_ids)
    absent = missing_headshots(player_ids)
    if absent:
        names = {int(r.high_id): r.high_name for _, r in rows.iterrows()}
        names.update({int(r.low_id): r.low_name for _, r in rows.iterrows()})
        print(
            "WARNING: no usable portrait for "
            + ", ".join(f"{names.get(p, p)} ({p})" for p in absent)
            + " — add a source to HISTORICAL_HEADSHOT_URLS"
        )

    bar_left = BAR_LEFT_WITH_SEASON if show_season else BAR_LEFT_NO_SEASON
    chart_height = slide_height(max(canvas_rows or 0, len(rows)), layout)
    header_y = chart_height - layout.header_from_top
    header_rule_y = chart_height - layout.header_rule_from_top
    first_row_y = chart_height - layout.first_row_from_top

    dpi = export_dpi(final)
    fig = plt.figure(figsize=(CHART_WIDTH / dpi, chart_height / dpi), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, chart_height)
    ax.axis("off")
    theme = DEFAULT_THEME

    headers = [
        # "DUO" sits over the portraits, not over the names, now that the faces are the
        # widest thing in the column.
        (DUO_HEADER_X, "DUO", "left", theme.ink),
        ((bar_left + BAR_RIGHT) / 2, "ASSISTS TO EACH OTHER", "center", theme.ink),
        ((AST_LEFT + AST_RIGHT) / 2, "TOTAL", "center", theme.accent),
        ((GAMES_LEFT + GAMES_RIGHT) / 2, "GAMES", "center", theme.ink),
    ]
    if show_season:
        headers.insert(1, ((SEASON_LEFT + SEASON_RIGHT) / 2, "SEASON", "center", theme.ink))
    for x, label, alignment, color in headers:
        ax.text(
            x, header_y, label, ha=alignment, va="center",
            fontsize=layout.header_font_size, color=color,
            fontproperties=helvetica("bold"),
        )

    ax.plot(
        [ROW_RULE_LEFT, GAMES_RIGHT], [header_rule_y] * 2,
        color=theme.ink, linewidth=2.0, zorder=3,
    )

    _draw_ast_card(ax, len(rows), first_row_y, layout)
    ceiling = int(scale_max) if scale_max else int(rows.combined_ast.max())
    if ceiling < int(rows.combined_ast.max()):
        raise ValueError("scale_max is below a value on this slide; bars would overflow")
    scale = (BAR_RIGHT - bar_left) / ceiling
    bar_height = layout.row_height - 2 * BAR_VERTICAL_INSET

    # One name size for the whole slide. Shrinking only the rows that overflow left the
    # column looking ragged, with "Tomas Satoransky" visibly smaller than "Tre Jones"
    # two rows below it. Measure every name once, then fit them all to the longest.
    name_budget = ((SEASON_LEFT if show_season else bar_left) - NAME_GUTTER) - (NAME_X + SWATCH + 10)
    probe = ax.text(0, -999, "", fontproperties=helvetica("bold"),
                    fontsize=layout.name_font_size)
    widest = 0.0
    for row in rows.itertuples():
        for name, player_id in ((row.high_name, row.high_id), (row.low_name, row.low_id)):
            probe.set_text(display_name(name, player_id, int(row.season_end_year)))
            widest = max(widest, rendered_width(ax, probe))
    probe.remove()
    name_font_size = layout.name_font_size
    if widest > name_budget:
        name_font_size *= name_budget / widest

    for index, row in rows.iterrows():
        y = first_row_y - index * layout.row_height

        if index:
            divider_y = y + layout.row_height / 2
            for rule_left, rule_right in (
                (ROW_RULE_LEFT, AST_LEFT - AST_CARD_OUTSET_X),
                (AST_RIGHT + AST_CARD_OUTSET_X, GAMES_RIGHT),
            ):
                ax.plot(
                    [rule_left, rule_right], [divider_y] * 2,
                    color=theme.rule, linewidth=1.0, zorder=3,
                )

        # Anchor the crop's bottom edge on the row's bottom rule; the head then rises
        # past the row top into the row above. Later rows draw over earlier ones, so a
        # lower player's head overlaps the neck of the one above, like stacked cards.
        face_y = y - layout.row_height / 2 + FACE_HALF
        face_zorder = 4 + index * 0.01
        # Right player first so the left one overlaps him, reading as a pairing rather
        # than two unrelated portraits.
        for face_x, player_id, name in (
            (FACE_B_X, int(row.low_id), row.low_name),
            (FACE_A_X, int(row.high_id), row.high_name),
        ):
            _draw_face(ax, player_id, name, face_x, face_y, FACE_HALF, face_zorder)

        # A swatch ties each name line to its own bar segment, so "first name = red =
        # left segment" does not have to be inferred.
        for line_y, name, player_id, color in (
            (y + 15, row.high_name, row.high_id, theme.accent),
            (y - 15, row.low_name, row.low_id, theme.contrast),
        ):
            ax.add_patch(
                Rectangle(
                    (NAME_X, line_y - SWATCH / 2), SWATCH, SWATCH,
                    facecolor=color, edgecolor="none", zorder=5,
                )
            )
            ax.text(
                NAME_X + SWATCH + 10, line_y,
                display_name(name, player_id, int(row.season_end_year)),
                ha="left", va="center", fontsize=name_font_size,
                color=theme.ink, fontproperties=helvetica("bold"), zorder=5,
            )

        if show_season:
            ax.text(
                (SEASON_LEFT + SEASON_RIGHT) / 2, y, display_season(row.season),
                ha="center", va="center", fontsize=layout.value_font_size,
                color=theme.ink, fontproperties=helvetica("bold"), zorder=5,
            )

        split = bar_left + row.high_ast * scale
        bar_end = bar_left + row.combined_ast * scale
        _draw_split_bar(ax, bar_left, split, bar_end, y, bar_height)
        _direction_label(
            ax, bar_left, split, y, row.high_ast, theme.accent, layout,
            align_outside_left=True,
        )
        _direction_label(
            ax, split, bar_end, y, row.low_ast, theme.contrast, layout,
            align_outside_left=False,
        )

        ax.text(
            (AST_LEFT + AST_RIGHT) / 2, y, f"{int(row.combined_ast)}",
            ha="center", va="center", fontsize=layout.ast_font_size,
            color="#FFFFFF", fontproperties=helvetica("bold"), zorder=7,
        )
        ax.text(
            (GAMES_LEFT + GAMES_RIGHT) / 2, y, f"{int(row.games_together)}",
            ha="center", va="center", fontsize=layout.value_font_size,
            color=theme.ink, fontproperties=helvetica("bold"), zorder=5,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, transparent=True)
    plt.close(fig)
    return output


# ---------------------------------------------------------------- cli


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("season", "history", "both"), default="both")
    parser.add_argument("--final", action="store_true", help="export at final DPI")
    parser.add_argument(
        "--date", default=date.today().isoformat(), help="date stamp for filenames"
    )
    args = parser.parse_args()

    names = player_names()

    if args.mode in ("season", "both"):
        events = fetch_season(CURRENT_SEASON_END_YEAR)
        pairs = attach_games_together(
            build_pairs(events, names),
            bulls_player_game_logs(CURRENT_SEASON_END_YEAR),
        ).head(SEASON_TOP_N)
        out = project_dir(YEARLY_PROJECT)
        pairs.to_csv(out / f"{args.date}-assist-duos-season.csv", index=False)
        path = render_table(
            pairs, out / f"{args.date}-assist-duos-season.png",
            show_season=False, final=args.final,
        )
        print(pairs[["high_name", "high_ast", "low_name", "low_ast",
                     "combined_ast", "combined_pts"]].to_string(index=False))
        print(f"season slide: {path}\n")

    if args.mode in ("history", "both"):
        events = load_history(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR)
        pairs = attach_games_together(
            build_pairs(events, names),
            load_player_game_logs(FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR),
        )
        project_dir(YEARLY_PROJECT).joinpath(
            f"{args.date}-assist-duos-history.csv"
        ).write_text(pairs.to_csv(index=False))

        columns = ["season", "high_name", "high_ast", "low_name", "low_ast",
                   "combined_ast", "games_together", "ast_per_game"]
        # Newest season first: the slide opens on the season a reader just watched.
        # Ascending stays available through best_per_season(descending=False).
        variants = {
            "decade": top_by_decade(pairs),
            "yearly-desc": best_per_season(pairs, descending=True),
        }
        for variant, slides in variants.items():
            # One scale and one canvas height across the whole carousel, so the eras
            # stay comparable and every slide drops into an identical Canva frame.
            populated = [rows for rows in slides.values() if len(rows)]
            ceiling = max(int(rows.combined_ast.max()) for rows in populated)
            canvas_rows = max(len(rows) for rows in populated)
            # The decade board is its own post idea, so it keeps its own folder.
            out = project_dir(
                DECADE_PROJECT if variant == "decade" else YEARLY_PROJECT
            )
            for index, (decade, rows) in enumerate(slides.items(), 1):
                if rows.empty:
                    print(f"WARNING: no rows for {decade}")
                    continue
                path = render_table(
                    rows,
                    out / f"{args.date}-assist-duos-{variant}-{index:02d}-{decade}.png",
                    show_season=True,
                    scale_max=ceiling,
                    canvas_rows=canvas_rows,
                    final=args.final,
                )
                print(f"\n{variant} · {decade} ({len(rows)} rows) -> {path.name}")
                print(rows[columns].to_string(index=False))


if __name__ == "__main__":
    main()
