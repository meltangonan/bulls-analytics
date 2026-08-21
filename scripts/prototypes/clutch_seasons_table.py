"""Rank the most productive Bulls clutch-scoring seasons since 2000-01.

NBA.com's clutch split — final five minutes, score within five — reaches back
past 2000, so the whole shot-clock-era Bulls can be ranked on one definition.
Totals are team-filtered, so a player traded mid-season is credited only with
the clutch points he scored in a Bulls uniform.

The same endpoint, called without the team filter, supplies both halves of the
colour scale: each season's league-wide clutch true shooting, and the
distribution of clutch player-seasons that the TS% and WIN% cells are
calibrated against.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import leaguedashplayerclutch

from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import (
    DEFAULT_THEME,
    draw_accent_card,
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

PROJECT = "most-clutch-seasons"
PROJECT_DATE = "2026-08-21"

BULLS_TEAM_ID = 1610612741
# 2000-01 is an editorial choice, not the source's limit. The endpoint reaches
# back to 1996-97 and no further — see the clutch-split floor in
# DEVELOPMENT.md — so a wider window was built, looked at, and rejected on
# 2026-08-21: it adds two Michael Jordan seasons to the leaderboard while
# still being unable to reach the first threepeat, which buys a worse headline
# rather than a better one. A round "since 2000" says what it covers.
FIRST_SEASON = 2000
LAST_SEASON = 2025
SEASON_TYPE = "Regular Season"
CLUTCH_TIME = "Last 5 Minutes"
POINT_DIFF = "5"
AHEAD_BEHIND = "Ahead or Behind"

TABLE_ROWS = 15

NBA_CLUTCH_URL = (
    "https://www.nba.com/stats/players/clutch-traditional"
    "?PerMode=Totals&SeasonType=Regular%20Season"
    "&ClutchTime=Last%205%20Minutes&PointDiff=5"
)

DATA_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT, when=PROJECT_DATE) / DATA
BULLS_CSV = DATA_DIR / "bulls-clutch-player-seasons.csv"
LEAGUE_CSV = DATA_DIR / "nba-clutch-player-seasons.csv"
DISPLAY_CSV = DATA_DIR / "most-clutch-seasons-table.csv"
OUTPUT_DIR = _REPO / "output" / f"{PROJECT_DATE}-{PROJECT}"

# The columns the post actually rests on. The endpoint returns 68; keeping the
# other 60 would make the tracked snapshot large without making it auditable.
KEEP = [
    "SEASON",
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ABBREVIATION",
    "GP",
    "W",
    "L",
    "MIN",
    "PTS",
    "FGM",
    "FGA",
    "FG3M",
    "FG3A",
    "FTM",
    "FTA",
    "PLUS_MINUS",
]


def season_labels() -> list[str]:
    """Every season label from 2000-01 through the last completed season."""
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(FIRST_SEASON, LAST_SEASON + 1)]


def fetch_clutch(season: str, team_id: int | None) -> pd.DataFrame:
    """One clutch-split call, optionally narrowed to a single team.

    Without ``team_id`` a traded player returns one combined row, which is why
    the Bulls figures cannot simply be filtered out of the league frame.
    """
    frame = leaguedashplayerclutch.LeagueDashPlayerClutch(
        season=season,
        season_type_all_star=SEASON_TYPE,
        per_mode_detailed="Totals",
        clutch_time=CLUTCH_TIME,
        point_diff=POINT_DIFF,
        ahead_behind=AHEAD_BEHIND,
        team_id_nullable=team_id,
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    frame.insert(0, "SEASON", season)
    missing = set(KEEP) - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com clutch columns changed, missing {sorted(missing)}")
    return frame[KEEP].copy()


def fetch_all(team_id: int | None, pause: float = 0.8) -> pd.DataFrame:
    """Walk every season, retrying the transient NBA.com timeouts."""
    frames = []
    for season in season_labels():
        for attempt in range(3):
            try:
                frames.append(fetch_clutch(season, team_id))
                break
            except Exception as error:  # noqa: BLE001 - retried, then re-raised
                if attempt == 2:
                    raise RuntimeError(f"NBA.com failed for {season}") from error
                time.sleep(3)
        time.sleep(pause)
    return pd.concat(frames, ignore_index=True)


def load_or_fetch(path: Path, team_id: int | None, refresh: bool) -> pd.DataFrame:
    """Use the tracked snapshot unless it is missing or explicitly refreshed."""
    if path.exists() and not refresh:
        return pd.read_csv(path)
    frame = fetch_all(team_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def add_rates(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach the three rates every downstream step needs."""
    out = frame.copy()
    out["tsa"] = out["FGA"] + 0.44 * out["FTA"]
    out["ts_pct"] = np.where(out["tsa"] > 0, out["PTS"] / (2 * out["tsa"]), np.nan)
    out["fg_pct"] = np.where(out["FGA"] > 0, out["FGM"] / out["FGA"], np.nan)
    # ⚠️ W and L are the FULL GAME's result, not the outcome of the clutch
    # stretch. Only the sample is clutch: GP counts the games in which this
    # player played clutch minutes. Verified 2026-08-21 on the 2010-11 Bulls,
    # where Taj Gibson carries a 17-6 clutch record on a clutch plus-minus of
    # -4 — impossible if the W meant he had won those five minutes.
    out["win_pct"] = np.where(out["GP"] > 0, out["W"] / out["GP"], np.nan)
    # Scoring rate per 36 clutch minutes. NOT a column: the table was kept to
    # the metrics it already carried rather than gaining another. It stays in
    # the working CSV because it is the honest counterweight to a totals
    # ranking — clutch minutes run from 105 to 203 across the fifteen rows —
    # and because reconciling it costs nothing.
    #
    # Points per true-shooting attempt was the other rate considered, and is
    # ruled out for good: it is exactly two times TS%, verified at zero
    # difference on all fifteen rows, so it can only print TS% twice.
    out["pts_per_36"] = np.where(out["MIN"] > 0, out["PTS"] / out["MIN"] * 36, np.nan)
    return out


