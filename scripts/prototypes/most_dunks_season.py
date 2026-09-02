"""Rank the most dunk-heavy Bulls player-seasons since 2000-01.

Made dunks only, Chicago stints only, regular season. A dunk is any
ShotChartDetail ACTION_TYPE that contains the word "dunk" (case-insensitive) —
the same pattern as summer_league_sticky_stats.is_dunk. Restricted Area is
NOT required: alley-oops and putbacks labelled dunks from just outside the
restricted area still count.

Totals are team-filtered at the shot grain (ShotChartDetail team_id = CHI,
player_id = 0), so a player traded mid-season is credited only with dunks
he threw down in a Bulls uniform. There is no games-played floor on v1:
this is a totals board, and the ranking column is the count.

Do not use bulls.data.fetch.get_team_shots for this. That wrapper drops
ACTION_TYPE, which is the field the definition rests on.
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
import pandas as pd
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import shotchartdetail

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import (
    DEFAULT_THEME,
    draw_accent_card,
    ensure_headshots,
    ensure_silhouette,
    export_dpi,
    helvetica,
    portrait_path,
    rendered_width,
)
from bulls.visuals import DATA, visual_dir

PROJECT = "most-dunks-season-since-2000"
PROJECT_DATE = "2026-09-02"

# 2000-01 is the editorial window, matching the clutch-seasons board. The
# shot-location archive reaches back to 1996-97 (DEVELOPMENT.md); this post
# does not take that extra four years.
FIRST_SEASON = 2000
LAST_SEASON = 2025
SEASON_TYPE = "Regular Season"
PAUSE = 0.8

TABLE_ROWS = 15

DATA_DIR = visual_dir(_REPO / "docs" / "visuals", PROJECT, when=PROJECT_DATE) / DATA
SHOTS_DIR = DATA_DIR / "seasons"
AUDIT_CSV = DATA_DIR / "season-audit.csv"
WORKING_CSV = DATA_DIR / "bulls-dunk-player-seasons.csv"
DISPLAY_CSV = DATA_DIR / "most-dunks-season-table.csv"
OUTPUT_DIR = _REPO / "output" / f"{PROJECT_DATE}-{PROJECT}"

# ShotChartDetail returns ~20 columns. These are the ones the definition,
# the ranking, and the audit actually use.
KEEP = [
    "GAME_ID",
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ID",
    "ACTION_TYPE",
    "SHOT_MADE_FLAG",
    "SHOT_ATTEMPTED_FLAG",
    "SHOT_ZONE_BASIC",
]


def season_labels() -> list[str]:
    """Every season label from 2000-01 through the last completed season."""
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(FIRST_SEASON, LAST_SEASON + 1)]


def season_shot_path(season: str) -> Path:
    return SHOTS_DIR / f"dunks-{season}.csv"


def is_dunk(action_type: object) -> bool:
    """NBA shot-detail labels every dunk variant with the word ``Dunk``.

    Copied from ``summer_league_sticky_stats.is_dunk`` rather than imported:
    promote the helper after a second regular-season consumer, not on first use.
    """
    return "dunk" in str(action_type or "").lower()


def shot_made(frame: pd.DataFrame) -> pd.Series:
    """SHOT_MADE_FLAG arrives as 1/0, 1.0/0.0, or occasionally a bool."""
    return pd.to_numeric(frame["SHOT_MADE_FLAG"], errors="coerce").fillna(0).astype(int).eq(1)


def dunk_rows(shots: pd.DataFrame) -> pd.DataFrame:
    """Keep dunk attempts — makes and misses — and nothing else."""
    return shots.loc[shots["ACTION_TYPE"].map(is_dunk)].copy()


def summarize_season(shots: pd.DataFrame) -> dict:
    """Compact per-season totals recorded from the full FGA extract."""
    dunk_mask = shots["ACTION_TYPE"].map(is_dunk)
    made = shot_made(shots)
    return {
        "SEASON": str(shots["SEASON"].iloc[0]),
        "total_fga": int(len(shots)),
        "dunk_attempts": int(dunk_mask.sum()),
        "dunk_makes": int((dunk_mask & made).sum()),
        "players": int(shots["PLAYER_ID"].nunique()),
    }


def fetch_season_shots(season: str) -> pd.DataFrame:
    """One ShotChartDetail call: every Bulls regular-season FGA, ACTION_TYPE kept.

    ``player_id=0`` with ``team_id=CHI`` is the team-wide extract. Each row is
    one field-goal attempt taken in a Bulls uniform that season, so a traded
    player's non-Chicago dunks never appear.
    """
    frame = shotchartdetail.ShotChartDetail(
        team_id=BULLS_TEAM_ID,
        player_id=0,
        season_nullable=season,
        season_type_all_star=SEASON_TYPE,
        context_measure_simple="FGA",
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    if frame.empty:
        # Same trap as the clutch split: unavailable seasons return empty,
        # not an error. Fail loudly rather than shipping a shorter window.
        raise RuntimeError(
            f"NBA.com returned no shots for {season}. ShotChartDetail returns "
            "an empty frame rather than an error for unavailable seasons."
        )
    missing = set(KEEP) - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com shot columns changed, missing {sorted(missing)}")
    out = frame[KEEP].copy()
    out.insert(0, "SEASON", season)
    out["GAME_ID"] = out["GAME_ID"].astype(str)
    team_ids = pd.to_numeric(out["TEAM_ID"], errors="coerce")
    if team_ids.ne(BULLS_TEAM_ID).any():
        raise ValueError(f"ShotChartDetail for {season} included a non-Bulls TEAM_ID.")
    return out


def fetch_season_shots_retry(season: str) -> pd.DataFrame:
    """Retry the transient NBA.com timeouts, then give up."""
    for attempt in range(3):
        try:
            return fetch_season_shots(season)
        except Exception as error:  # noqa: BLE001 - retried, then re-raised
            if attempt == 2:
                raise RuntimeError(f"NBA.com failed for {season}") from error
            time.sleep(3)
    raise RuntimeError(f"NBA.com failed for {season}")


def load_or_fetch(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use tracked per-season dunk extracts unless missing or refreshed.

    The live call still requests full FGA (needed to classify dunks). What is
    written under ``data/seasons/`` is dunk attempts only, plus a season-audit
    row that records the FGA count the classification ran over.
    """
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    existing_audit = (
        pd.read_csv(AUDIT_CSV) if AUDIT_CSV.exists() and not refresh else pd.DataFrame()
    )
    audit_rows: list[dict] = []
    dunk_frames: list[pd.DataFrame] = []

    for season in season_labels():
        path = season_shot_path(season)
        have_audit = (not existing_audit.empty) and season in set(existing_audit["SEASON"].astype(str))
        if path.exists() and have_audit and not refresh:
            cached = pd.read_csv(path, dtype={"GAME_ID": str})
            if "SEASON" not in cached.columns:
                cached.insert(0, "SEASON", season)
            dunk_frames.append(cached)
            print(f"{season}: cached {len(cached)} dunk attempts", flush=True)
            continue

        print(f"{season}: fetching ShotChartDetail FGA…", flush=True)
        shots = fetch_season_shots_retry(season)
        dunks = dunk_rows(shots)
        dunks.to_csv(path, index=False)
        dunk_frames.append(dunks)
        audit_rows.append(summarize_season(shots))
        print(
            f"{season}: {len(shots)} FGA, {int(audit_rows[-1]['dunk_makes'])} made dunks",
            flush=True,
        )
        time.sleep(PAUSE)

    if audit_rows:
        new_audit = pd.DataFrame(audit_rows)
        if existing_audit.empty:
            audit = new_audit
        else:
            keep = existing_audit.loc[
                ~existing_audit["SEASON"].astype(str).isin(new_audit["SEASON"])
            ]
            audit = pd.concat([keep, new_audit], ignore_index=True)
        audit = audit.sort_values("SEASON").reset_index(drop=True)
        audit.to_csv(AUDIT_CSV, index=False)
    else:
        audit = existing_audit

    dunks = pd.concat(dunk_frames, ignore_index=True) if dunk_frames else pd.DataFrame()
    return dunks, audit


