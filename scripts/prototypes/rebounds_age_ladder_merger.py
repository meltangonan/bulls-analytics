"""Render the Bulls rebound age ladder from the 1976-77 merger onward.

NBA.com's LeagueDashPlayerStats endpoint begins in 1996-97, so a literal
"since the merger" ladder cannot use that endpoint for the full window.  This
variant uses the already captured NBA.com PlayerCareerStats rows from the
height ladder (1976-77 onward), joined to NBA.com's TeamYearByYearStats for
the exact Bulls schedule and team reconciliation totals.

The primary asset keeps the published Stocks table grammar.  The alternate
uses the actual Game Score height-post hybrid card geometry, not the compact
table approximation from the first rebound draft.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle
from nba_api.stats.endpoints import teamyearbyyearstats

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from scripts.prototypes import height_ladder_cards as height_cards
from scripts.prototypes.rebounds_age_ladder import (
    COLUMNS,
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    OUT,
    PROJECT_DATA,
    REBOUNDS_FACE_CROP_FRACTION,
    REBOUNDS_LAYOUT,
    REBOUNDS_METRIC_WIDTH,
    REBOUNDS_NAME_COLUMN_GAP,
    REBOUNDS_TRAILING_COLUMNS,
    REBOUNDS_TRAILING_SLOT_WIDTH,
    REBOUNDS_CHART_HEIGHT,
    REBOUNDS_CHART_WIDTH,
    TableLayout,
    age_winners,
    apply_display_names,
    build_working_table,
    display_season_label,
    name_block_width,
    render_chart,
    validate_working_table,
)


MERGER_FIRST_SEASON_END_YEAR = 1977
MERGER_SOURCE_DATA = _REPO / "docs/visuals/2026-08-27-rebounds-age-ladder/data"
TEAM_YEAR_CACHE = _REPO / "cache/nba.com/rebounds-age-ladder/bulls-team-year-by-year.csv"
TEAM_YEAR_SOURCE_URL = f"https://stats.nba.com/stats/teamyearbyyearstats?TeamID={BULLS_TEAM_ID}"

# Fixed raw-RPG anchors keep the red/yellow/green cell meaningful across the
# whole merger window. A league-relative baseline cannot be reconstructed from
# LeagueDashPlayerStats before 1996-97 because that endpoint returns no rows.
RPG_SCALE_MIN = 4.0
RPG_SCALE_MIDPOINT = 8.0
RPG_SCALE_MAX = 16.0

# Exact Game Score height-card footprint, with one more row available so the
# age-43 Robert Parish season is not silently omitted.
HYBRID_RPG_LEFT = 0.895
HYBRID_STATS_START = 0.520
HYBRID_ROWS_TALL = 11


def fetch_team_year_by_year(*, refresh: bool = False) -> pd.DataFrame:
    if TEAM_YEAR_CACHE.exists() and not refresh:
        return pd.read_csv(TEAM_YEAR_CACHE)
    frame = teamyearbyyearstats.TeamYearByYearStats(
        team_id=BULLS_TEAM_ID, timeout=60, headers=_NBA_HEADERS
    ).get_data_frames()[0]
    required = {"YEAR", "GP", "OREB", "DREB", "REB"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"NBA.com team year-by-year response is missing {sorted(missing)}.")
    TEAM_YEAR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(TEAM_YEAR_CACHE, index=False)
    return frame


def build_merger_rows(team_year: pd.DataFrame) -> pd.DataFrame:
    """Turn the height ladder's NBA.com career rows into rebound rows."""
    careers = pd.read_csv(MERGER_SOURCE_DATA / "merger-raw-careers.csv")
    rosters = pd.read_csv(MERGER_SOURCE_DATA / "merger-raw-rosters.csv")
    names = (
        rosters.sort_values("SEASON")
        .drop_duplicates("PLAYER_ID", keep="last")[["PLAYER_ID", "PLAYER"]]
        .rename(columns={"PLAYER": "player"})
    )
    careers["TEAM_ID"] = pd.to_numeric(careers["TEAM_ID"], errors="raise").astype(int)
    careers = careers.loc[
        (careers["TEAM_ID"] == BULLS_TEAM_ID)
        & (careers["SEASON_ID"] >= "1976-77")
    ].copy()
    careers["season_end_year"] = careers["SEASON_ID"].str[:4].astype(int) + 1
    careers["player_id"] = careers["PLAYER_ID"].astype(int)
    careers["player"] = careers["player_id"].map(names.set_index("PLAYER_ID")["player"])
    careers["player"] = careers["player"].fillna(careers["player_id"].astype(str))
    careers["season"] = careers["SEASON_ID"].map(
        lambda value: str(value).replace("-", "–", 1)
    )
    careers["age"] = pd.to_numeric(careers["PLAYER_AGE"], errors="raise").round().astype(int)
    careers["games"] = pd.to_numeric(careers["GP"], errors="raise").astype(int)
    for source, target in (("OREB", "offensive_rebounds"), ("DREB", "defensive_rebounds"), ("REB", "rebounds")):
        careers[target] = pd.to_numeric(careers[source], errors="raise").fillna(0).astype(int)
    careers["offensive_rebounds_per_game"] = careers["offensive_rebounds"] / careers["games"]
    careers["defensive_rebounds_per_game"] = careers["defensive_rebounds"] / careers["games"]
    careers["rebounds_per_game"] = careers["rebounds"] / careers["games"]

    teams = team_year.copy()
    teams["season_end_year"] = teams["YEAR"].str[:4].astype(int) + 1
    teams = teams.loc[teams["season_end_year"].between(MERGER_FIRST_SEASON_END_YEAR, LAST_SEASON_END_YEAR)]
    teams = teams.rename(columns={
        "GP": "team_games", "OREB": "team_offensive_rebounds",
        "DREB": "team_defensive_rebounds", "REB": "team_rebounds",
    })
    joined = careers.merge(
        teams[["season_end_year", "team_games", "team_offensive_rebounds",
               "team_defensive_rebounds", "team_rebounds"]],
        on="season_end_year", how="left", validate="many_to_one",
    )
    if joined[["team_games", "team_offensive_rebounds", "team_defensive_rebounds", "team_rebounds"]].isna().any().any():
        raise ValueError("TeamYearByYearStats did not cover every merger-era Bulls season.")
    joined["player_source_url"] = joined["player_id"].map(
        lambda pid: f"https://stats.nba.com/stats/playercareerstats?PlayerID={int(pid)}&PerMode=Totals"
    )
    joined["team_source_url"] = TEAM_YEAR_SOURCE_URL
    return joined[COLUMNS]