def league_baselines(league: pd.DataFrame) -> pd.DataFrame:
    """League-wide clutch true shooting, one row per season.

    Pooled from the season's totals rather than averaged across players, so a
    deep bench of low-volume shooters cannot drag the baseline around.
    """
    grouped = league.groupby("SEASON", as_index=False)[["PTS", "FGA", "FTA", "FGM"]].sum()
    grouped["league_tsa"] = grouped["FGA"] + 0.44 * grouped["FTA"]
    if (grouped["league_tsa"] <= 0).any():
        raise ValueError("A season produced zero league clutch shooting attempts.")
    grouped["league_ts_pct"] = grouped["PTS"] / (2 * grouped["league_tsa"])
    grouped["league_fg_pct"] = grouped["FGM"] / grouped["FGA"]
    if not grouped["league_ts_pct"].between(0.3, 0.8).all():
        raise ValueError("A league clutch TS% baseline fell outside a plausible range.")
    return grouped[["SEASON", "league_ts_pct", "league_fg_pct"]]


# Colour scale, calibrated from NBA clutch player-seasons at 80+ clutch true
# shooting attempts (n=644, 2000-01 to 2025-26) — a population matched to the
# volume the table actually shows, whose thinnest row carries 103 attempts.
# Calibrating on every clutch player-season instead would have set the scale
# from bench players with a handful of shots, whose rates swing far wider than
# anything a 100-attempt season can.
#
# Each entry is (red_at, neutral_low, neutral_high, green_at); everything
# between the two neutral values stays the page colour.
CALIBRATION_MIN_TSA = 80
COLUMN_SCALES = {
    # Points of true shooting above or below the SAME SEASON's league clutch
    # average, at the 5th / 25th / 75th / 95th percentile of that population.
    # League clutch TS% climbed from .516 in 2000-01 to .569 in 2025-26, so a
    # raw scale would have graded the 2000s red and the 2020s green and called
    # it clutch shooting.
    "ts_pct": (-10.5, -3.5, 4.9, 11.1),
    # Diverging, and zero is where it belongs: the Bulls broke even over his
    # clutch minutes. The band is deliberately wider than the population's own
    # quartiles, because a single season's clutch plus-minus rests on roughly
    # 300 possessions and a twenty-point swing over that is not a finding.
    "PLUS_MINUS": (-80.0, -20.0, 20.0, 80.0),
}
ERA_RELATIVE_METRICS = ("ts_pct",)


