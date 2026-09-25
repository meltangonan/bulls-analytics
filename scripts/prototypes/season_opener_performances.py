"""Build the Bulls' top fifteen season-opening performances since 1983-84.

The established top-game-performances prototype owns NBA.com collection,
Hollinger Game Score, reconciliation, and the settled table renderer. This
prototype adds one rule: select the Bulls' first regular-season team game in
each season, then rank every Chicago player-game from those openers together.

The window starts in 1983-84: before it, NBA.com has no Bulls team game log and
most opener box scores lack steals, blocks, turnovers or the rebound split that
Game Score needs. Missing is not zero, so earlier seasons are excluded.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.graphics.house import game_score_fill
from scripts.prototypes import top_game_performances as base


PROJECT = "season-opener-performances"
FIRST_END_YEAR = 1984
TOP_N = 15
# The rookie and sophomore tables' fifteen-row fit for a 1080x1440 page.
TABLE_LAYOUT = replace(base.DECADE_LAYOUT, row_height=108, headshot_x=60, name_x=128,
                       headshot_half_size=66, headshot_rise=8, first_row_from_top=145,
                       bottom_pad=42, name_font_size=21, context_font_size=12.5,
                       name_rise=16, context_drop=22)
DATA_DIR = base._REPO / "docs" / "visuals" / "2026-09-25-season-opener-performances" / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
# Hand-sourced cut-out for a player the NBA CDN serves a silhouette for, copied from the
# 2026-08-20 height ladder post (its data/portraits_source holds the original).
PORTRAITS = {78615: DATA_DIR / "portraits" / "78615.png"}  # Orlando Woolridge


def select_season_openers(team_games: pd.DataFrame) -> pd.DataFrame:
    """Return exactly the first Bulls regular-season team game per season."""
    required = {"season_end_year", "game_id", "game_date", "matchup", "result"}
    missing = required - set(team_games.columns)
    if missing:
        raise ValueError(f"Team games are missing {sorted(missing)}.")

    games = team_games.copy()
    games["season_end_year"] = pd.to_numeric(games["season_end_year"], errors="raise").astype(int)
    games["game_id"] = games["game_id"].astype(str)
    games["game_date_parsed"] = pd.to_datetime(games["game_date"], errors="raise")
    games = games.sort_values(
        ["season_end_year", "game_date_parsed", "game_id"],
        kind="stable",
    )
    openers = games.groupby("season_end_year", sort=True, as_index=False).head(1).copy()
    if openers.duplicated("season_end_year").any():
        raise ValueError("Season opener selection returned more than one game for a season.")
    return openers.drop(columns="game_date_parsed").reset_index(drop=True)


def season_opener_player_games(
    working: pd.DataFrame,
    openers: pd.DataFrame,
) -> pd.DataFrame:
    """Keep all Bulls player-games belonging to the selected team openers."""
    keys = openers[["season_end_year", "game_id"]].copy()
    keys["game_id"] = keys["game_id"].astype(str)
    rows = working.copy()
    rows["game_id"] = rows["game_id"].astype(str)
    selected = rows.merge(
        keys,
        on=["season_end_year", "game_id"],
        how="inner",
        validate="many_to_one",
    )
    opener_years = set(openers["season_end_year"].astype(int))
    selected_years = set(selected["season_end_year"].astype(int))
    if selected_years != opener_years:
        raise ValueError("Every selected season opener must have player-game rows.")
    return selected


def rank_season_openers(rows: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """Rank opener player-games using the settled deterministic tie-breaks."""
    ranked = rows.sort_values(
        ["game_score", "points", "ts_pct", "game_date", "player", "player_id"],
        ascending=[False, False, False, True, True, True],
        kind="stable",
    ).head(top_n).copy()
    if len(ranked) != top_n:
        raise ValueError(f"Expected {top_n} ranked opener performances; got {len(ranked)}.")
    ranked["rank"] = range(1, len(ranked) + 1)
    return ranked.reset_index(drop=True)


def validate_opener_analysis(
    openers: pd.DataFrame,
    selected: pd.DataFrame,
    ranked: pd.DataFrame,
) -> dict[str, object]:
    """Check coverage and preserve the factual claims used in the mock."""
    expected_years = set(range(FIRST_END_YEAR, base.LAST_SEASON_END_YEAR + 1))
    if set(openers["season_end_year"].astype(int)) != expected_years:
        raise ValueError("Season opener source does not cover every season since 1983-84.")
    if openers["game_id"].astype(str).nunique() != len(expected_years):
        raise ValueError("There must be one distinct Bulls opener per season.")
    if selected.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Selected opener rows contain duplicate player-games.")
    # Earlier seasons carry blank box-score fields in some non-opener games, so the
    # completeness and reconciliation checks run on the openers this post uses.
    box_fields = ["minutes", "points", "fgm", "fga", "ftm", "fta", "oreb", "dreb", "ast",
                  "stl", "blk", "tov", "pf"]
    if selected[box_fields].isna().any().any():
        raise ValueError("An opener player-game is missing a Game Score input.")
    if not (selected["minutes"] > 0).all():
        raise ValueError("Selected opener rows include non-playing player-games.")
    per_game = selected.groupby("game_id").agg(player_points=("points", "sum"),
                                               team_points=("team_points", "first"))
    if not per_game["player_points"].eq(per_game["team_points"]).all():
        raise ValueError("Opener player points do not reconcile to the Bulls team score.")
    if len(ranked) != TOP_N or ranked.duplicated(["game_id", "player_id"]).any():
        raise ValueError("The ranking must hold fifteen distinct player-games.")
    return {
        "season_count": len(expected_years),
        "team_game_count": openers["game_id"].nunique(),
        "player_game_count": len(selected),
        "top_score": round(float(ranked.iloc[0]["game_score"]), 1),
        "cutoff_score": round(float(ranked.iloc[-1]["game_score"]), 1),
        "thirty_plus_count": int((ranked["game_score"] >= 30).sum()),
        "player_count": ranked["player"].nunique(),
    }


def write_data(
    players: pd.DataFrame,
    teams: pd.DataFrame,
    openers: pd.DataFrame,
    selected: pd.DataFrame,
    ranked: pd.DataFrame,
) -> None:
    """Ship the display table and fetched inputs beside the visual."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    openers.to_csv(DATA_DIR / "season_openers.csv", index=False)
    selected.to_csv(DATA_DIR / "season_opener_player_games.csv", index=False)
    ranked.to_csv(DATA_DIR / "top_15_season_opener_performances.csv", index=False)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for source in sorted(base.RAW_CACHE.glob("CHI-*-regular-season-*.csv")):
        shutil.copy2(source, RAW_DATA_DIR / source.name)

    # These combined snapshots make the raw grain easy to inspect without
    # changing the one-file-per-endpoint-per-season audit trail above.
    players.to_csv(DATA_DIR / "all_regular_season_player_games.csv", index=False)
    teams.to_csv(DATA_DIR / "all_regular_season_team_games.csv", index=False)


