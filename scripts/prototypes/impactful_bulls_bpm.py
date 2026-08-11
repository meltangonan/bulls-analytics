"""Build the most-impactful-Bull-per-season BPM carousel chart assets for Canva.

Basketball Reference supplies season-level Box Plus/Minus (BPM 2.0) for every
Bulls player since 2000-01. Each season's most impactful Bull is the qualified
player -- a rotation-sized role held for most of the season -- with the highest
BPM. The carousel splits the run into two even slides by default; one slide per
season-decade is available behind ``--split decades``.

The table format follows scoring_age_ladder.py: square headshots, a red-yellow-
green heat scale on the story columns, and light row rules that stop short of
each heat cell. Row and type sizing follow top_game_performances.py.

BPM is retrodictive and expressed against league average each season, so the
column is comparable across 26 seasons without an era adjustment. It splits
natively into OBPM and DBPM (DBPM = BPM - OBPM).
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from bulls.data.basketball_reference import load_or_fetch_advanced
from bulls.graphics.house import (
    DEFAULT_THEME,
    DRAFT_DPI,
    HEADSHOT_CACHE,
    ensure_headshots,
    export_dpi,
    helvetica,
    rendered_width,
)
from bulls.visuals import DATA, visual_dir

FIRST_SEASON_END = 2001  # 2000-01
LAST_SEASON_END = 2026  # 2025-26

# Qualification: a rotation-sized role, held for most of the season.
#
# Two conditions rather than one number, because each says plainly why a
# player is out. A single flat minutes floor is not one bar but nine: 1,500
# minutes asks 18.3 mpg of an 82-game season and 23.1 mpg of the 65-game
# 2019-20, tightening 26% in shortened years. That artifact is what cut
# Derrick Rose's 2011-12 (39 games at 35.3 mpg) in favour of Joakim Noah.
#
# Neither condition works alone. Games alone hands 2019-20 to Shaquille
# Harrison, who played 43 games at 11 mpg. Minutes-per-game alone hands
# 2018-19 to JaKarr Sampson on 4 games and 127 minutes. Together they agree
# with a 6.86%-of-team-minutes gate on all 26 seasons, and they can be read
# off the graphic without a percentage.
MIN_MINUTES_PER_GAME = 20.0
MIN_TEAM_GAMES_SHARE = 0.50

SNAPSHOT_TZ = ZoneInfo("America/Chicago")

PROJECT = "impactful-bulls-bpm"
OUT = _REPO / "output" / "feed"
# Basketball Reference is rate-limited and the published numbers rest on it, so
# the parsed table is tracked with the post rather than left in ignored cache/.
DATA_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT, create=False) / DATA
ADVANCED_CSV = DATA_DIR / "bulls-advanced-by-season.csv"
LEADERS_CSV = DATA_DIR / "most-impactful-bull-by-season.csv"

# Season decades, matching top_game_performances.py: a decade is bucketed by
# the season's ending year, so the 2000s run 2000-01 (ends 2001) through
# 2009-10 (ends 2010). "Since 2000" therefore starts at 2000-01, not 1999-00.
DECADES = (
    ("2000s", 2001, 2010),
    ("2010s", 2011, 2020),
    ("2020s", 2021, 2026),
)

# The canvas is wider than the 1080 Canva page. The page scales it to fit, so
# the extra width buys air between columns rather than pixels on the page: at
# 1080 the five stat columns could only be made equal by shrinking the faces
# and the names, which are the two things worth protecting.
CHART_WIDTH = 1200
SIDE_MARGIN = 39

# Every column from BPM rightwards is the same width. The widest thing any of
# them holds is the "MPG" header at 71 px, so 104 leaves 16 px of air either
# side and the block reads as one grid rather than five sizes.
#
# "OBPM" measures 94 px at the 15 pt header size against values of about 65,
# so the header, not the data, was setting the width. "OFF"/"DEF" under a BPM
# heading is unambiguous, and the explainer slide spells both out in full.
STAT_COLUMN_WIDTH = 104
STAT_COLUMNS = ("bpm", "obpm", "dbpm", "games", "minutes_per_game")
STAT_HEADERS = {
    "bpm": "BPM",
    "obpm": "OFF",
    "dbpm": "DEF",
    "games": "GP",
    "minutes_per_game": "MPG",
}
# The heat scale covers the three BPM columns; GP and MPG stay plain. Those
# two are the numbers the qualification rests on, so both are shown: 39 games
# (Rose 2011-12) or 48 (Miller 2001-02) reads as an error until the
# minutes-per-game beside it says "starter".
HEAT_COLUMNS = ("bpm", "obpm", "dbpm")
PLAIN_COLUMNS = ("games", "minutes_per_game")

_STAT_BLOCK_RIGHT = CHART_WIDTH - SIDE_MARGIN
_STAT_BLOCK_LEFT = _STAT_BLOCK_RIGHT - STAT_COLUMN_WIDTH * len(STAT_COLUMNS)
STAT_BOUNDS = {
    key: (
        _STAT_BLOCK_LEFT + index * STAT_COLUMN_WIDTH,
        _STAT_BLOCK_LEFT + (index + 1) * STAT_COLUMN_WIDTH,
    )
    for index, key in enumerate(STAT_COLUMNS)
}

ROW_RULE_LEFT = SIDE_MARGIN
BPM_LEFT = STAT_BOUNDS["bpm"][0]
PLAIN_LEFT = STAT_BOUNDS[PLAIN_COLUMNS[0]][0]
TABLE_RIGHT = _STAT_BLOCK_RIGHT

HEAT_RED = "#D64545"
HEAT_YELLOW = "#F2D46B"
HEAT_GREEN = "#3FAE63"

# Colour scale, calibrated from the league distribution rather than from
# Basketball Reference's tier labels or this table's own range.
#
# Over 3,036 qualified NBA player-seasons in this same window (1,500+ minutes,
# 2009-10 to 2025-26), each column's percentiles are:
#
#           1%     5%    25%    50%    75%    95%    99%
#   BPM   -4.40  -3.00  -1.10  +0.40  +2.00  +5.50  +9.20
#   OBPM  -3.50  -2.50  -0.90  +0.40  +1.80  +5.01  +7.60
#   DBPM  -2.46  -1.70  -0.80   0.00  +0.70  +2.00  +3.00
#
# Two things that fixes. Anchoring red at replacement level (-2.0) clamped a
# populated stretch of the distribution -- 10% of qualified players are below
# -2.30 BPM -- into one indistinguishable colour, and it painted -1.0, which
# is the 25th percentile, as near-worst. Standard deviations also differ far
# more than the tier labels suggest: BPM 2.70, OBPM 2.29, DBPM 1.16, which is
# why DBPM gets its own ceiling (the all-time single-season record is Nate
# McMillan's +5.54, so nothing ever approaches the +9.2 BPM allows).
#
# Each column runs 5th to 99th percentile: red is the bottom 5% of NBA
# rotation players, green the top 1%. The asymmetry is deliberate -- a 5th
# floor keeps the low end meaningful, and a 99th ceiling preserves the gap
# between a very good season and a historic one instead of clamping both.
COLUMN_SCALES = {
    "bpm": (-3.0, 9.2),
    "obpm": (-2.5, 7.6),
    "dbpm": (-1.7, 3.0),
}
SCALE_POPULATION = "NBA players with 1,500+ minutes, 2009-10 to 2025-26"
SCALE_PERCENTILES = (5, 99)
SCALE_SAMPLE_SIZE = 3036

# Basketball Reference's own plain-language tiers. These no longer drive the
# colour ramp, but they are what the explainer slide uses to tell a reader
# what a number means.
BPM_TIERS = (
    (10.0, "all-time season"),
    (8.0, "MVP season"),
    (6.0, "all-NBA season"),
    (4.0, "all-star consideration"),
    (2.0, "good starter"),
    (0.0, "league average"),
    (-2.0, "replacement level"),
)

MIN_USABLE_HEADSHOT_BYTES = 50_000

# NBA's CDN serves a generic silhouette for some retired players. ESPN keeps
# real portraits at a stable endpoint, the same fallback scoring_age_ladder.py
# uses. Keyed by NBA player id.
HISTORICAL_HEADSHOT_URLS = {
    2239: "https://a.espncdn.com/i/headshots/nba/players/full/998.png",  # Hassell
}
# Silhouettes with no NBA or ESPN portrait at all. Rendering continues with a
# neutral placeholder and prints a warning, rather than blocking the build on
# a picture that has to be sourced and licence-checked by hand.
ACCEPTED_MISSING_HEADSHOTS = {
    923: "Donyell Marshall (2002-03): no NBA or ESPN portrait exists",
}
# Share of the portrait's height kept by the face crop. NBA headshots are
# 1040x760 with the head in the upper frame, so this drops most of the jersey.
FACE_CROP_HEIGHT_FRACTION = 0.74


@dataclass(frozen=True)
class TableLayout:
    """Row and type sizing for one table page."""

    header_from_top: float
    header_rule_from_top: float
    first_row_from_top: float
    bottom_pad: float
    row_height: float
    season_x: float
    headshot_x: float
    name_x: float
    headshot_half_size: float
    headshot_rise: float
    header_font_size: float
    name_font_size: float
    season_font_size: float
    value_font_size: float
    bpm_font_size: float


# Row and type sizing follow top_game_performances.DECADE_LAYOUT, the most
# recent table the account shipped. Its headline stat is the same size as
# every other value and carries its weight through bold alone; BPM does the
# same here rather than being set larger.
DECADE_LAYOUT = TableLayout(
    header_from_top=59,
    header_rule_from_top=88,
    first_row_from_top=150,
    bottom_pad=56,
    row_height=112,
    # "2000-01" runs ~138 px at 17 pt and ends at 177, so a 116 px face
    # centred at 243 still clears it and stays taller than the row.
    season_x=39,
    headshot_x=243,
    name_x=317,
    headshot_half_size=58,
    headshot_rise=7,
    header_font_size=15,
    name_font_size=19,
    season_font_size=17,
    value_font_size=16,
    bpm_font_size=16,
)
# 13 rows will not fit at the decade layout's 112 px pitch (that lands at
# 1606 px, past a 1080x1350 page), so the halves layout keeps every type size
# and trims the row pitch and padding instead.
TWO_SLIDE_LAYOUT = TableLayout(
    header_from_top=50,
    header_rule_from_top=74,
    first_row_from_top=120,
    bottom_pad=42,
    row_height=84,
    season_x=39,
    headshot_x=229,
    name_x=289,
    headshot_half_size=44,
    headshot_rise=5,
    header_font_size=15,
    name_font_size=19,
    season_font_size=17,
    value_font_size=16,
    bpm_font_size=16,
)
ONE_SLIDE_LAYOUT = TableLayout(
    header_from_top=36,
    header_rule_from_top=60,
    first_row_from_top=100,
    bottom_pad=18,
    row_height=66,
    season_x=47,
    headshot_x=225,
    name_x=281,
    headshot_half_size=42,
    headshot_rise=3,
    header_font_size=13.5,
    name_font_size=16,
    season_font_size=14.5,
    value_font_size=15.5,
    bpm_font_size=15.5,
)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


def _norm(name: str) -> str:
    """Normalize a player name for cross-source joins."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = "".join(c for c in text.lower() if c.isalnum() or c == " ")
    for suffix in (" jr", " iii", " ii", " sr"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text.strip()


def build_working_table(refresh: bool = False) -> pd.DataFrame:
    """Return every Bulls player-season with BPM components in the window."""
    frame = load_or_fetch_advanced(
        ADVANCED_CSV,
        range(FIRST_SEASON_END, LAST_SEASON_END + 1),
        refresh=refresh,
    ).copy()
    frame = frame[frame["season"].between(FIRST_SEASON_END, LAST_SEASON_END)]
    frame["season_label"] = frame["season"].map(
        lambda end: f"{end - 1}-{str(end)[2:]}"
    )
    # The graphic shows "2000–01": four-digit first year, en dash. This is
    # top_game_performances.display_season_label; the working table keeps the
    # plain hyphenated form that filenames and other surfaces use.
    frame["season_short"] = frame["season_label"].str.replace("-", "–", n=1)

    # Team games come from the season's own total minutes (five players for
    # 48 minutes), so a shortened season needs no special case.
    team_minutes = frame.groupby("season")["mp"].transform("sum")
    frame["team_games"] = (team_minutes / 240).round()
    frame["minutes_per_game"] = frame["mp"] / frame["games"]
    frame["games_share"] = frame["games"] / frame["team_games"]
    frame["qualified"] = (
        (frame["minutes_per_game"] >= MIN_MINUTES_PER_GAME)
        & (frame["games_share"] >= MIN_TEAM_GAMES_SHARE)
    )
    return frame.reset_index(drop=True)


def select_leaders(table: pd.DataFrame) -> pd.DataFrame:
    """Return the highest-BPM qualified Bull for each season, newest first.

    BPM ties are real -- Ben Gordon and Joakim Noah both posted +1.1 in
    2008-09 -- so the tiebreak is explicit rather than left to sort order.
    VORP breaks first because it is a published figure for the same season;
    minutes break a VORP tie.
    """
    qualified = table[table["qualified"] & table["bpm"].notna()]
    return (
        qualified.sort_values(
            ["season", "bpm", "vorp", "mp"], ascending=[False, False, False, False]
        )
        .groupby("season", sort=False)
        .head(1)
        .sort_values("season", ascending=False)
        .reset_index(drop=True)
    )


def attach_player_ids(leaders: pd.DataFrame) -> pd.DataFrame:
    """Attach NBA player ids so the working table stays joinable downstream."""
    from nba_api.stats.static import players as static_players

    index: dict[str, list[dict]] = {}
    for player in static_players.get_players():
        index.setdefault(_norm(player["full_name"]), []).append(player)

    def resolve(name: str):
        matches = index.get(_norm(name), [])
        return int(matches[0]["id"]) if len(matches) == 1 else None

    leaders = leaders.copy()
    leaders["nba_id"] = leaders["player_name"].map(resolve)
    return leaders


def validate_working_table(table: pd.DataFrame, leaders: pd.DataFrame) -> dict:
    """Check every claim the graphic will make before it is drawn."""
    expected = list(range(FIRST_SEASON_END, LAST_SEASON_END + 1))
    missing_seasons = sorted(set(expected) - set(leaders["season"]))
    seasons_without_qualifier = sorted(
        season
        for season in expected
        if not table[(table["season"] == season) & table["qualified"]].shape[0]
    )
    decade_counts = {
        name: int(((leaders["season"] >= low) & (leaders["season"] <= high)).sum())
        for name, low, high in DECADES
    }
    ties = []
    for _, row in leaders.iterrows():
        season_rows = table[(table["season"] == row["season"]) & table["qualified"]]
        tied = season_rows[season_rows["bpm"] == season_rows["bpm"].max()]
        if len(tied) > 1:
            ties.append(
                {
                    "season": row["season_label"],
                    "bpm": float(row["bpm"]),
                    "selected": row["player_name"],
                    "selected_vorp": float(row["vorp"]),
                    "passed_over": [
                        {"player": r["player_name"], "vorp": float(r["vorp"])}
                        for _, r in tied.iterrows()
                        if r["player_name"] != row["player_name"]
                    ],
                    "resolved_by": "VORP",
                }
            )

    return {
        "seasons_expected": len(expected),
        "seasons_selected": int(leaders.shape[0]),
        "missing_seasons": missing_seasons,
        "seasons_without_qualifier": seasons_without_qualifier,
        "decade_counts": decade_counts,
        "tied_seasons": ties,
        "unresolved_player_ids": sorted(
            leaders.loc[leaders["nba_id"].isna(), "player_name"].tolist()
        ),
        "null_values": {
            field: int(leaders[field].isna().sum())
            for field in ("games", "mp", "bpm", "obpm", "dbpm")
        },
        "bpm_range": [float(leaders["bpm"].min()), float(leaders["bpm"].max())],
        "split_range": [
            float(min(leaders["obpm"].min(), leaders["dbpm"].min())),
            float(max(leaders["obpm"].max(), leaders["dbpm"].max())),
        ],
        "negative_bpm_seasons": leaders.loc[
            leaders["bpm"] < 0, "season_label"
        ].tolist(),
        "min_minutes_per_game": MIN_MINUTES_PER_GAME,
        "min_team_games_share": MIN_TEAM_GAMES_SHARE,
        "lowest_qualifying_mpg": round(float(leaders["minutes_per_game"].min()), 1),
        "lowest_qualifying_games_share": round(
            float(leaders["games_share"].min()), 3
        ),
    }


def write_working_table(
    table: pd.DataFrame, leaders: pd.DataFrame, date: str
) -> Path:
    """Persist the analysis table beside the fetched inputs it came from."""
    LEADERS_CSV.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "season", "season_label", "player_name", "nba_id",
        "games", "mp", "minutes_per_game", "games_share",
        "bpm", "obpm", "dbpm", "vorp",
    ]
    leaders[columns].to_csv(LEADERS_CSV, index=False)
    return LEADERS_CSV