def prepare_table(
    bulls: pd.DataFrame,
    baselines: pd.DataFrame,
    league: pd.DataFrame,
) -> pd.DataFrame:
    """Rank Bulls clutch player-seasons and attach every displayed figure."""
    if bulls["SEASON"].nunique() != LAST_SEASON - FIRST_SEASON + 1:
        raise ValueError(
            f"The Bulls snapshot does not cover every season from "
            f"{FIRST_SEASON}-{str(FIRST_SEASON + 1)[-2:]} onward."
        )
    if bulls.duplicated(["SEASON", "PLAYER_ID"]).any():
        raise ValueError("The Bulls snapshot contains duplicate player-seasons.")


    table = add_rates(bulls).merge(baselines, on="SEASON", how="left", validate="many_to_one")
    table = table.merge(
        league[["SEASON", "PLAYER_ID", "GP", "PTS"]].rename(
            columns={"GP": "season_gp", "PTS": "season_pts"}
        ),
        on=["SEASON", "PLAYER_ID"],
        how="left",
        validate="one_to_one",
    )
    if table["league_ts_pct"].isna().any():
        raise ValueError("A Bulls season has no league clutch baseline.")
    table["ts_pct_relative"] = (table["ts_pct"] - table["league_ts_pct"]) * 100

    # Points first. Ties break toward the season that needed fewer clutch
    # minutes to score them, then toward the more recent season, so the order
    # is fully determined rather than left to the source's own row order.
    ranked = table.sort_values(
        ["PTS", "MIN", "SEASON"],
        ascending=[False, True, False],
        kind="stable",
    ).reset_index(drop=True)

    cutoff = ranked.iloc[TABLE_ROWS - 1]["PTS"]
    if (ranked["PTS"] == cutoff).sum() > 1 and ranked.iloc[TABLE_ROWS]["PTS"] == cutoff:
        raise ValueError(
            f"The {TABLE_ROWS}-row cut falls inside a tie at {cutoff:.0f} clutch points."
        )
    return ranked.head(TABLE_ROWS).reset_index(drop=True)


def reconcile_team_filter(bulls: pd.DataFrame, league: pd.DataFrame) -> pd.DataFrame:
    """Prove the team filter really returned Bulls-only stints.

    ⚠️ ``TEAM_ABBREVIATION`` in a team-filtered response names the player's
    LAST team of that season, not the team the filter selected. Ron Mercer's
    2001-02 Bulls stint comes back stamped ``IND``, because Chicago traded him
    to Indiana in February. Filtering the response down to ``CHI`` therefore
    looks like a tidy safety check and silently deletes 45 real Bulls stints,
    every one of them belonging to a traded player.

    The figures themselves are correct, and this is what shows it: a stint has
    to be a subset of the player's whole season, and a player stamped with
    another team has to have a strictly smaller Bulls stint than his season
    total. Measured on Mercer: 19 Bulls clutch games plus 4 Indiana clutch
    games equals the 23 his unfiltered row reports.
    """
    combined = league[["SEASON", "PLAYER_ID", "GP", "MIN", "PTS"]].rename(
        columns={"GP": "season_gp", "MIN": "season_min", "PTS": "season_pts"}
    )
    merged = bulls.merge(combined, on=["SEASON", "PLAYER_ID"], how="left", validate="one_to_one")
    if merged["season_gp"].isna().any():
        missing = merged.loc[merged["season_gp"].isna(), "PLAYER_NAME"].tolist()
        raise ValueError(f"A Bulls clutch stint has no league row: {sorted(missing)}")

    over = merged.loc[
        merged["GP"].gt(merged["season_gp"] + 1e-9)
        | merged["MIN"].gt(merged["season_min"] + 1e-6)
        | merged["PTS"].gt(merged["season_pts"] + 1e-9)
    ]
    if len(over):
        raise ValueError(
            "A Bulls clutch stint exceeds the player's own season total: "
            f"{sorted(over['PLAYER_NAME'].unique())}"
        )
    return merged


