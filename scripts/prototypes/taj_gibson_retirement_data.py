"""Prepare the verified inputs for the Taj Gibson retirement post.

Five display-ready tables, each written as its own CSV so a spacing change can
re-render without refetching:

* ``season-regular.csv``  per-game Bulls line by season, plus a career row
* ``season-playoffs.csv`` the same for his six Bulls postseasons
* ``top-games.csv``       best five by Game Score, playoffs included, with the
                          round/game marker derived from each playoff game id
* ``career-highs.csv``    single-game best in each category, playoffs included
* ``franchise-ranks.csv`` all-time Bulls rank in twelve categories
* ``milestones.csv``      how often he cleared each threshold, and the share

Three sources, cross-checked against each other:

``PlayerCareerStats`` supplies the per-game season splits, including games
started, which the cached game logs do not carry. ``FranchisePlayers`` supplies
every Bull's career totals, which is what the ranks are computed against.
The cached Chicago player-game logs under the primary checkout supply the
game-level rows for the best-games and career-high tables.

Rank pools differ by category and the difference is load-bearing. The NBA did
not record blocks, steals, or the offensive/defensive rebound split before
1973-74, so 38 early Bulls carry no value in those columns and are excluded
from those pools rather than counted as zero. ``pool`` records which population
each rank was measured against so the rendered page can qualify it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS

# The game logs live in the primary checkout's gitignored cache, which linked
# worktrees do not share. Read them in place rather than copying the tree.
PRIMARY_GAME_LOGS = Path(
    "/Users/meltangonan/projects/bulls-analytics/cache/nba.com/top-game-performances"
)
DEFAULT_OUT = _REPO / "docs/visuals/2026-09-15-taj-gibson-retirement/data"

TAJ_ID = 201959
TAJ = "Taj Gibson"

# Conventional box-score reading order, with points promoted to the top and
# games played moved to the bottom: the post leads on the headline counting
# stat and closes on the durability that explains every other row.
RANK_CATEGORIES = (
    ("PTS", "Points"),
    ("FGM", "Field goals made"),
    ("FGA", "Field goal attempts"),
    ("FTM", "Free throws made"),
    ("FTA", "Free throw attempts"),
    ("OREB", "Offensive rebounds"),
    ("DREB", "Defensive rebounds"),
    ("REB", "Total rebounds"),
    ("AST", "Assists"),
    ("STL", "Steals"),
    ("BLK", "Blocks"),
    ("GP", "Games played"),
)

# Categories the NBA began recording in 1973-74. Their ranks are measured
# against a smaller pool, and the page must say so.
PARTIAL_COVERAGE = {"OREB", "DREB", "STL", "BLK"}

# Eight, which fills the four-wide grid exactly rather than leaving a hole.
CAREER_HIGH_CATEGORIES = (
    ("points", "Points"),
    ("reb", "Rebounds"),
    ("oreb", "Offensive rebounds"),
    ("dreb", "Defensive rebounds"),
    ("blk", "Blocks"),
    ("ast", "Assists"),
    ("stl", "Steals"),
    ("plus_minus", "Plus-minus"),
)

# "How often did he do it", as distinct from "what was his best night". Each
# entry is a label and a predicate over his regular-season player-game rows.
# Thresholds are basketball-conventional, not tuned to flatter the totals.
# Every threshold here is an achievement, not a rate in disguise. "Games with
# a block" and "games with an offensive rebound" were cut for that reason:
# at 67% and 87% they restate his per-game averages rather than marking
# anything he had to reach for, and the season tables already carry those.
MILESTONES = (
    ("Double-doubles", lambda g: (g.points >= 10) & (g.reb >= 10)),
    ("Games in double figures", lambda g: g.points >= 10),
    ("20-point games", lambda g: g.points >= 20),
    ("10-rebound games", lambda g: g.reb >= 10),
    ("15-rebound games", lambda g: g.reb >= 15),
    ("5+ offensive rebound games", lambda g: g.oreb >= 5),
    ("3+ block games", lambda g: g.blk >= 3),
    ("5+ block games", lambda g: g.blk >= 5),
    # Not the Win Shares metric: this is simply the team's record in the games
    # he played, which is why it is labelled as games won rather than a share.
    ("Games won", lambda g: g.result == "W"),
)

GAME_NUMERIC = (
    "points", "reb", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf",
    "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "minutes", "game_score", "ts_pct",
)

# Verified 2026-09-15 against both FranchisePlayers and the cached game logs.
EXPECTED_CAREER = {"GP": 562, "PTS": 5280, "REB": 3586, "BLK": 695}
EXPECTED_PLAYOFF_GAMES = 56


def _load_game_logs(kind: str) -> pd.DataFrame:
    """Read Taj's cached Chicago player-game rows for one season type."""
    pattern = f"CHI-players-{kind}-*.csv"
    paths = sorted(PRIMARY_GAME_LOGS.glob(pattern))
    if not paths:
        raise FileNotFoundError(
            f"No cached {kind} game logs under {PRIMARY_GAME_LOGS}. "
            "Run scripts/prototypes/top_game_performances.py to populate them."
        )
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    taj = frame[frame["player"] == TAJ].copy()
    for column in GAME_NUMERIC:
        taj[column] = pd.to_numeric(taj[column], errors="coerce")
    if taj[["points", "reb", "game_score"]].isna().any().any():
        raise ValueError("A cached Taj Gibson game row is missing a needed value.")
    return taj