def player_seasons(dunks: pd.DataFrame) -> pd.DataFrame:
    """Roll dunk attempts up to one row per Bulls player-season."""
    if dunks.empty:
        raise ValueError("No dunk attempts in the snapshot.")
    rows = dunks.copy()
    rows["made"] = shot_made(rows).astype(int)
    in_ra = rows["SHOT_ZONE_BASIC"].eq("Restricted Area")
    grouped = rows.groupby(["SEASON", "PLAYER_ID"], as_index=False).agg(
        PLAYER_NAME=("PLAYER_NAME", "last"),
        dunks_made=("made", "sum"),
        dunks_attempted=("made", "size"),
        games=("GAME_ID", "nunique"),
    )
    ra_makes = (
        rows.loc[in_ra & rows["made"].eq(1)]
        .groupby(["SEASON", "PLAYER_ID"], as_index=False)
        .size()
        .rename(columns={"size": "restricted_area_makes"})
    )
    grouped = grouped.merge(ra_makes, on=["SEASON", "PLAYER_ID"], how="left")
    grouped["restricted_area_makes"] = grouped["restricted_area_makes"].fillna(0).astype(int)
    grouped["dunks_made"] = grouped["dunks_made"].astype(int)
    grouped["dunks_attempted"] = grouped["dunks_attempted"].astype(int)
    grouped["games"] = grouped["games"].astype(int)
    grouped["fg_pct"] = grouped["dunks_made"] / grouped["dunks_attempted"]
    grouped["non_ra_makes"] = grouped["dunks_made"] - grouped["restricted_area_makes"]
    return grouped