def assert_whole_season_bulls(table: pd.DataFrame) -> None:
    """Every displayed row must be a season spent entirely in Chicago.

    The stint-versus-season distinction above is what makes this checkable, and
    it currently costs the table nothing: all fifteen rows are players who were
    Bulls from opening night to game 82, so each printed total is both the
    Bulls figure and the player's whole clutch season. If a future refresh
    promotes a half-season into the table, this fails rather than quietly
    printing a partial season beside fourteen complete ones.
    """
    partial = table.loc[
        table["GP"].ne(table["season_gp"]) | table["PTS"].ne(table["season_pts"])
    ]
    if len(partial):
        rows = [
            f"{row['PLAYER_NAME']} {row['SEASON']}" for _, row in partial.iterrows()
        ]
        raise ValueError(
            "A displayed season is only part of the player's clutch year: "
            f"{rows}. Say so on the page before shipping it."
        )


def calibration_population(league: pd.DataFrame, baselines: pd.DataFrame) -> pd.DataFrame:
    """The volume-matched clutch seasons the colour scale is anchored on."""
    rated = add_rates(league).merge(baselines, on="SEASON", how="left", validate="many_to_one")
    rated["ts_pct_relative"] = (rated["ts_pct"] - rated["league_ts_pct"]) * 100
    return rated.loc[rated["tsa"].ge(CALIBRATION_MIN_TSA)].copy()


def validate(table: pd.DataFrame, population: pd.DataFrame) -> dict:
    """Re-derive every printed figure from the raw totals beside it."""
    if len(table) != TABLE_ROWS:
        raise ValueError(f"Expected {TABLE_ROWS} rows, built {len(table)}.")
    if not table["PTS"].is_monotonic_decreasing:
        raise ValueError("The table is not ordered by clutch points.")
    if (table["W"] + table["L"] != table["GP"]).any():
        raise ValueError("Clutch wins and losses do not reconcile to games played.")
    displayed = [
        "GP", "MIN", "PTS", "FGM", "FGA", "FTM", "FTA",
        "pts_per_36", "ts_pct", "ts_pct_relative", "PLUS_MINUS",
    ]
    if table[displayed].isna().any().any():
        raise ValueError("A displayed cell is missing a value.")
    if not np.allclose(table["ts_pct"], table["PTS"] / (2 * table["tsa"]), atol=1e-12):
        raise ValueError("TS% does not reconcile to PTS / (2 x TSA).")
    if not np.allclose(table["win_pct"], table["W"] / table["GP"], atol=1e-12):
        raise ValueError("WIN% does not reconcile to W / GP.")
    if not np.allclose(table["fg_pct"], table["FGM"] / table["FGA"], atol=1e-12):
        raise ValueError("FG% does not reconcile to FGM / FGA.")
    if not np.allclose(
        table["pts_per_36"], table["PTS"] / table["MIN"] * 36, atol=1e-9
    ):
        raise ValueError("P/36 does not reconcile to PTS / MIN x 36.")
    if (table["FTM"] > table["FTA"]).any():
        raise ValueError("A season reports more free throws made than attempted.")
    if table["tsa"].min() < CALIBRATION_MIN_TSA:
        raise ValueError(
            "A displayed season carries less volume than the colour scale's own "
            "calibration floor, so its cell colour is extrapolated."
        )
    if len(population) < 300:
        raise ValueError("The calibration population is too small to set percentiles.")

    return {
        "rows": int(len(table)),
        # The window SEARCHED, which is what the page claims. Reporting the
        # earliest season that happened to make the top fifteen instead would
        # have printed "2002-03 to 2025-26" beside a page saying "since 2000".
        "seasons_searched": f"{FIRST_SEASON}-{str(FIRST_SEASON + 1)[-2:]} to "
        f"{LAST_SEASON}-{str(LAST_SEASON + 1)[-2:]}",
        "earliest_season_displayed": str(min(table["SEASON"])),
        "leader": f"{table.iloc[0]['PLAYER_NAME']} {table.iloc[0]['SEASON']} "
        f"({int(table.iloc[0]['PTS'])} clutch points)",
        "cutoff_points": int(table.iloc[-1]["PTS"]),
        "players_represented": int(table["PLAYER_ID"].nunique()),
        "repeat_players": {
            str(name): int(count)
            for name, count in table["PLAYER_NAME"].value_counts().items()
            if count > 1
        },
        "calibration_population": int(len(population)),
        "calibration_min_tsa": CALIBRATION_MIN_TSA,
        "min_displayed_tsa": round(float(table["tsa"].min()), 1),
        "league_ts_first": round(float(table["league_ts_pct"].max()), 4),
    }