def _career_stats_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-game and total season splits for Taj's Bulls stints only."""
    from nba_api.stats.endpoints import playercareerstats

    def fetch(per_mode: str) -> dict[str, pd.DataFrame]:
        endpoint = playercareerstats.PlayerCareerStats(
            player_id=TAJ_ID, per_mode36=per_mode, headers=_NBA_HEADERS, timeout=60
        )
        names = list(endpoint.get_normalized_dict().keys())
        return dict(zip(names, endpoint.get_data_frames()))

    per_game = fetch("PerGame")
    totals = fetch("Totals")
    return per_game, totals


def _season_table(per_game: pd.DataFrame, totals: pd.DataFrame, label: str) -> pd.DataFrame:
    """One per-game season table with a career row derived from the totals.

    The career row is computed from summed totals rather than by averaging the
    per-game rows, which would weight a 55-game season like an 82-game one.
    """
    pg = per_game[per_game["TEAM_ABBREVIATION"] == "CHI"].copy()
    tot = totals[totals["TEAM_ABBREVIATION"] == "CHI"].copy()
    if pg.empty:
        raise ValueError(f"No Chicago {label} seasons returned for {TAJ}.")

    rows = [
        {
            "season": row.SEASON_ID,
            "games": int(row.GP),
            "starts": int(row.GS),
            "minutes": float(row.MIN),
            "points": float(row.PTS),
            "rebounds": float(row.REB),
            "offensive_rebounds": float(row.OREB),
            "blocks": float(row.BLK),
            "fg_pct": float(row.FG_PCT),
            "is_career": False,
        }
        for row in pg.itertuples()
    ]

    games = int(tot["GP"].sum())
    starts = int(tot["GS"].sum())

    def per(column: str) -> float:
        return float(tot[column].sum()) / games

    rows.append({
        # Named for the team, not just "Career": he also played for Oklahoma
        # City, Minnesota, New York, Washington and Charlotte, and this row is
        # only the Chicago stint.
        "season": "Bulls career",
        "games": games,
        "starts": starts,
        "minutes": per("MIN"),
        "points": per("PTS"),
        "rebounds": per("REB"),
        "offensive_rebounds": per("OREB"),
        "blocks": per("BLK"),
        # Recomputed from made and attempted, never averaged from season rates.
        "fg_pct": float(tot["FGM"].sum()) / float(tot["FGA"].sum()),
        "is_career": True,
    })
    return pd.DataFrame(rows)