def assert_season_coverage(audit: pd.DataFrame) -> None:
    """Every season in the headline window must have a positive FGA count."""
    expected = set(season_labels())
    got = set(audit["SEASON"].astype(str))
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise ValueError(
            f"Season audit does not cover 2000-01 through 2025-26. "
            f"missing={missing} extra={extra}"
        )
    if (pd.to_numeric(audit["total_fga"], errors="coerce").fillna(0) <= 0).any():
        empty = audit.loc[pd.to_numeric(audit["total_fga"], errors="coerce").fillna(0) <= 0, "SEASON"]
        raise ValueError(f"A season produced zero field-goal attempts: {list(empty)}")


def prepare_table(seasons: pd.DataFrame) -> pd.DataFrame:
    """Rank Bulls dunk player-seasons. No games-played floor on v1."""
    if seasons.duplicated(["SEASON", "PLAYER_ID"]).any():
        raise ValueError("The dunk snapshot contains duplicate player-seasons.")

    ranked = seasons.sort_values(
        ["dunks_made", "dunks_attempted", "SEASON"],
        ascending=[False, True, False],
        kind="stable",
    ).reset_index(drop=True)

    if len(ranked) < TABLE_ROWS:
        raise ValueError(f"Only {len(ranked)} player-seasons with a dunk attempt.")

    cutoff = ranked.iloc[TABLE_ROWS - 1]["dunks_made"]
    if (
        len(ranked) > TABLE_ROWS
        and ranked.iloc[TABLE_ROWS]["dunks_made"] == cutoff
    ):
        raise ValueError(
            f"The {TABLE_ROWS}-row cut falls inside a tie at {cutoff:.0f} made dunks."
        )
    return ranked.head(TABLE_ROWS).reset_index(drop=True)


