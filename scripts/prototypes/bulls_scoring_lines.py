#!/usr/bin/env python3
"""Render individual 2025-26 Bulls scoring-line assets for Canva.

The comparison population is every player with at least 20 Chicago regular-
season appearances. Each asset repeats that qualified cohort in quiet gray,
then highlights one player's Bulls-only scoring line and PPG reference in red.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator
from nba_api.stats.endpoints import playergamelogs

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house


STATS_SEASON = "2025-26"
SEASON_TYPE = "Regular Season"
MIN_GAMES = 20
ROLLING_GAMES = 10
ROLLING_MIN_PERIODS = 5
PLAYER_LOGS_URL = "https://stats.nba.com/stats/playergamelogs"

QUIET_LINE = "#C9C4BD"


def rolling_points(
    featured: pd.DataFrame,
    *,
    window: int = ROLLING_GAMES,
    min_periods: int = ROLLING_MIN_PERIODS,
) -> pd.Series:
    """Return a trailing scoring average that preserves chronological order."""
    return featured["points"].rolling(window=window, min_periods=min_periods).mean()


def fetch_inputs() -> pd.DataFrame:
    """Fetch every Chicago player-game row from the 2025-26 regular season."""
    logs = playergamelogs.PlayerGameLogs(
        season_nullable=STATS_SEASON,
        season_type_nullable=SEASON_TYPE,
        team_id_nullable=str(BULLS_TEAM_ID),
        timeout=60,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    required = {
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GAME_ID",
        "GAME_DATE",
        "MATCHUP",
        "MIN",
        "PTS",
    }
    missing = required.difference(logs.columns)
    if missing:
        raise RuntimeError(f"PlayerGameLogs missing columns: {sorted(missing)}")

    return logs


def prepare_data(logs: pd.DataFrame, min_games: int = MIN_GAMES) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize Bulls games and select players meeting the appearance floor."""
    games = logs.rename(
        columns={
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "source_player_name",
            "TEAM_ABBREVIATION": "team_abbreviation",
            "GAME_ID": "game_id",
            "GAME_DATE": "game_date",
            "MATCHUP": "matchup",
            "MIN": "minutes",
            "PTS": "points",
        }
    )[
        [
            "player_id",
            "source_player_name",
            "team_abbreviation",
            "game_id",
            "game_date",
            "matchup",
            "minutes",
            "points",
        ]
    ].copy()
    games["player_id"] = pd.to_numeric(games["player_id"], errors="raise").astype(int)
    games["game_date"] = pd.to_datetime(games["game_date"], errors="raise")
    games["points"] = pd.to_numeric(games["points"], errors="raise").astype(int)
    games["minutes"] = pd.to_numeric(games["minutes"], errors="raise")
    games = games.sort_values(["player_id", "game_date", "game_id"])
    games["game_number"] = games.groupby("player_id").cumcount() + 1

    summary = (
        games.groupby("player_id", as_index=False)
        .agg(
            games_played=("game_id", "nunique"),
            total_points=("points", "sum"),
            ppg=("points", "mean"),
            max_points=("points", "max"),
            teams=("team_abbreviation", lambda s: "/".join(dict.fromkeys(s))),
        )
    )
    names = games[["player_id", "source_player_name"]].drop_duplicates("player_id")
    audit = names.merge(summary, on="player_id", how="left")
    audit = audit.rename(columns={"source_player_name": "player_name"})
    audit["qualifies"] = audit["games_played"] >= min_games
    audit["ppg"] = audit["ppg"].round(1)
    audit = audit.sort_values(
        ["qualifies", "ppg", "games_played", "player_name"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    qualified_ids = set(audit.loc[audit["qualifies"], "player_id"])
    qualified_games = games[games["player_id"].isin(qualified_ids)].copy()
    return qualified_games, audit


def render_player(
    games: pd.DataFrame,
    audit: pd.DataFrame,
    player_name: str,
    output_path: Path,
    *,
    axes_rect: tuple[float, float, float, float] | None = None,
    y_max: float = 50,
    visible_y_max: float | None = None,
    dpi: int = 150,
    rolling_games: int = ROLLING_GAMES,
    rolling_min_periods: int = ROLLING_MIN_PERIODS,
    pixel_width: int = 1200,
    pixel_height: int = 1200,
) -> None:
    """Render one transparent, fixed-size player chart for placement in Canva."""
    qualified = audit[audit["qualifies"]]
    match = qualified[qualified["player_name"] == player_name]
    if match.empty:
        raise ValueError(f"{player_name!r} is not in the {MIN_GAMES}-game qualified cohort")
    player = match.iloc[0]
    featured = games[games["player_id"] == player["player_id"]]

    fig = plt.figure(figsize=(pixel_width / dpi, pixel_height / dpi), dpi=dpi)
    ax = fig.add_axes(axes_rect or (0.035, 0.025, 0.945, 0.96))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    bold = house.helvetica("bold")

    for player_id in qualified["player_id"]:
        other = games[games["player_id"] == player_id]
        ax.plot(
            other["game_number"],
            other["points"],
            color=QUIET_LINE,
            linewidth=1.25,
            alpha=0.30,
            zorder=1,
        )

    ax.hlines(
        float(player["ppg"]),
        xmin=1,
        xmax=82,
        color=house.RED,
        linewidth=1.8,
        linestyle=(0, (4, 3)),
        alpha=0.82,
        zorder=2,
    )
    ax.plot(
        featured["game_number"],
        featured["points"],
        color=house.RED,
        linewidth=2.0,
        alpha=0.38,
        zorder=3,
    )
    ax.plot(
        featured["game_number"],
        rolling_points(
            featured,
            window=rolling_games,
            min_periods=rolling_min_periods,
        ),
        color=house.RED,
        linewidth=5.0,
        alpha=0.98,
        zorder=4,
    )
    ax.text(
        84,
        float(player["ppg"]),
        f"{player['ppg']:.1f} PPG",
        ha="left",
        va="center",
        color=house.RED,
        fontproperties=bold,
        fontsize=18,
        zorder=5,
        clip_on=False,
    )

    ax.set_xlim(1, 99)
    ax.set_ylim(-2.5, y_max)
    visible_y_max = y_max if visible_y_max is None else visible_y_max
    ax.xaxis.set_major_locator(MultipleLocator(20))
    ax.set_yticks(list(range(0, int(visible_y_max), 10)))
    ax.grid(False)
    for side, spine in ax.spines.items():
        spine.set_visible(side in {"left", "bottom"})
        spine.set_color(house.BLACK)
        spine.set_linewidth(1.8)
    ax.spines["bottom"].set_position(("data", 0))
    ax.spines["left"].set_bounds(0, visible_y_max)
    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        length=7,
        width=1.4,
        colors=house.BLACK,
        labelbottom=False,
        labelleft=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, transparent=True)
    plt.close(fig)


def save_data(games: pd.DataFrame, audit: pd.DataFrame, data_dir: Path) -> None:
    """Save the exact chart population, source rows, and audit metadata."""
    data_dir.mkdir(parents=True, exist_ok=True)
    games_out = games.copy()
    games_out["stats_season"] = STATS_SEASON
    games_out["season_type"] = SEASON_TYPE
    games_out["source_url"] = PLAYER_LOGS_URL
    games_out["captured_on"] = date.today().isoformat()
    games_out.to_csv(data_dir / "qualified_bulls_player_game_points.csv", index=False)

    audit_out = audit.copy()
    audit_out["ppg_formula"] = "total_points / games_played"
    audit_out["stats_season"] = STATS_SEASON
    audit_out["minimum_bulls_games"] = MIN_GAMES
    audit_out.to_csv(data_dir / "bulls_scoring_qualification_audit.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--players",
        nargs="+",
        help="Qualified players to render; omit to render the complete cohort",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/bulls_scoring_lines"))
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("docs/visuals/2026-09-20-current-roster-scoring-lines/data"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_logs = fetch_inputs()
    games, audit = prepare_data(raw_logs)
    save_data(games, audit, args.data_dir)
    player_names = args.players or audit.loc[audit["qualifies"], "player_name"].tolist()
    for player_name in player_names:
        slug = player_name.lower().replace(" ", "-")
        output = args.output_dir / f"{slug}-scoring-line.png"
        render_player(games, audit, player_name, output)
        print(f"Saved {output}")
    print(audit.to_string(index=False))


if __name__ == "__main__":
    main()