# --- Layout ------------------------------------------------------------------
#
# Fifteen rows on one 1080x1350 feed page is the constraint everything else
# bends to. The rookie table's 66px rows carried two lines of type under each
# portrait; this one carries a name and nothing else, so the row loses the
# caption's height without losing any of its air.
CHART_WIDTH = 1080
TABLE_LEFT = 18
TABLE_RIGHT = 1036

HEADER_FROM_TOP = 62
HEADER_RULE_FROM_TOP = 84
HEADER_RULE_CLEARANCE = 1.5
ROW_HEIGHT = 63
FIRST_ROW_FROM_TOP = HEADER_RULE_FROM_TOP + ROW_HEIGHT / 2 + HEADER_RULE_CLEARANCE
BOTTOM_PAD = 26

HEADSHOT_X = 64
HEADSHOT_HALF_SIZE = 40
HEADSHOT_RISE = 6
# Fraction of the source portrait's height kept, as a square centred on the
# face. The rest of the table family keeps 0.74, which frames head and
# shoulders; this one crops closer, because that is what makes a face read
# BIGGER without giving it a bigger box. Enlarging the box instead pushed each
# portrait out of its own row and left the name beside a chin.
HEADSHOT_CROP_FRACTION = 0.72
NAME_X = 116
NAME_FONT_SIZE = 15.5
# Larger than the rookie table's 9.6pt marker. There the season was context
# beside a unique name; here four Ben Gordon seasons and three DeMar DeRozan
# seasons share the column, so the year is half the row's identity.
SEASON_FONT_SIZE = 11.5
VALUE_FONT_SIZE = 14.0
HEADER_FONT_SIZE = 13.0
NAME_GAP = 24

# PTS leads, immediately beside the name, because it is what the table is
# ranked by and it wears the accent card. The rest run from opportunity (G,
# MIN) through the shooting line to the result.
# The third value is a width weight. Equal columns gave PTS a 130px box for a
# three-digit number, and the accent card inherited that width as a red slab
# wider than anything it contained. Widths follow the widest string a column
# actually holds — "55-113" needs the room, "40" does not.
# WIN% was here and was cut. It was the only column whose window disagreed
# with the rest of the table: the sample was clutch, but the win or loss was
# the whole game's, so it credited a player for a result decided long after
# the last five minutes. Clutch plus-minus answers the same question — did it
# work — inside the same window everything else is measured in.
STAT_COLUMNS = (
    ("PTS", "PTS", 0.84),
    ("GP", "G", 0.58),
    ("MIN", "MIN", 0.76),
    ("fg_line", "FG", 1.06),
    ("ft_line", "FT", 0.96),
    ("ts_pct", "TS%", 1.00),
    ("PLUS_MINUS", "+/−", 0.94),
)
SHADED_METRICS = ("ts_pct", "PLUS_MINUS")
HERO_METRIC = "PTS"
# The rookie leaderboard's values, and its whole treatment: the card reaches
# past the header rule and is drawn ABOVE it, so it reads as an object resting
# on the table. Two things have to be true together for that to work, and
# getting only one gives a defect rather than depth — the card must win the
# stacking order, AND the rule must break around it, or the line shows through
# the rounded corners the overlap exists to display.
CARD_OUTSET_Y = 7.0
CARD_OVERLAP_Y = 3.0
# Matches ACCENT_CARD_OUTSET_X, so the rule stops exactly at the card's edge.
CARD_OUTSET_X = 8.0
# Clear air between the ranking card and the first ordinary column, so the
# pill has a margin rather than a column pressed against it.
HERO_GAP = 22.0


def table_height(row_count: int) -> float:
    """Size the canvas to the rows it holds, with no trailing transparency."""
    return FIRST_ROW_FROM_TOP + (row_count - 1) * ROW_HEIGHT + ROW_HEIGHT / 2 + BOTTOM_PAD