def validate(table: pd.DataFrame, audit: pd.DataFrame) -> dict:
    """Re-derive every printed figure from the raw counts beside it."""
    if len(table) != TABLE_ROWS:
        raise ValueError(f"Expected {TABLE_ROWS} rows, built {len(table)}.")
    if not table["dunks_made"].is_monotonic_decreasing:
        raise ValueError("The table is not ordered by made dunks.")
    if (table["dunks_made"] > table["dunks_attempted"]).any():
        raise ValueError("A season reports more made dunks than attempts.")
    if (table["dunks_attempted"] <= 0).any():
        raise ValueError("A displayed season has zero dunk attempts.")
    if (table["games"] <= 0).any():
        raise ValueError("A displayed season has zero dunk-attempt games.")
    displayed = ["dunks_made", "dunks_attempted", "fg_pct", "games"]
    if table[displayed].isna().any().any():
        raise ValueError("A displayed cell is missing a value.")
    if not (table["dunks_made"] / table["dunks_attempted"] - table["fg_pct"]).abs().lt(1e-12).all():
        raise ValueError("FG% does not reconcile to makes / attempts.")
    if (table["restricted_area_makes"] > table["dunks_made"]).any():
        raise ValueError("Restricted-area makes exceed total made dunks.")

    return {
        "rows": int(len(table)),
        "seasons_searched": f"{FIRST_SEASON}-{str(FIRST_SEASON + 1)[-2:]} to "
        f"{LAST_SEASON}-{str(LAST_SEASON + 1)[-2:]}",
        "earliest_season_displayed": str(min(table["SEASON"])),
        "leader": (
            f"{table.iloc[0]['PLAYER_NAME']} {table.iloc[0]['SEASON']} "
            f"({int(table.iloc[0]['dunks_made'])} made dunks)"
        ),
        "cutoff_dunks": int(table.iloc[-1]["dunks_made"]),
        "players_represented": int(table["PLAYER_ID"].nunique()),
        "repeat_players": {
            str(name): int(count)
            for name, count in table["PLAYER_NAME"].value_counts().items()
            if count > 1
        },
        "min_games": int(table["games"].min()),
        "non_ra_makes_in_table": int(table["non_ra_makes"].sum()),
        "window_fga": int(pd.to_numeric(audit["total_fga"]).sum()),
        "window_dunk_makes": int(pd.to_numeric(audit["dunk_makes"]).sum()),
    }


# --- Layout ------------------------------------------------------------------
#
# Fifteen rows on one 1080-wide feed asset, matching clutch_seasons_table.
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
HEADSHOT_CROP_FRACTION = 0.72
NAME_X = 116
NAME_FONT_SIZE = 15.5
SEASON_FONT_SIZE = 11.5
VALUE_FONT_SIZE = 14.0
HEADER_FONT_SIZE = 13.0
NAME_GAP = 24

# DUNKS leads, immediately beside the name, because it is what the table is
# ranked by and it wears the accent card. ATT and FG% are the sample; G is
# unique games with a dunk attempt, not games played.
STAT_COLUMNS = (
    ("dunks_made", "DUNKS", 0.92),
    ("dunks_attempted", "ATT", 0.70),
    ("fg_pct", "FG%", 0.80),
    ("games", "G", 0.58),
)
HERO_METRIC = "dunks_made"
CARD_OUTSET_Y = 7.0
CARD_OVERLAP_Y = 3.0
CARD_OUTSET_X = 8.0
HERO_GAP = 22.0


def table_height(row_count: int) -> float:
    """Size the canvas to the rows it holds, with no trailing transparency."""
    return FIRST_ROW_FROM_TOP + (row_count - 1) * ROW_HEIGHT + ROW_HEIGHT / 2 + BOTTOM_PAD