# --------------------------------------------------------------------------
# Colour and headshots
# --------------------------------------------------------------------------


def _mix(base: str, target: str, strength: float) -> tuple[float, float, float]:
    """Blend two colors using the shared table calculation."""
    amount = min(max(float(strength), 0.0), 1.0)
    base_rgb, target_rgb = to_rgb(base), to_rgb(target)
    return tuple(b + (t - b) * amount for b, t in zip(base_rgb, target_rgb))


def heat_fill(
    value: float, minimum: float, maximum: float
) -> tuple[float, float, float]:
    """Map a value onto the red-yellow-green scale from the age ladder.

    Red is the low end of the column's range and green the high end, so the
    scale reads as rank rather than as the house red/black semantics. Every
    cell prints its own number, which is what keeps a red-to-green ramp usable
    for colourblind readers (DESIGN.md §2).
    """
    span = maximum - minimum
    fraction = 1.0 if span <= 0 else (float(value) - minimum) / span
    fraction = min(max(fraction, 0.0), 1.0)
    if fraction <= 0.5:
        return _mix(HEAT_RED, HEAT_YELLOW, fraction * 2)
    return _mix(HEAT_YELLOW, HEAT_GREEN, (fraction - 0.5) * 2)


def heat_text_color(fill: tuple[float, float, float]) -> str:
    """Black-or-white contrast rule shared with the age ladder."""
    red, green, blue = fill
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#FFFFFF" if luminance < 0.47 else DEFAULT_THEME.ink