def column_bounds(stats_left: float) -> dict[str, tuple[float, float, str]]:
    """Divide the space right of the name block by each column's width weight.

    ``HERO_GAP`` is taken out before the weights are applied, so widening the
    pill's margin narrows the ordinary columns rather than pushing the last one
    off the canvas.
    """
    available = TABLE_RIGHT - stats_left - HERO_GAP
    total_weight = sum(weight for _, _, weight in STAT_COLUMNS)
    bounds = {}
    edge = stats_left
    for metric, label, weight in STAT_COLUMNS:
        width = available * weight / total_weight
        bounds[metric] = (edge, edge + width, label)
        edge += width
        if metric == HERO_METRIC:
            edge += HERO_GAP
    return bounds


def display_name(value: object) -> str:
    """Drop generational suffixes, as the recent table family does."""
    return str(value).removesuffix(" III").removesuffix(" Jr.")


def season_marker(season: object) -> str:
    """Compact a season label for the superscript beside a name."""
    return str(season)[2:].replace("-", "\N{EN DASH}", 1)


def cell_label(row: pd.Series, metric: str) -> str:
    """Format one cell, keeping the shooting sample visible as makes-attempts."""
    if metric == "fg_line":
        return f"{int(row['FGM'])}\N{EN DASH}{int(row['FGA'])}"
    if metric == "ft_line":
        return f"{int(row['FTM'])}\N{EN DASH}{int(row['FTA'])}"
    if metric == "ts_pct":
        return f"{float(row['ts_pct']) * 100:.1f}%"
    if metric == "pts_per_36":
        return f"{float(row['pts_per_36']):.1f}"
    if metric == "PLUS_MINUS":
        # A true minus, and the sign decided after rounding so a -0.4 never
        # prints as a signed zero that its own digit contradicts.
        value = round(float(row["PLUS_MINUS"]))
        sign = "+" if value > 0 else ("−" if value < 0 else "")
        return f"{sign}{abs(value):.0f}"
    if metric == "MIN":
        return f"{float(row['MIN']):.0f}"
    return f"{int(row[metric])}"


def shaded_value(row: pd.Series, metric: str) -> float:
    """Give a column the number its colour scale is actually calibrated on."""
    if metric in ERA_RELATIVE_METRICS:
        return float(row[f"{metric}_relative"])
    return float(row[metric])


def _name_block_width(ax, name: str, season: str) -> float:
    """Measure one name plus its superscript season marker."""
    season_font = helvetica("regular")
    season_font.set_style("italic")
    probe = ax.text(
        0, 0, season_marker(season), fontsize=SEASON_FONT_SIZE,
        fontproperties=season_font, alpha=0,
    )
    season_width = rendered_width(ax, probe)
    probe.remove()
    name_probe = ax.text(
        NAME_X, 0, name, ha="left", va="center", fontsize=NAME_FONT_SIZE,
        fontproperties=helvetica("bold"), alpha=0,
    )
    name_width = rendered_width(ax, name_probe)
    name_probe.remove()
    return name_width + 5 + season_width


