"""Build the Bulls' top combined-scoring duo games since 2000-01.

Each Bulls game contributes one duo: the two highest-scoring Chicago players in
that game. Rows are ranked on their combined points. The two leading scorers
also maximise the lower half of any pair drawn from the same game, so no
separate balance qualifier is applied; the resulting top fifteen is naturally
balanced and the selection audit records how far the gap ever widens.

Source rows, the player/team score reconciliation and the season coverage check
all come from ``top_game_performances``; this prototype only adds duo
selection, tie handling and the share-of-team-points calculation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import pandas as pd

from scripts.prototypes.top_game_performances import (
    FIRST_SEASON_END_YEAR,
    LAST_SEASON_END_YEAR,
    MINUTES_REPORT_THRESHOLD,
    build_working_table,
    display_season_label,
    fetch_bulls_history,
    minute_reconciliation,
)

TOP_N = 15
PROJECT = "top-scoring-duo-games"
DEFAULT_DATA_DIR = _REPO / "docs" / "visuals" / "2026-09-13-top-scoring-duo-games" / "data"

# Names carried at their NBA.com spelling everywhere except the rendered label.
DISPLAY_NAME_FIXES = {"Jimmy Butler III": "Jimmy Butler"}


def display_name(full_name: str) -> str:
    return DISPLAY_NAME_FIXES.get(str(full_name), str(full_name))


def overtime_periods(table: pd.DataFrame) -> pd.Series:
    return minute_reconciliation(table)["overtime_periods"]


def select_duos(table: pd.DataFrame) -> pd.DataFrame:
    """Reduce every Bulls game to its two highest-scoring players.

    Ordering is points first, then minutes, then player_id, so a tie at either
    slot resolves the same way on every run. ``second_tied_with`` counts the
    other players who matched the second scorer's points, because those games
    could have named a different partner.
    """
    ordered = table.sort_values(
        ["game_id", "points", "minutes", "player_id"],
        ascending=[True, False, False, True],
        kind="stable",
    )
    pair = ordered.groupby("game_id", sort=False).head(2)
    counts = pair.groupby("game_id").size()
    if (counts != 2).any():
        short = counts[counts != 2].index.tolist()
        raise ValueError(f"Games without two scoring players: {short}")

    first = pair.groupby("game_id", sort=False).nth(0).reset_index(drop=True)
    second = pair.groupby("game_id", sort=False).nth(1).reset_index(drop=True)

    duos = pd.DataFrame(
        {
            "game_id": first["game_id"].to_numpy(),
            "season_end_year": first["season_end_year"].to_numpy(),
            "season": first["season"].to_numpy(),
            "game_date": first["game_date"].to_numpy(),
            "matchup": first["matchup"].to_numpy(),
            "opponent": first["opponent"].to_numpy(),
            "result": first["result"].to_numpy(),
            "team_points": first["team_points"].to_numpy(),
            "player_1_id": first["player_id"].to_numpy(),
            "player_1": first["player"].to_numpy(),
            "player_1_points": first["points"].to_numpy(),
            "player_1_minutes": first["minutes"].to_numpy(),
            "player_2_id": second["player_id"].to_numpy(),
            "player_2": second["player"].to_numpy(),
            "player_2_points": second["points"].to_numpy(),
            "player_2_minutes": second["minutes"].to_numpy(),
        }
    )
    duos["combined_points"] = duos["player_1_points"] + duos["player_2_points"]
    duos["point_gap"] = duos["player_1_points"] - duos["player_2_points"]
    duos["team_share_pct"] = duos["combined_points"] / duos["team_points"] * 100

    # Other players who matched the second scorer exactly; >0 means the partner
    # was chosen by tiebreak rather than by points alone.
    second_points = duos.set_index("game_id")["player_2_points"]
    matched = table.assign(second=table["game_id"].map(second_points))
    matched = matched[matched["points"] == matched["second"]]
    tie_counts = matched.groupby("game_id").size() - 1
    duos["second_tied_with"] = duos["game_id"].map(tie_counts).fillna(0).astype(int)

    duos["overtime_periods"] = duos["game_id"].map(overtime_periods(table)).astype(int)
    duos["overtime_label"] = duos["overtime_periods"].map(
        lambda n: "" if n == 0 else ("OT" if n == 1 else f"{n}OT")
    )

    return duos.sort_values(
        ["combined_points", "player_2_points", "game_date"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)


def build_top(duos: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    top = duos.head(top_n).copy()
    top.insert(0, "rank", range(1, len(top) + 1))
    top["player_1_label"] = top["player_1"].map(display_name)
    top["player_2_label"] = top["player_2"].map(display_name)
    top["season_label"] = top["season"].astype(str).str.replace("–", "-", regex=False)
    return top


def selection_audit(duos: pd.DataFrame, top: pd.DataFrame) -> dict[str, object]:
    """Record the facts a reader could challenge about this selection."""
    cutoff = int(top["combined_points"].min())
    at_cutoff = duos[duos["combined_points"] == cutoff]
    return {
        "games_considered": int(len(duos)),
        "seasons_covered": int(duos["season_end_year"].nunique()),
        "first_season": display_season_label(FIRST_SEASON_END_YEAR),
        "last_season": display_season_label(LAST_SEASON_END_YEAR),
        "cutoff_combined_points": cutoff,
        "games_at_cutoff": int(len(at_cutoff)),
        "rows_beyond_cutoff_excluded": int(max(0, len(at_cutoff) - (top["combined_points"] == cutoff).sum())),
        "lowest_second_scorer_in_top": int(top["player_2_points"].min()),
        "widest_gap_in_top": int(top["point_gap"].max()),
        "top_rows_with_tied_second": int((top["second_tied_with"] > 0).sum()),
        "overtime_games_in_top": int((top["overtime_periods"] > 0).sum()),
        "overtime_share_all_games_pct": round(float((duos["overtime_periods"] > 0).mean() * 100), 1),
        "max_share_pct": round(float(top["team_share_pct"].max()), 1),
        "min_share_pct": round(float(top["team_share_pct"].min()), 1),
    }


def season_audit(table: pd.DataFrame, duos: pd.DataFrame) -> pd.DataFrame:
    """One row per season: games seen and the best duo total in it."""
    games = table.groupby("season_end_year")["game_id"].nunique().rename("games")
    best = duos.groupby("season_end_year")["combined_points"].max().rename("best_duo_points")
    audit = pd.concat([games, best], axis=1).reset_index()
    audit["season"] = audit["season_end_year"].map(display_season_label)
    return audit[["season_end_year", "season", "games", "best_duo_points"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--top-n", type=int, default=TOP_N)
    parser.add_argument("--refresh", action="store_true", help="Re-request NBA.com instead of cache")
    args = parser.parse_args()

    players, teams = fetch_bulls_history(refresh=args.refresh)
    table = build_working_table(players, teams)
    duos = select_duos(table)
    top = build_top(duos, args.top_n)

    args.data_dir.mkdir(parents=True, exist_ok=True)
    duos.to_csv(args.data_dir / "all_duo_games.csv", index=False)
    top.to_csv(args.data_dir / "top15.csv", index=False)
    season_audit(table, duos).to_csv(args.data_dir / "season_audit.csv", index=False)

    minutes = minute_reconciliation(table)
    flagged = minutes[minutes["minutes_deviation"].abs() > MINUTES_REPORT_THRESHOLD]
    flagged.to_csv(args.data_dir / "minutes_reconciliation_exceptions.csv")
    if not flagged.empty:
        print(f"Minutes deviating past {MINUTES_REPORT_THRESHOLD:g}: {len(flagged)} game(s)")
        print(flagged.to_string())

    audit = selection_audit(duos, top)
    pd.Series(audit).to_frame("value").to_csv(args.data_dir / "selection_audit.csv")
    for key, value in audit.items():
        print(f"{key}: {value}")
    print(f"\nWrote {args.data_dir}")


if __name__ == "__main__":
    main()