def playoff_label(game_id: str) -> str:
    """Round and game marker for a playoff game id, e.g. "(RD 1 GM4)".

    NBA playoff ids are ``004`` + two season digits + filler, then one digit
    each for round, series and game. Deriving it beats the hand-kept lookup the
    game-score-by-height post used, which only covered the single playoff game
    on that ladder. Regular-season ids return an empty label.
    """
    text = str(game_id).zfill(10)
    if not text.startswith("004"):
        return ""
    round_no, game_no = text[7], text[9]
    return f"(RD {int(round_no)} GM{int(game_no)})"


def _top_games(regular: pd.DataFrame, playoffs: pd.DataFrame, count: int = 5) -> pd.DataFrame:
    """Best games by Game Score across both season types.

    Playoffs are included because his single best game is one, and because
    ranking only the regular season leaves a tie straddling the fifth slot.
    """
    combined = pd.concat([
        regular.assign(season_type="Regular season"),
        playoffs.assign(season_type="Playoffs"),
    ], ignore_index=True)
    best = combined.sort_values("game_score", ascending=False).head(count).copy()
    best["rank"] = best["game_score"].rank(ascending=False, method="min").astype(int)
    best["opponent"] = (
        best["matchup"].str.replace("CHI vs. ", "vs ", regex=False)
        .str.replace("CHI @ ", "at ", regex=False)
    )
    best["playoff_label"] = best["game_id"].map(playoff_label)
    # The whole box-score line travels with the row: the boxed leaderboard
    # format shows made-attempted splits, not just the derived percentages.
    return best[[
        "rank", "game_id", "game_date", "opponent", "playoff_label", "result",
        "season_type", "minutes",
        "points", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
        "reb", "ast", "stl", "blk", "tov", "plus_minus", "ts_pct", "game_score",
    ]].reset_index(drop=True)


def _career_highs(regular: pd.DataFrame, playoffs: pd.DataFrame) -> pd.DataFrame:
    """Single-game best in each category across his whole Bulls career.

    Playoffs are included because they are part of the career: his best
    scoring night as a Bull was 32 points at Washington in the 2014 first
    round, and a "career high" slide that reported the regular-season 26 would
    simply be wrong. ``in_playoffs`` marks the rows where that matters.

    Several of these are ties, and the tie count is reported on every row
    rather than only where it flatters him. The named game is the highest
    Game Score among the tied nights.
    """
    combined = pd.concat([
        regular.assign(season_type="Regular season"),
        playoffs.assign(season_type="Playoffs"),
    ], ignore_index=True)

    rows = []
    for column, label in CAREER_HIGH_CATEGORIES:
        high = combined[column].max()
        tied = combined[combined[column] == high]
        best = tied.sort_values("game_score", ascending=False).iloc[0]
        rows.append({
            "category": label,
            "value": float(high),
            "times": int(len(tied)),
            "game_date": best.game_date,
            "opponent": best.matchup.replace("CHI vs. ", "vs ").replace("CHI @ ", "at "),
            "in_playoffs": bool(best.season_type == "Playoffs"),
            # What the same category peaked at in the regular season alone, so
            # a reader can see which highs the postseason actually moved.
            "regular_season_value": float(regular[column].max()),
        })
    return pd.DataFrame(rows)


def _milestones(regular: pd.DataFrame) -> pd.DataFrame:
    """How often he cleared each threshold, with the share of games it took.

    The share is what makes a count mean anything: 375 games with a block is
    only impressive once you know it was two thirds of the games he played.
    """
    games = len(regular)
    if not games:
        raise ValueError("No regular-season games to count milestones over.")
    return pd.DataFrame([
        {
            "milestone": label,
            "games": int(predicate(regular).sum()),
            "share": float(predicate(regular).mean()),
            "of_games": games,
        }
        for label, predicate in MILESTONES
    ])