def face_headshot_label(ax, image_path, x, y, half_size, *, zorder=4):
    """Place a square crop tight to the face, anchored at the top of the frame.

    ``house.square_headshot_label`` centre-crops the full 1040x760 portrait,
    which keeps the jersey. NBA only publishes era-specific portraits from
    2015-16 onward, so the older rows can only be served by the current
    "latest" image -- Noah in Memphis, Butler in Golden State. Showing that
    uniform on a Bulls graphic reads as an error, and mixing era and current
    portraits would put the same player in two jerseys on one slide. Cropping
    to the face sidesteps both: what is left is the player, not the team.
    """
    try:
        image = plt.imread(image_path)
    except (FileNotFoundError, OSError, ValueError):
        return ax.add_patch(
            Rectangle(
                (x - half_size, y - half_size),
                2 * half_size,
                2 * half_size,
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=zorder,
            )
        )

    height, width = image.shape[:2]
    side = min(int(height * FACE_CROP_HEIGHT_FRACTION), width)
    left = max(0, (width - side) // 2)
    square = image[:side, left:left + side]
    return ax.imshow(
        square,
        extent=[x - half_size, x + half_size, y - half_size, y + half_size],
        interpolation="bilinear",
        zorder=zorder,
    )


def ensure_historical_headshot_fallbacks(player_ids) -> None:
    """Replace known NBA-CDN silhouettes with a real portrait."""
    import requests

    for player_id in {int(pid) for pid in player_ids}:
        url = HISTORICAL_HEADSHOT_URLS.get(player_id)
        if url is None:
            continue
        path = HEADSHOT_CACHE / f"{player_id}.png"
        if path.exists() and path.stat().st_size >= MIN_USABLE_HEADSHOT_BYTES:
            continue
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        if len(response.content) < MIN_USABLE_HEADSHOT_BYTES:
            raise ValueError(f"Fallback portrait for {player_id} is too small.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)


def verify_headshots(player_ids) -> list[int]:
    """Return ids whose cached headshot is the NBA CDN's generic silhouette.

    The silhouette is ~12 KB against 150-220 KB for a real portrait, so size
    is the only reliable tell (DESIGN.md §5).
    """
    missing = []
    for player_id in {int(pid) for pid in player_ids}:
        path = HEADSHOT_CACHE / f"{player_id}.png"
        if not path.exists() or path.stat().st_size < MIN_USABLE_HEADSHOT_BYTES:
            missing.append(player_id)
    return sorted(missing)


# --------------------------------------------------------------------------
# Slide grouping
# --------------------------------------------------------------------------


def decade_groups(leaders: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """One slide per season-decade: 10 / 10 / 6 rows."""
    groups = []
    for name, low, high in DECADES:
        rows = leaders[leaders["season"].between(low, high)]
        groups.append((name, rows.reset_index(drop=True)))
    return groups


def half_groups(leaders: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Two even slides, newest half first.

    A decade split leaves the 2020s six rows short, and against two full
    slides that gap reads as a mistake rather than a choice. 26 seasons halve
    exactly, so neither slide carries dead space.
    """
    ordered = leaders.sort_values("season", ascending=False).reset_index(drop=True)
    midpoint = len(ordered) // 2
    groups = []
    for part in (ordered.iloc[:midpoint], ordered.iloc[midpoint:]):
        part = part.reset_index(drop=True)
        newest = part["season_label"].iloc[0]
        oldest = part["season_label"].iloc[-1]
        groups.append((f"{oldest}-to-{newest}", part))
    return groups


def uniform_row_count(groups) -> int:
    """Rows the largest slide needs; every slide is sized to this.

    A short slide cropped to its own content would land at a different height,
    so the same paste position in Canva would put its rows somewhere else.
    """
    return max(len(rows) for _, rows in groups)


def slide_height(row_count: int, layout: TableLayout) -> float:
    """Canvas height that fits exactly ``row_count`` rows plus the header."""
    return (
        layout.first_row_from_top
        + (row_count - 1) * layout.row_height
        + layout.row_height / 2
        + layout.bottom_pad
    )


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def row_rule_segments() -> tuple[tuple[float, float], ...]:
    """Rule the identity and plain columns, leaving each heat cell whole.

    The left segment also stops short of the headshot column so the faces,
    which are taller than the row, overlap a clean gap rather than a line.
    """
    return ((ROW_RULE_LEFT, BPM_LEFT), (PLAIN_LEFT, TABLE_RIGHT))


def _heat_cell(ax, left, right, y, layout, fill, value, *, bold=False):
    """Draw one edge-to-edge heat cell with its value."""
    ax.add_patch(
        Rectangle(
            (left, y - layout.row_height / 2),
            right - left,
            layout.row_height,
            facecolor=fill,
            edgecolor="none",
            linewidth=0,
            zorder=2,
        )
    )
    ax.text(
        (left + right) / 2,
        y,
        value,
        ha="center",
        va="center",
        fontsize=layout.bpm_font_size if bold else layout.value_font_size,
        color=heat_text_color(fill),
        fontproperties=helvetica("bold" if bold else "regular"),
        zorder=4,
    )


def render_slide(
    rows: pd.DataFrame,
    slug: str,
    date: str,
    layout: TableLayout = DECADE_LAYOUT,
    final: bool = False,
    row_capacity: int | None = None,
) -> Path:
    """Render one transparent table slide for Canva.

    ``row_capacity`` sizes the canvas for that many rows regardless of how
    many this slide holds, so every slide in a carousel exports identically.
    """
    if rows.empty:
        raise ValueError(f"Cannot render an empty slide for {slug}.")

    chart_height = slide_height(row_capacity or len(rows), layout)
    header_y = chart_height - layout.header_from_top
    header_rule_y = chart_height - layout.header_rule_from_top
    first_row_y = chart_height - layout.first_row_from_top

    theme = DEFAULT_THEME
    fig = plt.figure(
        figsize=(CHART_WIDTH / DRAFT_DPI, chart_height / DRAFT_DPI),
        facecolor="none",
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, chart_height)
    ax.axis("off")

    headers = [
        (layout.season_x, "SEASON", theme.ink),
        (layout.name_x, "PLAYER", theme.ink),
    ]
    for key in STAT_COLUMNS:
        left, right = STAT_BOUNDS[key]
        headers.append(
            (
                (left + right) / 2,
                STAT_HEADERS[key],
                theme.accent if key == "bpm" else theme.ink,
            )
        )
    for x, label, color in headers:
        ax.text(
            x,
            header_y,
            label,
            ha="left" if label in ("SEASON", "PLAYER") else "center",
            va="center",
            fontsize=layout.header_font_size,
            color=color,
            fontproperties=helvetica("bold"),
        )
    ax.plot(
        [ROW_RULE_LEFT, TABLE_RIGHT],
        [header_rule_y, header_rule_y],
        color=theme.ink,
        lw=2.0,
        zorder=3,
    )

    for index, (_, row) in enumerate(rows.iterrows()):
        y = first_row_y - index * layout.row_height
        if index:
            divider_y = y + layout.row_height / 2
            for rule_left, rule_right in row_rule_segments():
                ax.plot(
                    [rule_left, rule_right],
                    [divider_y, divider_y],
                    color=theme.rule,
                    linewidth=1.0,
                    zorder=3,
                )

        ax.text(
            layout.season_x,
            y,
            row["season_short"],
            ha="left",
            va="center",
            fontsize=layout.season_font_size,
            color=theme.accent,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        face_headshot_label(
            ax,
            HEADSHOT_CACHE / f"{int(row['nba_id'])}.png",
            layout.headshot_x,
            y + layout.headshot_rise,
            layout.headshot_half_size,
            zorder=4,
        )
        name = ax.text(
            layout.name_x,
            y,
            row["player_name"],
            ha="left",
            va="center",
            fontsize=layout.name_font_size,
            color=theme.ink,
            fontproperties=helvetica("bold"),
            zorder=4,
        )
        # "Donyell Marshall" overruns into the stat block at the base size;
        # shrink only the names that need it rather than the whole column.
        name_budget = BPM_LEFT - layout.name_x - 16
        width = rendered_width(ax, name)
        if width > name_budget:
            name.set_fontsize(layout.name_font_size * name_budget / width)

        for key in HEAT_COLUMNS:
            left, right = STAT_BOUNDS[key]
            value = float(row[key])
            _heat_cell(
                ax, left, right, y, layout,
                heat_fill(value, *COLUMN_SCALES[key]),
                f"{value:+.1f}",
                bold=(key == "bpm"),
            )
        for key in PLAIN_COLUMNS:
            left, right = STAT_BOUNDS[key]
            raw = row[key]
            ax.text(
                (left + right) / 2,
                y,
                f"{int(raw)}" if key == "games" else f"{float(raw):.1f}",
                ha="center",
                va="center",
                fontsize=layout.value_font_size,
                color=theme.ink,
                fontproperties=helvetica("regular"),
                zorder=4,
            )

    path = OUT / f"{date}-impactful-bulls-bpm-{slug}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        dpi=export_dpi(final),
        transparent=True,
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Copy
# --------------------------------------------------------------------------


def canva_copy_block(leaders: pd.DataFrame, report: dict, date: str) -> str:
    """Return exact framing copy from the same validated run."""
    peak = leaders.loc[leaders["bpm"].idxmax()]
    worst = leaders.loc[leaders["bpm"].idxmin()]
    negatives = ", ".join(report["negative_bpm_seasons"]) or "None"
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: Most impactful Bulls each year",
            "",
            "SUBTITLE: Box Plus/Minus since 2000–01",
            "",
            (
                "QUALIFICATION: Highest BPM among Bulls who averaged "
                f"{MIN_MINUTES_PER_GAME:.0f}+ minutes per game in at least "
                f"{MIN_TEAM_GAMES_SHARE:.0%} of the team's games that season."
            ),
            "",
            (
                "DEFINITIONS: BPM = Box Plus/Minus, estimated points per 100 "
                "possessions above league average. OFF and DEF are its "
                "offensive and defensive halves (OBPM and DBPM, which sum to "
                "BPM). GP = games played for Chicago. MPG = minutes per game."
            ),
            "",
            (
                "COLOUR SCALE: each column runs from the "
                f"{SCALE_PERCENTILES[0]}th to the {SCALE_PERCENTILES[1]}th "
                f"percentile of {SCALE_POPULATION} (n={SCALE_SAMPLE_SIZE:,}). "
                + " / ".join(
                    f"{c.upper()} {lo:+.1f} to {hi:+.1f}"
                    for c, (lo, hi) in COLUMN_SCALES.items()
                )
                + ". Reference tiers: "
                + " / ".join(f"{v:+.0f} {label}" for v, label in BPM_TIERS)
            ),
            "",
            (
                "SAMPLE NOTE: BPM reads defense from steals, blocks, and "
                "rebounds only. Its creator advises treating the defensive "
                "column as a guide, not a verdict."
            ),
            "",
            (
                f"PEAK: {peak['player_name']} {peak['season_label']} "
                f"({peak['bpm']:+.1f} BPM)"
            ),
            (
                f"FLOOR: {worst['player_name']} {worst['season_label']} "
                f"({worst['bpm']:+.1f} BPM)"
            ),
            (
                f"SEASONS BELOW LEAGUE AVERAGE: {negatives}"
                if report["negative_bpm_seasons"]
                else "NOTE: every season in this window had at least one "
                "above-average Bull."
            ),
            "",
            f"SOURCE: Data via Basketball Reference · Pulled {date}",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at final DPI; first-review drafts should omit this.",
    )
    parser.add_argument(
        "--split", choices=("halves", "decades"), default="halves",
        help="Two even slides, or one slide per season-decade.",
    )
    parser.add_argument(
        "--one-slide",
        action="store_true",
        help="Also render every season on a single dense slide.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch Basketball Reference instead of using the saved CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    date = datetime.now(SNAPSHOT_TZ).date().isoformat()

    table = build_working_table(args.refresh)
    leaders = attach_player_ids(select_leaders(table))
    report = validate_working_table(table, leaders)

    ensure_headshots(leaders["nba_id"])
    ensure_historical_headshot_fallbacks(leaders["nba_id"])
    silhouettes = verify_headshots(leaders["nba_id"])
    report["silhouette_headshots"] = silhouettes
    unexpected = [i for i in silhouettes if i not in ACCEPTED_MISSING_HEADSHOTS]
    if unexpected:
        raise SystemExit(
            f"Generic silhouette headshots for NBA ids {unexpected}; add a "
            "verified portrait source before rendering."
        )
    for player_id in silhouettes:
        print(f"WARNING: placeholder face -- {ACCEPTED_MISSING_HEADSHOTS[player_id]}")

    table_path = write_working_table(table, leaders, date)

    if args.split == "decades":
        groups, layout = decade_groups(leaders), DECADE_LAYOUT
    else:
        groups, layout = half_groups(leaders), TWO_SLIDE_LAYOUT
    capacity = uniform_row_count(groups)
    slide_paths = [
        render_slide(rows, slug, date, layout=layout,
                     final=args.final, row_capacity=capacity)
        for slug, rows in groups
    ]
    if args.one_slide:
        slide_paths.append(
            render_slide(
                leaders.reset_index(drop=True), "all", date,
                layout=ONE_SLIDE_LAYOUT, final=args.final,
            )
        )

    print(json.dumps(report, indent=2))
    print(f"\nWrote {table_path}")
    for path in slide_paths:
        print(f"Wrote {path}")
    print()
    print(canva_copy_block(leaders, report, date))


if __name__ == "__main__":
    main()