def _rpg_fill(value: float):
    from scripts.prototypes.scoring_age_ladder import ppg_fill
    return ppg_fill(value, RPG_SCALE_MIN, RPG_SCALE_MAX, midpoint=RPG_SCALE_MIDPOINT)


def _hybrid_portrait(ax, row, x: float, bottom: float, height_frac: float, fig_h: float, zorder: int) -> None:
    path = house.HEADSHOT_CACHE / f"{int(row.player_id)}.png"
    try:
        image = plt.imread(path)
    except (FileNotFoundError, OSError, ValueError):
        return
    h, w = image.shape[:2]
    side = min(int(h * REBOUNDS_FACE_CROP_FRACTION), w)
    left = max(0, (w - side) // 2)
    square = image[:side, left:left + side]
    half_x = (height_frac * fig_h / height_cards.FIG_W) / 2
    ax.imshow(square, extent=[x - half_x, x + half_x, bottom, bottom + height_frac],
              interpolation="bilinear", zorder=zorder)
    ax.set_aspect("auto")


def render_height_hybrid(rows: pd.DataFrame, page: int, date: str, *, final: bool = False) -> Path:
    """Use the Game Score height-post's full bordered-card treatment exactly."""
    rows = apply_display_names(rows).reset_index(drop=True)
    fig_h = height_cards.figure_height(HYBRID_ROWS_TALL)
    fig, ax = plt.subplots(figsize=(height_cards.FIG_W, fig_h))
    fig.patch.set_alpha(0)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off(); ax.patch.set_alpha(0); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_aspect("auto"); ax.autoscale(False)
    row_h = height_cards.ROW_H_IN / fig_h
    top = 1 - height_cards.PAD_TOP_IN / fig_h
    stripe_y = height_cards.STRIPE * height_cards.FIG_W / fig_h
    age_right = 0.112
    portrait_x = 0.170
    name_x = 0.235
    for i, (_, row) in enumerate(rows.iterrows()):
        y = top - (i + 0.5) * row_h
        zorder = 10 + i
        box_h = row_h * 0.86
        bottom = y - box_h / 2
        height_cards.striped_box(
            ax, height_cards.X_ROW_L, bottom,
            height_cards.X_ROW_R - height_cards.X_ROW_L, box_h,
            height_cards.BULLS_RED,
            height_cards._mix("#FFFFFF", height_cards.BULLS_RED, 0.11),
            fig_h, zorder=2,
        )
        ax.add_patch(Rectangle(
            (height_cards.X_ROW_L + height_cards.STRIPE, bottom + stripe_y),
            age_right - height_cards.X_ROW_L - height_cards.STRIPE,
            box_h - 2 * stripe_y, facecolor=height_cards.BULLS_RED,
            edgecolor="none", zorder=3,
        ))
        ax.text((height_cards.X_ROW_L + height_cards.STRIPE + age_right) / 2, y,
                str(int(row.age)), fontproperties=house.helvetica("bold"), fontsize=26,
                color="white", ha="center", va="center", zorder=4)
        _hybrid_portrait(ax, row, portrait_x,
                         bottom + height_cards.PORTRAIT_LIFT_IN / fig_h,
                         row_h * height_cards.PORTRAIT_SCALE, fig_h, zorder)
        ax.text(name_x, y + row_h * 0.12, row.player,
                fontproperties=house.helvetica("bold"), fontsize=19,
                color=house.DEFAULT_THEME.ink, ha="left", va="center", zorder=5)
        ax.text(name_x, y - row_h * 0.18,
                f"{row.season} · {int(row.games)} GP",
                fontproperties=house.helvetica(), fontsize=12,
                color=house.DEFAULT_THEME.muted, ha="left", va="center", zorder=5)
        stat_specs = (
            ("DREB", f"{row.defensive_rebounds_per_game:.1f}", 0.055),
            ("ORB", f"{row.offensive_rebounds_per_game:.1f}", 0.050),
            ("GP", int(row.games), 0.040),
        )
        cursor = HYBRID_STATS_START
        for label, value, width in stat_specs:
            x = cursor + width / 2
            ax.text(x, y + row_h * 0.105, str(value), ha="center", va="center",
                    color=house.DEFAULT_THEME.ink, fontsize=19,
                    fontproperties=house.helvetica("bold"), zorder=5)
            ax.text(x, y - row_h * 0.105, label, ha="center", va="center",
                    color=house.DEFAULT_THEME.muted, fontsize=10,
                    fontproperties=house.helvetica("bold"), zorder=5)
            cursor += width + 0.005
        fill = _rpg_fill(row.rebounds_per_game)
        height_cards.striped_box(
            ax, HYBRID_RPG_LEFT, bottom,
            height_cards.X_ROW_R - HYBRID_RPG_LEFT, box_h,
            fill, fill, fig_h, zorder=5,
        )
        from scripts.prototypes.scoring_age_ladder import ppg_text_color
        ax.text((HYBRID_RPG_LEFT + height_cards.X_ROW_R) / 2, y,
                f"{row.rebounds_per_game:.1f}", fontproperties=house.helvetica("bold"),
                fontsize=21.5, color=ppg_text_color(fill), ha="center", va="center",
                zorder=7)
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "final" if final else "draft"
    path = OUT / f"{date}-bulls-rebounds-age-ladder-since-merger-height-hybrid-p{page}-{suffix}.png"
    fig.savefig(path, dpi=400 if final else 200, transparent=True)
    plt.close(fig)
    return path


def render_merger_table(winners: pd.DataFrame, date: str, *, final: bool = False) -> Path:
    """Render a since-merger one-slide Stocks-style table with fixed RPG colors."""
    merger_layout = TableLayout(
        header_y=1211, header_rule_y=1186, first_row_y=1154,
        row_height=56, headshot_half_size=37, headshot_rise=5,
        header_font_size=15.5, name_font_size=18, age_font_size=17,
        ppg_font_size=18, season_font_size=10, season_rise=10.5,
    )
    return render_chart(
        apply_display_names(winners), date, slug="one-slide",
        layout=merger_layout, scale_min=RPG_SCALE_MIN, scale_max=RPG_SCALE_MAX,
        fill_midpoint=RPG_SCALE_MIDPOINT, metric_column="rebounds_per_game",
        metric_header="RPG", metric_decimals=1,
        output_stem="bulls-rebounds-age-ladder-since-merger",
        trailing_columns=REBOUNDS_TRAILING_COLUMNS,
        chart_width=REBOUNDS_CHART_WIDTH, chart_height=REBOUNDS_CHART_HEIGHT + 56,
        auto_name_column=True, name_column_gap=REBOUNDS_NAME_COLUMN_GAP,
        metric_width=REBOUNDS_METRIC_WIDTH,
        trailing_slot_width=REBOUNDS_TRAILING_SLOT_WIDTH,
        face_crop_fraction=REBOUNDS_FACE_CROP_FRACTION,
        # The supplied/archived Artis portrait is a wide source image. Keep
        # more of its vertical frame so his neck remains visible and the afro
        # does not dominate the row.
        portrait_crop_overrides={600014: 0.90},
        clip_portraits_to_row=True, final=final,
    )


def write_merger_data(table: pd.DataFrame, winners: pd.DataFrame, team_year: pd.DataFrame) -> None:
    PROJECT_DATA.mkdir(parents=True, exist_ok=True)
    table.to_csv(PROJECT_DATA / "bulls-rebounds-age-ladder-since-merger-working.csv", index=False)
    winners.to_csv(PROJECT_DATA / "bulls-rebounds-age-ladder-since-merger-winners.csv", index=False)
    team_year.to_csv(PROJECT_DATA / "bulls-team-year-by-year.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    team_year = fetch_team_year_by_year(refresh=args.refresh)
    table = build_working_table(build_merger_rows(team_year))
    report = validate_working_table(
        table,
        first_season_end_year=MERGER_FIRST_SEASON_END_YEAR,
        reconcile_team_totals=False,
    )
    winners = age_winners(table)
    write_merger_data(table, winners, team_year)
    player_ids = sorted(set(winners["player_id"].astype(int)))
    house.ensure_headshots(player_ids)
    from scripts.prototypes.scoring_age_ladder import ensure_historical_headshot_fallbacks
    ensure_historical_headshot_fallbacks(player_ids)
    date = "2026-08-27"
    print(f"Stocks-style since merger: {render_merger_table(winners, date, final=args.final)}")
    print("CANVA COPY")
    print("TITLE: THE BULLS' REBOUND AGE LADDER")
    print("SUBTITLE: Highest RPG by a Bull at every age since the 1976–77 merger")
    print("FOOTER: NBA.com | 1976–77 to 2025–26 regular seasons | Min. 50% of team games | Age as listed by NBA.com")
    print("NOTE: RPG is total rebounds per game; DREB and ORB are shown as context.")
    print("NOTE: NBA.com player-career totals are used for the full merger window; the NBA player league baseline begins in 1996–97, so RPG shading uses fixed 4/8/16 anchors.")
    print(f"AUDIT: {report['age_count']} ages, {report['youngest_age']}–{report['oldest_age']}; {report['qualified_count']} qualifying player-seasons across {report['season_count']} Bulls seasons.")


if __name__ == "__main__":
    main()