def canva_copy(report: dict[str, object]) -> str:
    """Print the exact framing tied to this analysis run."""
    return "\n".join(
        [
            "CANVA COPY",
            "TITLE: THE BULLS' BEST SEASON OPENERS",
            "SUBTITLE: Top 15 individual performances since 1983-84, ranked by Game Score",
            (
            "FOOTER: Data via nba.com | 1983-84 to 2025-26 regular seasons | "
                "First Bulls team game of each season"
            ),
            (
                "NOTE: Game Score measures box-score productivity. "
                "Overtime games are included and not adjusted. "
                "FG and 3PT show makes–attempts; TOV is turnovers."
            ),
            (
                f"AUDIT: {report['player_game_count']} player-games across "
                f"{report['team_game_count']} season openers; top-fifteen cutoff "
                f"{report['cutoff_score']:.1f}."
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls season-opener performance table.")
    parser.add_argument("--refresh", action="store_true", help="Refetch NBA.com season responses.")
    parser.add_argument("--final", action="store_true", help="Render the chart at final resolution.")
    args = parser.parse_args()

    snapshot = datetime.now(base.SNAPSHOT_TZ)
    players, teams = base.fetch_bulls_history(
        season_type="Regular Season", refresh=args.refresh, first_end_year=FIRST_END_YEAR
    )
    working = base.build_working_table(players, teams)
    openers = select_season_openers(teams)
    selected = season_opener_player_games(working, openers)
    ranked = rank_season_openers(selected)
    report = validate_opener_analysis(openers, selected, ranked)
    write_data(players, teams, openers, selected, ranked)

    base.ensure_headshots(ranked["player_id"].tolist())
    base.ensure_historical_headshot_fallbacks(ranked["player_id"].tolist())
    chart = base.render_chart(
        ranked,
        snapshot.date().isoformat(),
        decade="season-openers",
        season_type="Regular Season",
        show_free_throws=False,
        show_turnovers=True,
        top_n=TOP_N,
        layout=TABLE_LAYOUT,
        final=args.final,
        emphasize_points=True,
        shooting_after_assists=True,
        score_fill=game_score_fill,
        # NBA.com has no plus/minus before 1996-97, so the column would be blank for early rows.
        show_plus_minus=False,
        portraits=PORTRAITS,
    )
    print(f"Chart: {chart}")
    print(f"Data: {DATA_DIR}")
    print(canva_copy(report))
    print()
    print(
        ranked[
            ["rank", "player", "season", "game_date", "matchup", "result", "game_score", "ts_pct"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