def column_bounds(stats_left: float) -> dict[str, tuple[float, float, str]]:
    """Divide the space right of the name block by each column's width weight."""
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
    """Format one cell."""
    if metric == "fg_pct":
        return f"{float(row['fg_pct']) * 100:.0f}%"
    return f"{int(row[metric])}"


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
    """Draw the face-focused square crop, clipped at this row's separator."""
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
    for start, end in (
        (TABLE_LEFT, hero_left - CARD_OUTSET_X),
        (hero_right + CARD_OUTSET_X, TABLE_RIGHT),
    ):
        ax.plot([start, end], [header_rule_y, header_rule_y],
                color=theme.ink, linewidth=1.5, zorder=3, solid_capstyle="butt")

    draw_accent_card(
        ax, hero_left, hero_right, first_row_y, len(table), ROW_HEIGHT,
        zorder=4, outset_y=CARD_OUTSET_Y, overlap_y=CARD_OVERLAP_Y,
    )

    for row_index, row in table.iterrows():
        y = first_row_y - row_index * ROW_HEIGHT
        if row_index < len(table) - 1:
            rule_y = y - ROW_HEIGHT / 2
            ax.plot([TABLE_LEFT, TABLE_RIGHT], [rule_y, rule_y],
                    color=theme.rule, linewidth=0.9, zorder=1.5)

        for metric, (left, right, _) in columns.items():
            color = "#FFFFFF" if metric == HERO_METRIC else theme.ink
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
    non_ra = int(table["non_ra_makes"].sum())
    non_ra_note = (
        f"{non_ra} of the made dunks on this board sit outside the Restricted Area."
        if non_ra
        else "Every made dunk on this board is labelled Restricted Area."
    )
    return "\n".join(
        [
            "--- CANVA COPY BLOCK ---",
            "",
            "TITLE: MOST DUNKS IN A SEASON",
            "",
            "SUBTITLE: Most made dunks in a Bulls season since 2000",
            "",
            (
                "QUALIFICATION: Bulls player-seasons, 2000-01 to 2025-26 regular "
                "seasons. No games-played minimum — this is a totals board. "
                "Dunks count only what he threw down in a Bulls uniform."
            ),
            "",
            (
                "DEFINITIONS: A dunk is any field-goal attempt whose NBA.com "
                "ACTION_TYPE contains the word dunk, case-insensitive — Driving "
                "Dunk, Alley Oop Dunk, Putback Dunk, Tip Dunk, Reverse Dunk, "
                "Cutting Dunk, and the rest. Makes only (SHOT_MADE_FLAG = 1); "
                "missed dunks sit in ATT, not DUNKS. Restricted Area is not "
                "required. G = unique games with a dunk attempt, not games played. "
                "FG% = made dunks / dunk attempts."
            ),
            "",
            f"ZONE NOTE: {non_ra_note}",
            "",
            (
                f"LEADER: {display_name(leader['PLAYER_NAME'])} threw down "
                f"{int(leader['dunks_made'])} dunks in {leader['SEASON']}, the "
                "most by any Bull in a season since 2000."
            ),
            "",
            "SOURCE: Data via nba.com",
            "",
            "--- END ---",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refetch every season's ShotChartDetail instead of using data/seasons/.",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="Export at final DPI; first-review drafts should omit this.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dunks, audit = load_or_fetch(args.refresh)
    assert_season_coverage(audit)
    seasons = player_seasons(dunks)
    table = prepare_table(seasons)
    report = validate(table, audit)

    WORKING_CSV.parent.mkdir(parents=True, exist_ok=True)
    seasons.sort_values(
        ["dunks_made", "dunks_attempted", "SEASON"],
        ascending=[False, True, False],
        kind="stable",
    ).to_csv(WORKING_CSV, index=False)
    table.to_csv(DISPLAY_CSV, index=False)

    ensure_headshots(table["PLAYER_ID"])
    ensure_silhouette()
    suffix = "final" if args.final else "draft"
    output = render_table(
        table,
        OUTPUT_DIR / f"{PROJECT_DATE}-most-dunks-season-{suffix}.png",
        final=args.final,
    )

    print(json.dumps(report, indent=2))
    print(f"\nWrote {WORKING_CSV}")
    print(f"Wrote {DISPLAY_CSV}")
    print(f"Wrote {output}\n")
    print(canva_copy_block(table, report))


if __name__ == "__main__":
    main()
