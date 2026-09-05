"""Render every qualified Bulls rookie season since 2000, newest class first.

The population is NBA.com's explicit regular-season Rookie filter for Chicago,
qualified at 300 Bulls minutes. NBA.com supplies the box score, on-court net
rating, and each player's original overall draft position, printed as a caption
under his name rather than as a column. Basketball Reference supplies true
shooting; Win Shares stays in the working CSV but is no longer a table column.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from io import BytesIO
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import commonplayerinfo
from PIL import Image

from bulls.data import fetch
from bulls.graphics.craft import draw_table_cell
from bulls.graphics.house import (
    DEFAULT_THEME,
    HEAT_GREEN,
    HEAT_MID,
    HEAT_RED,
    HEADSHOT_CACHE,
    MIN_TRANSPARENT_FRACTION,
    NBA_PLACEHOLDER_SHA256,
    SILHOUETTE_PATH,
    background_removed,
    ensure_headshots,
    ensure_silhouette,
    export_dpi,
    heat_fill,
    heat_text_color,
    helvetica,
    portrait_path,
    rendered_width,
)
from bulls.visuals import DATA, visual_dir
from scripts.prototypes.bulls_rookie_metric_analysis import (
    LEAGUE_TS_CSV,
    WORKING_CSV,
    normalize_name,
)

PROJECT = "bulls-rookie-landscape"
MIN_MINUTES = 300
DATA_DIR = visual_dir(
    _REPO / "docs" / "visuals", PROJECT, when="2026-08-14"
) / DATA
DRAFT_CSV = DATA_DIR / "nba-rookie-draft-info.csv"
DISPLAY_CSV = DATA_DIR / "bulls-rookie-chronological-table.csv"
ON_OFF_CSV = DATA_DIR / "databallr-bulls-on-off-snapshot.csv"
LEAGUE_TOV_CSV = DATA_DIR / "nba-league-rookie-tov-by-season.csv"
OUTPUT_DIR = _REPO / "output" / "2026-08-14-bulls-rookie-landscape"

CHART_WIDTH = 1080
TABLE_LEFT = 18
TABLE_RIGHT = 1062

HEADER_FROM_TOP = 66
HEADER_RULE_FROM_TOP = 88
# Clear the rule's own thickness, so the first colored cell starts at the black
# line's lower edge rather than underneath it. Small enough to still read as
# flush, large enough that the fill never eats into the separator.
HEADER_RULE_CLEARANCE = 1.5
# The first row sits flush under the rule: half a row below it, so the top edge
# of the first colored cell meets the separator with no gap and no overlap.
ROW_HEIGHT = 66
FIRST_ROW_FROM_TOP = HEADER_RULE_FROM_TOP + ROW_HEIGHT / 2 + HEADER_RULE_CLEARANCE
BOTTOM_PAD = 34

# The portrait is deliberately taller than the row, so neighbouring faces
# overlap slightly. This is the game-score and BPM performance table treatment.
HEADSHOT_X = 62
HEADSHOT_HALF_SIZE = 42
HEADSHOT_RISE = 4
NAME_X = 112
NAME_FONT_SIZE = 16.0
CAPTION_FONT_SIZE = 11.2
SEASON_FONT_SIZE = 9.6
VALUE_FONT_SIZE = 14.5
HEADER_FONT_SIZE = 13.0
NAME_RISE = 10
CAPTION_DROP = 15
# Breathing room between the longest name in the pool and the first statistic.
NAME_GAP = 18

# Three slides, newest first, as even as the season boundaries allow: the only
# alternatives that keep a rookie class whole are 18/15/13 and 18/18/10, both
# of which strand more empty rows. Sixteen and seventeen read as the same slide
# length; the short one is last, where a reader notices it least.
#
# Note that 46 rookies across three slides does not fit a 1080x1350 page at
# full size. The 17-row canvas is 1246px tall against roughly 875px of usable
# page height, so the asset is placed smaller than page width in Canva. Four
# slides of twelve would have rendered at 96%; three is the editorial choice.
PAGE_SEASON_RANGES = ((2016, 2026), (2005, 2015), (2001, 2004))
PAGE_ROW_COUNTS = (16, 17, 13)

# Steals and blocks are separate columns, and every statistic gets one identical
# width so no category reads as more important because of its box size.
STAT_COLUMNS = (
    ("games", "GP"),
    ("mpg", "MPG"),
    ("ppg", "PTS"),
    ("rpg", "REB"),
    ("apg", "AST"),
    ("spg", "STL"),
    ("bpg", "BLK"),
    ("ts_pct", "TS%"),
    ("impact", "ON/OFF"),
)
SHADED_METRICS = (
    "ppg",
    "rpg",
    "apg",
    "spg",
    "bpg",
    "ts_pct",
    "impact",
)

# Colour scale, calibrated from the rookie distribution rather than from this
# table's own best and worst rows, following the same reasoning as the BPM post.
#
# Reference population: 1,147 NBA rookie seasons at 300+ minutes, 2000-01 to
# 2025-26 — every rookie, not only Chicago's. Percentiles:
#
#            25th   50th   75th   90th   95th
#   PTS      4.12   5.94   8.78  12.32  14.68
#   REB      1.91   2.80   4.04   5.46   6.81
#   AST      0.65   1.09   1.98   3.27   4.20
#   STL      0.35   0.52   0.75   1.02   1.20
#   BLK      0.13   0.26   0.49   0.87   1.15
#
# The five counting columns are SEQUENTIAL: low equals neutral, so nothing
# below the rookie median takes any colour at all. A guard with 0.1 blocks or
# 0.4 steals is not a bad rookie, he is a guard — that is a role, not a
# failure, and painting it red said something untrue. Only production that
# genuinely stands out among rookies earns green.
#
# TS% and ON/OFF are DIVERGING, because each is already a rate: neither rewards
# a player for having a large role, so a low value really is worse rather than
# merely smaller. TS% is coloured on the gap to that season's league average, so
# 2001 and 2025 are judged on equal terms even though the printed percentage is
# raw.
#
# TOV% was a column here and was cut: it is a fair measure, but nine columns of
# heat is more than a phone screen can carry, and turnovers were the one the
# reader could most easily do without. `tov_pct` stays in the working CSV.
# Each entry is (red_at, neutral_low, neutral_high, green_at). Everything
# BETWEEN the two neutral values is left blank — a dead band, not a single
# midpoint. With one midpoint every cell except an exact tie took some tint, so
# the middle of the table shimmered pink and green at values that meant nothing.
# The band states the rule plainly: ordinary is not worth colouring.
COLUMN_SCALES = {
    # Sequential: the band collapses onto the rookie 75th percentile, so nothing
    # below it is coloured at all and green arrives at the 95th.
    "ppg": (8.78, 8.78, 8.78, 14.68),
    "rpg": (4.04, 4.04, 4.04, 6.81),
    "apg": (1.98, 1.98, 1.98, 4.20),
    "spg": (0.75, 0.75, 0.75, 1.20),
    "bpg": (0.49, 0.49, 0.49, 1.15),
    # Points of true shooting above or below that season's league average, at
    # the rookie 5th / 25th / 75th / 95th percentile. The middle half of all
    # rookies is blank; red is the bottom quarter, green the top quarter.
    "ts_pct": (-11.92, -6.38, 0.55, 5.67),
    # Zero stays the mid mark, because zero is the one value each impact measure
    # genuinely means something at: the team broke even with him on the floor,
    # or was no different with him than without him. The band is +/-2 per 100
    # possessions, which at these sample sizes is not a real difference.
    "impact": (-10.0, -2.0, 2.0, 10.0),
}
# Below this many minutes an on-off number is mostly noise, so the cell is left
# blank rather than shaded. It applies to the on/off variant only.
MIN_IMPACT_MINUTES = 750
# TS% is judged against the season it happened in, not its raw value.
ERA_RELATIVE_METRICS = ("ts_pct",)
SCALE_POPULATION = "NBA rookies with 300+ minutes, 2000-01 to 2025-26"
SCALE_SAMPLE_SIZE = 1147


def slide_height(row_count: int = 0) -> float:
    """Give every slide one identical canvas, sized to the fullest one.

    A carousel is read by swiping, so slides that differ in height would jump
    under the reader's thumb and would each need their own Canva crop. The
    canvas is therefore fixed to the longest slide; shorter slides simply end
    early. ``row_count`` is accepted for callers that measure a single slide.
    """
    rows = max(row_count, max(PAGE_ROW_COUNTS))
    return (
        FIRST_ROW_FROM_TOP
        + (rows - 1) * ROW_HEIGHT
        + ROW_HEIGHT / 2
        + BOTTOM_PAD
    )


def column_bounds(stats_left: float) -> dict[str, tuple[float, float, str]]:
    """Divide the space right of the name block into equal statistic columns."""
    width = (TABLE_RIGHT - stats_left) / len(STAT_COLUMNS)
    return {
        metric: (stats_left + index * width, stats_left + (index + 1) * width, label)
        for index, (metric, label) in enumerate(STAT_COLUMNS)
    }

# NBA.com's current CDN serves this same generic silhouette for several
# historical players. Use a real, source-specific portrait when that exact
# placeholder is present; the files still live in the shared ignored cache.
# Every entry here is a cut-out portrait with a genuinely removed background.
# Flat news and college photographs were tried for six other players and
# dropped: they carry their own backgrounds, so they cannot sit in a row beside
# cut-out portraits without looking pasted in. Those players use the silhouette.
HISTORICAL_HEADSHOT_URLS = {
    1434: "https://api.olympiacosbc.gr/media/cache/person_header/media/persons-web/2025/05/6815fbdb17e05320434755.png",
    2648: "https://a.espncdn.com/i/headshots/nba/players/full/2214.png",
    2768: "https://a.espncdn.com/i/headshots/nba/players/full/2377.png",
    200748: "https://a.espncdn.com/i/headshots/nba/players/full/3032.png",
    201189: "https://a.espncdn.com/i/headshots/nba/players/full/3207.png",
    203104: "https://a.espncdn.com/i/headshots/nba/players/full/6626.png",
}



def fetch_draft_info(player_ids: list[int]) -> pd.DataFrame:
    """Fetch official career draft metadata, one row per NBA player ID."""
    rows = []
    for index, player_id in enumerate(player_ids):
        frame = commonplayerinfo.CommonPlayerInfo(
            player_id=int(player_id),
            timeout=60,
            headers=fetch._NBA_HEADERS,
        ).get_data_frames()[0]
        if frame.empty:
            raise ValueError(f"NBA.com returned no player info for {player_id}")
        row = frame.iloc[0]
        rows.append(
            {
                "player_id": int(row["PERSON_ID"]),
                "nba_player_name": str(row["DISPLAY_FIRST_LAST"]),
                "draft_year": str(row["DRAFT_YEAR"]),
                "draft_round": str(row["DRAFT_ROUND"]),
                "draft_number": str(row["DRAFT_NUMBER"]),
            }
        )
        if index < len(player_ids) - 1:
            time.sleep(0.6)
    return pd.DataFrame(rows)


def load_or_fetch_draft_info(
    player_ids: list[int], path: Path = DRAFT_CSV, refresh: bool = False
) -> pd.DataFrame:
    """Use the tracked NBA.com snapshot when it covers the qualified pool."""
    expected = {int(value) for value in player_ids}
    if path.exists() and not refresh:
        cached = pd.read_csv(path, dtype={"draft_number": str, "draft_round": str})
        if expected.issubset(set(cached["player_id"].astype(int))):
            return cached
    result = fetch_draft_info(sorted(expected))
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    return result


def draft_label(value: object) -> str:
    """Format an overall draft slot compactly, preserving undrafted status."""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "undrafted"}:
        return "UDFA"
    try:
        return f"PK{int(float(text))}"
    except ValueError as exc:
        raise ValueError(f"Unrecognized NBA draft number: {value!r}") from exc


def attach_impact(table: pd.DataFrame) -> pd.DataFrame:
    """Fill the impact column with databallr's on-court minus off-court rating.

    On/off is hand-captured because NBA.com serves no on/off before 2007-08. It
    was chosen over NBA.com's own on-court net rating, which is still fetched
    into the working CSV as `net_rating`: that measure grades the rookie's
    teammates as much as the rookie, reading -7.3 for Tyson Chandler and -4.6
    for Kirk Hinrich, where on/off has them at +3.5 and +6.0.

    Removing the team baseline costs stability, because subtracting two noisy
    estimates compounds the error — so the column is blanked below
    `MIN_IMPACT_MINUTES` rather than shown as if it were solid.
    """
    table = table.copy()
    snapshot = pd.read_csv(ON_OFF_CSV)
    snapshot["key"] = snapshot["player_name"].map(normalize_name)
    table["key"] = table["player_name"].map(normalize_name)
    merged = table.merge(
        snapshot[["season", "key", "net_on_off"]],
        on=["season", "key"],
        how="left",
        validate="one_to_one",
    )
    missing = merged.loc[merged["net_on_off"].isna(), "player_name"]
    if len(missing):
        raise ValueError(f"No captured on/off row for: {sorted(missing)}")
    merged["impact"] = merged["net_on_off"].where(
        merged["minutes"].ge(MIN_IMPACT_MINUTES)
    )
    return merged.drop(columns=["key"])


def era_relative_ts(frame: pd.DataFrame) -> pd.Series:
    """Express each TS% as points above or below that season's league average.

    The cell prints the raw percentage, because that is the number a reader
    recognises, but the colour is judged on this. A 52% true-shooting season
    was strong in 2001 and poor in 2025; colouring the raw value would rank
    eras rather than rookies.
    """
    league = pd.read_csv(LEAGUE_TS_CSV)[["season", "league_ts_pct"]]
    league = league.rename(columns={"season": "season_label"})
    merged = frame[["season_label", "ts_pct"]].merge(
        league, on="season_label", how="left", validate="many_to_one"
    )
    if merged["league_ts_pct"].isna().any():
        missing = sorted(
            merged.loc[merged["league_ts_pct"].isna(), "season_label"].unique()
        )
        raise ValueError(f"No league TS baseline for seasons: {missing}")
    relative = (merged["ts_pct"] - merged["league_ts_pct"]) * 100
    return relative.to_numpy()


def era_relative_tov(frame: pd.DataFrame) -> pd.Series:
    """Express each turnover rate against that season's rookie median.

    The cell prints the raw rate, but the colour is judged on this. Rookies
    turned the ball over on 14.6% of their possessions in the early 2000s and
    12.7% today, so a fixed bar would grade eras rather than rookies.
    """
    league = pd.read_csv(LEAGUE_TOV_CSV)[["season", "league_rookie_tov_pct"]]
    merged = frame[["season", "tov_pct"]].merge(
        league, on="season", how="left", validate="many_to_one"
    )
    if merged["league_rookie_tov_pct"].isna().any():
        missing = sorted(
            merged.loc[merged["league_rookie_tov_pct"].isna(), "season"].unique()
        )
        raise ValueError(f"No league rookie turnover baseline for: {missing}")
    return (merged["tov_pct"] - merged["league_rookie_tov_pct"]).to_numpy()


def draft_caption(draft_year: object, draft_number: object) -> str:
    """Spell out the draft slot, because a caption carries no column header.

    The year is the player's own draft, not his rookie season, so the gap shows
    where there is one — Dragan Tarlac was a 1995 pick who first played in
    2000-01, and Omer Asik a 2008 pick who arrived in 2010-11.

    Undrafted players carry no year: NBA.com records `Undrafted` in the year
    field too, and guessing which draft they went unpicked in would be inventing
    a fact the source does not hold.
    """
    label = draft_label(draft_number)
    if label == "UDFA":
        return "Undrafted"
    return f"{draft_year}, #{label[2:]} pick"


def season_marker(season: object) -> str:
    """Compact a season label for the small superscript beside a name."""
    return str(season)[2:].replace("-", "–", 1)


def ensure_historical_headshot_fallbacks(player_ids) -> None:
    """Replace exact NBA-CDN silhouettes with verified historical portraits."""
    for player_id in {int(value) for value in player_ids}:
        url = HISTORICAL_HEADSHOT_URLS.get(player_id)
        if url is None:
            continue
        path = HEADSHOT_CACHE / f"{player_id}.png"
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != NBA_PLACEHOLDER_SHA256:
                continue
        response = requests.get(
            url,
            headers={"User-Agent": "bulls-analytics/1.0"},
            timeout=30,
        )
        response.raise_for_status()
        if len(response.content) < 5_000:
            raise ValueError(f"Historical portrait for {player_id} is too small.")
        image = Image.open(BytesIO(response.content)).convert("RGBA")
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, format="PNG")


def prepare_table(rookies: pd.DataFrame, draft: pd.DataFrame) -> pd.DataFrame:
    """Create the display-ready, chronologically ordered 300-minute table."""
    required = {
        "season",
        "season_label",
        "player_id",
        "player_name",
        "games",
        "minutes",
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "ts_pct",
        "ws",
        "bpm",
    }
    missing = required - set(rookies.columns)
    if missing:
        raise ValueError(f"Rookie table is missing {sorted(missing)}")
    draft_required = {"player_id", "draft_number", "draft_round", "draft_year"}
    missing_draft = draft_required - set(draft.columns)
    if missing_draft:
        raise ValueError(f"Draft table is missing {sorted(missing_draft)}")

    qualified = rookies.loc[rookies["minutes"].ge(MIN_MINUTES)].copy()
    if len(qualified) != 46:
        raise ValueError(f"Expected 46 rookies at 300+ minutes, found {len(qualified)}")
    if qualified.duplicated(["season", "player_id"]).any():
        raise ValueError("Qualified rookie table contains duplicate player-seasons")
    if draft["player_id"].duplicated().any():
        raise ValueError("Draft table contains duplicate player IDs")

    qualified = qualified.merge(
        draft[["player_id", "draft_year", "draft_round", "draft_number"]],
        on="player_id",
        how="left",
        validate="many_to_one",
    )
    if qualified["draft_number"].isna().any():
        names = qualified.loc[qualified["draft_number"].isna(), "player_name"]
        raise ValueError("Missing draft information for " + ", ".join(names))

    qualified["draft_label"] = qualified["draft_number"].map(draft_label)
    qualified["draft_caption"] = [
        draft_caption(year, number)
        for year, number in zip(qualified["draft_year"], qualified["draft_number"])
    ]
    qualified["mpg"] = qualified["minutes"] / qualified["games"]
    qualified["ppg"] = qualified["points"] / qualified["games"]
    qualified["rpg"] = qualified["rebounds"] / qualified["games"]
    qualified["apg"] = qualified["assists"] / qualified["games"]
    qualified["spg"] = qualified["steals"] / qualified["games"]
    qualified["ts_pct_relative"] = era_relative_ts(qualified)
    # Turnovers per possession the player actually used. Raw turnovers per game
    # measured how often he had the ball, which punished the creators.
    qualified["tov_pct"] = (
        qualified["turnovers"]
        / (
            qualified["field_goal_attempts"]
            + 0.44 * qualified["free_throw_attempts"]
            + qualified["turnovers"]
        )
        * 100
    )
    qualified["tov_pct_relative"] = era_relative_tov(qualified)
    qualified["bpg"] = qualified["blocks"] / qualified["games"]
    if "turnovers" not in qualified:
        raise ValueError("Rookie source must include turnovers for the settled table")
    qualified["tov_per_game"] = qualified["turnovers"] / qualified["games"]

    output = qualified[
        [
            "season",
            "season_label",
            "player_id",
            "player_name",
            "draft_year",
            "draft_round",
            "draft_number",
            "draft_label",
            "draft_caption",
            "games",
            "minutes",
            "mpg",
            "ppg",
            "rpg",
            "apg",
            "spg",
            "bpg",
            "ts_pct_relative",
            "tov_per_game",
            "tov_pct",
            "tov_pct_relative",
            "ts_pct",
            "ws",
            "bpm",
            "net_rating",
        ]
    ].sort_values(["season", "minutes", "player_name"], ascending=[False, False, True])
    return output.reset_index(drop=True)


def split_pages(table: pd.DataFrame) -> list[pd.DataFrame]:
    """Split on fixed season boundaries so no rookie class crosses a page."""
    pages = []
    for lower, upper in PAGE_SEASON_RANGES:
        page = table.loc[table["season"].ge(lower) & table["season"].le(upper)].copy()
        pages.append(page.reset_index(drop=True))
    if sum(map(len, pages)) != len(table):
        raise ValueError("Chronological page boundaries lost one or more rows")
    if tuple(len(page) for page in pages) != PAGE_ROW_COUNTS:
        raise ValueError(f"Unexpected page sizes: {[len(page) for page in pages]}")
    return pages


def heat_scales(table: pd.DataFrame | None = None) -> dict[str, tuple[float, float, float]]:
    """Return the fixed reference scale every slide shares.

    The table argument is ignored. It is kept so the call site reads the same
    as the other table posts, and as a reminder that this scale deliberately
    does not depend on which rookies happen to be in the pool.
    """
    return dict(COLUMN_SCALES)


def shaded_value(row: pd.Series, metric: str) -> float:
    """Give a column the number its colour scale is actually calibrated on."""
    if metric in ERA_RELATIVE_METRICS:
        return float(row[f"{metric}_relative"])
    return float(row[metric])


def headshot_clip_bounds(row_y: float) -> tuple[float, float, float, float]:
    """Give the portrait room above its row but a hard floor at its separator.

    A face may rise into the row above it, which is the overlap the game-score
    table uses. It may never spill downward: the shoulders stop at this row's
    own separator, so no portrait intrudes on the row beneath it.
    """
    left = HEADSHOT_X - HEADSHOT_HALF_SIZE
    bottom = row_y - ROW_HEIGHT / 2
    top = row_y + HEADSHOT_RISE + HEADSHOT_HALF_SIZE
    return left, bottom, 2 * HEADSHOT_HALF_SIZE, top - bottom


def _face_headshot(ax, player_id: int, row_y: float) -> None:
    """Draw the face-focused square crop, clipped at this row's separator."""
    y = row_y + HEADSHOT_RISE
    clip_left, clip_bottom, clip_width, clip_height = headshot_clip_bounds(row_y)
    path = portrait_path(player_id)
    try:
        image = plt.imread(path)
    except (FileNotFoundError, OSError, ValueError):
        ax.add_patch(
            Rectangle(
                (clip_left, clip_bottom),
                clip_width,
                clip_height,
                facecolor="#DDD8D1",
                edgecolor="none",
                zorder=4,
            )
        )
        return
    height, width = image.shape[:2]
    side = min(int(height * 0.74), width)
    left = max(0, (width - side) // 2)
    crop = image[:side, left:left + side]
    artist = ax.imshow(
        crop,
        extent=[
            HEADSHOT_X - HEADSHOT_HALF_SIZE,
            HEADSHOT_X + HEADSHOT_HALF_SIZE,
            y - HEADSHOT_HALF_SIZE,
            y + HEADSHOT_HALF_SIZE,
        ],
        interpolation="bilinear",
        zorder=4,
    )
    artist.set_clip_path(
        Rectangle(
            (clip_left, clip_bottom),
            clip_width,
            clip_height,
            transform=ax.transData,
        )
    )


def _name_block_width(ax, name: str, season: str) -> float:
    """Measure one fitted name plus its superscript season marker."""
    season_font = helvetica("regular")
    season_font.set_style("italic")
    season_probe = ax.text(
        0, 0, season_marker(season), fontsize=SEASON_FONT_SIZE,
        fontproperties=season_font, alpha=0,
    )
    season_width = rendered_width(ax, season_probe)
    season_probe.remove()
    name_probe = ax.text(
        NAME_X, 0, name, ha="left", va="center", fontsize=NAME_FONT_SIZE,
        fontproperties=helvetica("bold"), alpha=0,
    )
    name_width = rendered_width(ax, name_probe)
    name_probe.remove()
    return name_width + 5 + season_width


def display_name(value: object) -> str:
    """Drop generational suffixes, as the recent table family does."""
    return str(value).removesuffix(" III").removesuffix(" Jr.")


def measure_stats_left(table: pd.DataFrame) -> float:
    """Start the statistics right after the widest name in the whole pool.

    The columns must line up across all three slides, so this measures every
    qualified rookie once rather than each slide independently. It is what
    keeps the gap between the name and GP as small as the longest name allows.
    """
    fig = plt.figure(figsize=(CHART_WIDTH / 100, slide_height(1) / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, slide_height(1))
    ax.axis("off")
    widest = max(
        _name_block_width(ax, display_name(row["player_name"]), str(row["season_label"]))
        for _, row in table.iterrows()
    )
    plt.close(fig)
    return NAME_X + widest + NAME_GAP


def _draw_player(ax, row: pd.Series, y: float) -> None:
    """Draw the portrait, the fitted name, its season, and the draft caption."""
    _face_headshot(ax, int(row["player_id"]), y)
    name = display_name(row["player_name"])
    name_artist = ax.text(
        NAME_X, y + NAME_RISE, name, ha="left", va="center",
        fontsize=NAME_FONT_SIZE, color=DEFAULT_THEME.ink,
        fontproperties=helvetica("bold"), zorder=5,
    )
    season_font = helvetica("regular")
    season_font.set_style("italic")
    ax.text(
        NAME_X + rendered_width(ax, name_artist) + 5,
        y + NAME_RISE + 7,
        season_marker(str(row["season_label"])),
        ha="left", va="center", fontsize=SEASON_FONT_SIZE,
        color=DEFAULT_THEME.muted, fontproperties=season_font, zorder=5,
    )
    ax.text(
        NAME_X, y - CAPTION_DROP, str(row["draft_caption"]),
        ha="left", va="center", fontsize=CAPTION_FONT_SIZE,
        color=DEFAULT_THEME.muted, fontproperties=helvetica("regular"), zorder=5,
    )


def render_page(
    page: pd.DataFrame,
    full_table: pd.DataFrame,
    page_number: int,
    output_path: Path,
    stats_left: float,
    final: bool = False,
) -> Path:
    """Render one transparent, Canva-ready chronological table asset."""
    theme = DEFAULT_THEME
    header_font = helvetica("bold")
    body_font = helvetica("regular")
    scales = heat_scales(full_table)
    columns = column_bounds(stats_left)

    height = slide_height(len(page))
    header_y = height - HEADER_FROM_TOP
    header_rule_y = height - HEADER_RULE_FROM_TOP
    first_row_y = height - FIRST_ROW_FROM_TOP

    fig = plt.figure(figsize=(CHART_WIDTH / 100, height / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")

    ax.text(NAME_X, header_y, "ROOKIE", ha="left", va="center",
            fontsize=HEADER_FONT_SIZE + 1, color=theme.ink, fontproperties=header_font)
    for left, right, label in columns.values():
        ax.text((left + right) / 2, header_y, label, ha="center", va="center",
                fontsize=HEADER_FONT_SIZE, color=theme.ink, fontproperties=header_font)
    ax.plot([TABLE_LEFT, TABLE_RIGHT], [header_rule_y, header_rule_y],
            color=theme.ink, linewidth=1.5, zorder=3, solid_capstyle="butt")

    for row_index, row in page.iterrows():
        y = first_row_y - row_index * ROW_HEIGHT
        if row_index < len(page) - 1:
            # One unbroken rule across the whole row, drawn above the fills.
            # Ruling only the plain cells left no separator wherever two blank
            # cells met, which is now most of the table.
            rule_y = y - ROW_HEIGHT / 2
            ax.plot([TABLE_LEFT, TABLE_RIGHT], [rule_y, rule_y], color=theme.rule,
                    linewidth=0.9, zorder=3)

        for metric, (left, right, _) in columns.items():
            fill = None
            text_color = theme.ink
            if pd.isna(row[metric]):
                # Too small a sample to say anything. Say nothing.
                draw_table_cell(
                    ax, "—", left, right, y, ROW_HEIGHT, color=theme.faint,
                    fontsize=VALUE_FONT_SIZE, fontproperties=body_font,
                )
                continue
            if metric in SHADED_METRICS:
                fill = heat_fill(shaded_value(row, metric), *scales[metric])
                text_color = heat_text_color(fill)

            value = row[metric]
            if metric == "games":
                label = f"{int(value)}"
            elif metric == "ts_pct":
                label = f"{float(value) * 100:.1f}%"
            elif metric == "impact":
                label = f"{float(value):+.1f}"
            else:
                label = f"{float(value):.1f}"
            draw_table_cell(
                ax, label, left, right, y, ROW_HEIGHT, fill=fill, color=text_color,
                fontsize=VALUE_FONT_SIZE, fontproperties=body_font,
            )

        # Draw the player last so the overlapping portraits sit above the rules.
        _draw_player(ax, row, y)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output_path,
        dpi=export_dpi(final),
        transparent=True,
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)
    return output_path


def canva_copy(pages: list[pd.DataFrame]) -> str:
    ranges = [
        f"{page.iloc[-1]['season_label']} to {page.iloc[0]['season_label']}"
        for page in pages
    ]
    return "\n".join(
        [
            "BULLS ROOKIES SINCE 2000",
            "Every Bulls rookie to play at least 300 regular-season minutes",
            "Newest rookie class first",
            "Box-score stats are per game · TS% is a rate · ON/OFF is per 100 possessions",
            "Green is better and red is worse, against every NBA rookie since 2000 with 300+ minutes",
            "ON/OFF is how much better the Bulls were with him on the floor than off it",
            "It is blank below 750 minutes — too small a sample to mean anything",
            "TS% is judged against the league average of its own season",
            "The line under each name is his original overall NBA Draft position",
            "Sources: NBA.com (box score, draft) and databallr (on/off)",
            *(f"Slide {index}: {label}" for index, label in enumerate(ranges, 1)),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rookie-csv", type=Path, default=WORKING_CSV)
    parser.add_argument("--draft-csv", type=Path, default=DRAFT_CSV)
    parser.add_argument("--refresh-draft", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()

    rookies = pd.read_csv(args.rookie_csv)
    qualified_ids = rookies.loc[rookies["minutes"].ge(MIN_MINUTES), "player_id"]
    draft = load_or_fetch_draft_info(
        qualified_ids.astype(int).tolist(), args.draft_csv, args.refresh_draft
    )
    table = prepare_table(rookies, draft)
    table = attach_impact(table)
    ensure_headshots(table["player_id"])
    ensure_historical_headshot_fallbacks(table["player_id"])
    ensure_silhouette()
    DISPLAY_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(DISPLAY_CSV, index=False)
    pages = split_pages(table)
    stats_left = measure_stats_left(table)
    for page_number, page in enumerate(pages, 1):
        suffix = "final" if args.final else "draft"
        output = OUTPUT_DIR / f"rookie-chronological-slide-{page_number}-{suffix}.png"
        render_page(page, table, page_number, output, stats_left, final=args.final)
        print(f"Wrote {output}")
    print(f"Wrote {DISPLAY_CSV}")
    print("\nCanva copy:\n" + canva_copy(pages))


if __name__ == "__main__":
    main()