def _franchise_ranks() -> pd.DataFrame:
    """Taj's all-time Bulls rank in each category, with its measured pool."""
    from nba_api.stats.endpoints import franchiseplayers

    frame = franchiseplayers.FranchisePlayers(
        team_id=BULLS_TEAM_ID, headers=_NBA_HEADERS, timeout=60
    ).get_data_frames()[0]
    regular = frame[frame["SEASON_TYPE"] == "Regular Season"].copy()

    rows = []
    for column, label in RANK_CATEGORIES:
        regular[column] = pd.to_numeric(regular[column], errors="coerce")
        # Players with no recorded value are dropped, not treated as zero.
        pool = regular.dropna(subset=[column]).sort_values(column, ascending=False)
        pool = pool.reset_index(drop=True)
        pool["rank"] = pool[column].rank(ascending=False, method="min").astype(int)
        taj = pool[pool["PLAYER"] == TAJ]
        if taj.empty:
            raise ValueError(f"{TAJ} is missing from the franchise {column} pool.")
        rows.append({
            "category": label,
            "stat": column,
            "total": int(taj[column].iloc[0]),
            "rank": int(taj["rank"].iloc[0]),
            "pool": len(pool),
            "partial_coverage": column in PARTIAL_COVERAGE,
        })
    return pd.DataFrame(rows)


def _reconcile(
    ranks: pd.DataFrame,
    regular_games: pd.DataFrame,
    playoff_games: pd.DataFrame,
    season_regular: pd.DataFrame,
) -> None:
    """Cross-check three independent sources before anything is written."""
    by_stat = ranks.set_index("stat")["total"].to_dict()
    for stat, expected in EXPECTED_CAREER.items():
        if by_stat[stat] != expected:
            raise ValueError(
                f"FranchisePlayers {stat} is {by_stat[stat]}, expected {expected}."
            )

    # The cached game logs must reproduce the franchise totals independently.
    log_totals = {
        "GP": len(regular_games),
        "PTS": int(regular_games["points"].sum()),
        "REB": int(regular_games["reb"].sum()),
        "BLK": int(regular_games["blk"].sum()),
    }
    for stat, expected in EXPECTED_CAREER.items():
        if log_totals[stat] != expected:
            raise ValueError(
                f"Cached game logs give {stat} = {log_totals[stat]}, expected {expected}."
            )

    # And the per-game season splits must sum to the same games played.
    season_games = int(season_regular.loc[~season_regular["is_career"], "games"].sum())
    if season_games != EXPECTED_CAREER["GP"]:
        raise ValueError(
            f"Season splits sum to {season_games} games, expected {EXPECTED_CAREER['GP']}."
        )

    if len(playoff_games) != EXPECTED_PLAYOFF_GAMES:
        raise ValueError(
            f"Cached playoff logs give {len(playoff_games)} games, "
            f"expected {EXPECTED_PLAYOFF_GAMES}."
        )


def build(out_dir: Path) -> dict[str, Path]:
    regular_games = _load_game_logs("regular-season")
    playoff_games = _load_game_logs("playoffs")

    per_game, totals = _career_stats_frames()
    season_regular = _season_table(
        per_game["SeasonTotalsRegularSeason"], totals["SeasonTotalsRegularSeason"], "regular"
    )
    season_playoffs = _season_table(
        per_game["SeasonTotalsPostSeason"], totals["SeasonTotalsPostSeason"], "playoff"
    )

    ranks = _franchise_ranks()
    _reconcile(ranks, regular_games, playoff_games, season_regular)

    tables = {
        "season-regular.csv": season_regular,
        "season-playoffs.csv": season_playoffs,
        "top-games.csv": _top_games(regular_games, playoff_games),
        "career-highs.csv": _career_highs(regular_games, playoff_games),
        "franchise-ranks.csv": ranks,
        "milestones.csv": _milestones(regular_games),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, frame in tables.items():
        path = out_dir / name
        frame.to_csv(path, index=False)
        written[name] = path
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    for name, path in build(args.out).items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