def measure_stats_left(table: pd.DataFrame) -> float:
    """Start the statistics just past the widest name in the table."""
    height = table_height(len(table))
    fig = plt.figure(figsize=(CHART_WIDTH / 100, height / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")
    widest = max(
        _name_block_width(ax, display_name(row["PLAYER_NAME"]), str(row["SEASON"]))
        for _, row in table.iterrows()
    )
    plt.close(fig)
    return NAME_X + widest + NAME_GAP


def _face_headshot(ax, player_id: int, row_y: float) -> None:
    """Draw the face-focused square crop, clipped at this row's separator.

    A portrait is deliberately much taller than its row and rises into the row
    above it. The top row has no row above it, only the header rule, and the
    leader's head is meant to break that line — it is drawn above the rule and
    stops at nothing but the canvas. The clip only ever applies downward: a
    face may reach up, never spill onto the row beneath it.
    """
    y = row_y + HEADSHOT_RISE
    clip_left = HEADSHOT_X - HEADSHOT_HALF_SIZE
    clip_bottom = row_y - ROW_HEIGHT / 2
    clip_height = y + HEADSHOT_HALF_SIZE - clip_bottom
    clip = Rectangle(
        (clip_left, clip_bottom), 2 * HEADSHOT_HALF_SIZE, clip_height,
        transform=ax.transData,
    )
    try:
        image = plt.imread(portrait_path(player_id))
    except (FileNotFoundError, OSError, ValueError):
        ax.add_patch(
            Rectangle(
                (clip_left, clip_bottom), 2 * HEADSHOT_HALF_SIZE, clip_height,
                facecolor="#DDD8D1", edgecolor="none", zorder=4,
            )
        )
        return
    height, width = image.shape[:2]
    side = min(int(height * HEADSHOT_CROP_FRACTION), width)
    left = max(0, (width - side) // 2)
    artist = ax.imshow(
        image[:side, left:left + side],
        extent=[
            HEADSHOT_X - HEADSHOT_HALF_SIZE, HEADSHOT_X + HEADSHOT_HALF_SIZE,
            y - HEADSHOT_HALF_SIZE, y + HEADSHOT_HALF_SIZE,
        ],
        interpolation="bilinear",
        zorder=4,
    )
    artist.set_clip_path(clip)


def _draw_player(ax, row: pd.Series, y: float) -> None:
    """Draw the portrait, the name, and the season it belongs to."""
    _face_headshot(ax, int(row["PLAYER_ID"]), y)
    name = display_name(row["PLAYER_NAME"])
    name_artist = ax.text(
        NAME_X, y, name, ha="left", va="center", fontsize=NAME_FONT_SIZE,
        color=DEFAULT_THEME.ink, fontproperties=helvetica("bold"), zorder=5,
    )
    season_font = helvetica("regular")
    season_font.set_style("italic")
    ax.text(
        NAME_X + rendered_width(ax, name_artist) + 5,
        y + 7,
        season_marker(row["SEASON"]),
        ha="left", va="center", fontsize=SEASON_FONT_SIZE,
        color=DEFAULT_THEME.muted, fontproperties=season_font, zorder=5,
    )


def render_table(table: pd.DataFrame, output_path: Path, final: bool = False) -> Path:
    """Render the transparent, Canva-ready leaderboard asset."""
    theme = DEFAULT_THEME
    body_font = helvetica("regular")
    header_font = helvetica("bold")
    stats_left = measure_stats_left(table)
    columns = column_bounds(stats_left)

    height = table_height(len(table))
    header_y = height - HEADER_FROM_TOP
    header_rule_y = height - HEADER_RULE_FROM_TOP
    first_row_y = height - FIRST_ROW_FROM_TOP

    fig = plt.figure(figsize=(CHART_WIDTH / 100, height / 100), facecolor="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CHART_WIDTH)
    ax.set_ylim(0, height)
    ax.axis("off")

    ax.text(NAME_X, header_y, "PLAYER", ha="left", va="center",
            fontsize=HEADER_FONT_SIZE + 1, color=theme.ink, fontproperties=header_font)
    for metric, (left, right, label) in columns.items():
        ax.text((left + right) / 2, header_y, label, ha="center", va="center",
                fontsize=HEADER_FONT_SIZE,
                color=theme.accent if metric == HERO_METRIC else theme.ink,
                fontproperties=header_font)
    hero_left, hero_right, _ = columns[HERO_METRIC]
    # The header rule breaks around the card rather than running behind it.
    for start, end in (
        (TABLE_LEFT, hero_left - CARD_OUTSET_X),
        (hero_right + CARD_OUTSET_X, TABLE_RIGHT),
    ):
        ax.plot([start, end], [header_rule_y, header_rule_y],
                color=theme.ink, linewidth=1.5, zorder=3, solid_capstyle="butt")

    # Drawn above the rule and before the rows, so the values sit on the card
    # and the card sits on the table.
    draw_accent_card(
        ax, hero_left, hero_right, first_row_y, len(table), ROW_HEIGHT,
        zorder=4, outset_y=CARD_OUTSET_Y, overlap_y=CARD_OVERLAP_Y,
    )

    for row_index, row in table.iterrows():
        y = first_row_y - row_index * ROW_HEIGHT
        if row_index < len(table) - 1:
            # One unbroken rule, drawn UNDER the card rather than stopped at
            # its edges. The card still reads as a single object, because it
            # hides the segment it covers — but the two stubs no longer die a
            # few pixels short of a rounded corner, which is what made the
            # gap either side of the pill look like a rendering fault.
            rule_y = y - ROW_HEIGHT / 2
            ax.plot([TABLE_LEFT, TABLE_RIGHT], [rule_y, rule_y],
                    color=theme.rule, linewidth=0.9, zorder=1.5)

        for metric, (left, right, _) in columns.items():
            color = theme.ink
            if metric == HERO_METRIC:
                color = "#FFFFFF"
            elif metric in SHADED_METRICS:
                fill = heat_fill(shaded_value(row, metric), *COLUMN_SCALES[metric])
                ax.add_patch(
                    Rectangle((left, y - ROW_HEIGHT / 2), right - left, ROW_HEIGHT,
                              facecolor=fill, edgecolor="none", zorder=1)
                )
                color = heat_text_color(fill)
            ax.text((left + right) / 2, y, cell_label(row, metric),
                    ha="center", va="center", fontsize=VALUE_FONT_SIZE,
                    color=color,
                    fontproperties=header_font if metric == HERO_METRIC else body_font,
                    zorder=5)

        _draw_player(ax, row, y)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=export_dpi(final), transparent=True,
                bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return output_path


def canva_copy_block(table: pd.DataFrame, report: dict) -> str:
    """Exact framing copy from the same validated run."""
    leader = table.iloc[0]
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: THE MOST CLUTCH BULLS SEASONS",
            "",
            "SUBTITLE: Most clutch points in a season since 2000",
            "",
            (
                "QUALIFICATION: Bulls player-seasons, 2000-01 to 2025-26 regular "
                "seasons. Clutch totals count only points scored in a Bulls uniform."
            ),
            "",
            (
                "DEFINITIONS: Clutch = final 5:00 with the score within 5. "
                "G and MIN are clutch games and clutch minutes. FG = clutch field "
                "goals made-attempted. FT = clutch free throws made-attempted. "
                "TS% = true "
                "shooting, which counts free throws and the extra point on a "
                "three, and is built only from clutch shooting. +/− = the "
                "Bulls' net points over the clutch minutes he was on the floor "
                "for. It is a five-man team figure: everyone on the court "
                "shares the same swing."
            ),
            "",
            (
                "COLOUR: TS% is shaded against the league clutch average of its "
                "own season, because that average rose from 51.6% in 2000-01 to "
                "56.9% in 2025-26. +/− is shaded around zero. Green is better."
            ),
            "",
            (
                "SAMPLE NOTE: every figure here rests on one season of crunch "
                "time — roughly 100 to 200 minutes. FG and FT are printed as "
                "made-attempted so the size of that sample stays visible, and "
                "+/\N{MINUS SIGN} is a five-man team measure, not a solo one."
            ),
            "",
            (
                f"LEADER: {display_name(leader['PLAYER_NAME'])} scored "
                f"{int(leader['PTS'])} clutch points in {leader['SEASON']}, the "
                "most by any Bull in a season since 2000."
            ),
            "",
            f"SOURCE: Data via nba.com",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="Refetch both NBA.com snapshots instead of using data/.")
    parser.add_argument("--final", action="store_true",
                        help="Export at final DPI; first-review drafts should omit this.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bulls = load_or_fetch(BULLS_CSV, BULLS_TEAM_ID, args.refresh)
    league = load_or_fetch(LEAGUE_CSV, None, args.refresh)

    baselines = league_baselines(league)
    reconcile_team_filter(bulls, league)
    table = prepare_table(bulls, baselines, league)
    assert_whole_season_bulls(table)
    population = calibration_population(league, baselines)
    report = validate(table, population)

    DISPLAY_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(DISPLAY_CSV, index=False)

    ensure_headshots(table["PLAYER_ID"])
    ensure_silhouette()
    suffix = "final" if args.final else "draft"
    output = render_table(
        table, OUTPUT_DIR / f"{PROJECT_DATE}-most-clutch-seasons-{suffix}.png",
        final=args.final,
    )

    print(json.dumps(report, indent=2))
    print(f"\nWrote {DISPLAY_CSV}")
    print(f"Wrote {output}\n")
    print(canva_copy_block(table, report))


if __name__ == "__main__":
    main()
