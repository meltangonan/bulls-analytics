"""Prepare the Bulls career leaderboard for made 27–39-foot threes.

Includes regular season and playoffs. Inputs are saved NBA ShotChartDetail
shots and team-filtered LeagueDashPlayerStats totals. League shot data supply
the same-range, same-season, same-phase comparison. No endpoint is called here.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/visuals/2026-09-25-deep-threes-career/data"
FIRST_YEAR = 1996
LAST_YEAR = 2025
MIDCOURT_Y = 417.5  # NBA LOC_Y is in tenths of a foot; hoop to midcourt = 41.75 ft.
PLAYOFF_SEASONS = (
    "1996-97", "1997-98", "2004-05", "2005-06", "2006-07",
    "2008-09", "2009-10", "2010-11", "2011-12", "2012-13",
    "2013-14", "2014-15", "2016-17", "2021-22",
)


def seasons() -> list[str]:
    return [f"{year}-{(year + 1) % 100:02d}" for year in range(FIRST_YEAR, LAST_YEAR + 1)]


def eligible(shots: pd.DataFrame, *, league: bool = False) -> pd.DataFrame:
    """Official threes, 27–39 whole feet, with the shot location before midcourt."""
    shot_type = "3PT" if league else "3PT Field Goal"
    type_col = "shot_type" if league else "SHOT_TYPE"
    distance_col = "shot_distance" if league else "SHOT_DISTANCE"
    y_col = "loc_y" if league else "LOC_Y"
    return shots.loc[
        shots[type_col].eq(shot_type)
        & shots[distance_col].between(27, 39, inclusive="both")
        & shots[y_col].lt(MIDCOURT_Y)
    ].copy()


def league_summary(cache: Path, destination: Path) -> pd.DataFrame:
    rows = []
    for season in seasons():
        path = cache / f"league_{season}.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(
            path, usecols=["shot_type", "shot_distance", "loc_y", "shot_made"]
        )
        picked = eligible(frame, league=True)
        attempts = len(picked)
        if not attempts:
            raise ValueError(f"{season}: no league attempts in selected range")
        rows.append({
            "season": season,
            "league_3pa": attempts,
            "league_3pm": int(picked.shot_made.sum()),
            "source_path": str(path),
            "source_file_modified_utc": datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat(),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError(f"No league shot files found in {cache}")
    out.to_csv(destination, index=False)
    return out


def playoff_league_summary(data_dir: Path) -> pd.DataFrame:
    rows = []
    for season in PLAYOFF_SEASONS:
        path = data_dir / "raw/league-playoff-shots" / f"{season}.csv.gz"
        official_path = data_dir / "raw/league-playoff-team-totals" / f"{season}.csv.gz"
        shots = pd.read_csv(path)
        official = pd.read_csv(official_path)
        threes = shots.loc[shots.SHOT_TYPE.eq("3PT Field Goal")]
        if len(threes) != int(official.FG3A.sum()) or int(threes.SHOT_MADE_FLAG.sum()) != int(official.FG3M.sum()):
            raise ValueError(f"{season}: league playoff shots do not reconcile to official totals")
        selected = eligible(shots)
        rows.append({
            "season": season,
            "official_3pa": int(official.FG3A.sum()),
            "official_3pm": int(official.FG3M.sum()),
            "league_3pa": len(selected),
            "league_3pm": int(selected.SHOT_MADE_FLAG.sum()),
            "source_path": str(path.relative_to(data_dir)),
            "official_source_path": str(official_path.relative_to(data_dir)),
            "source_file_modified_utc": datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat(),
        })
    result = pd.DataFrame(rows)
    if result.league_3pa.eq(0).any():
        raise ValueError("A playoff season has no eligible league attempts")
    result.to_csv(data_dir / "league_27_39_playoffs_by_season.csv", index=False)
    return result


def prepare(data_dir: Path, league_cache: Path | None = None) -> pd.DataFrame:
    data_dir.mkdir(parents=True, exist_ok=True)
    league_path = data_dir / "league_27_39_by_season.csv"
    if league_cache is not None:
        league_summary(league_cache, league_path)
    if not league_path.exists():
        raise FileNotFoundError("Provide --league-cache to create the league snapshot")
    league = pd.read_csv(league_path)
    league["league_rate"] = league.league_3pm / league.league_3pa
    league_rates = league.set_index("season").league_rate.to_dict()
    playoff_league = playoff_league_summary(data_dir)
    playoff_league["league_rate"] = playoff_league.league_3pm / playoff_league.league_3pa
    playoff_rates = playoff_league.set_index("season").league_rate.to_dict()

    player_seasons = []
    audits = []
    sources = []
    for season_type, years, rates in (
        ("Regular Season", seasons(), league_rates),
        ("Playoffs", PLAYOFF_SEASONS, playoff_rates),
    ):
      for season in years:
        if season_type == "Regular Season":
            shot_path = data_dir / "raw/bulls-shots" / f"{season}.csv.gz"
            official_path = data_dir / "raw/bulls-player-totals" / f"{season}.csv.gz"
        else:
            shot_path = data_dir / "raw/league-playoff-shots" / f"{season}.csv.gz"
            official_path = data_dir / "raw/bulls-playoff-totals" / f"{season}.csv.gz"
        all_shots = pd.read_csv(shot_path, dtype={"GAME_ID": str})
        shots = all_shots.loc[all_shots.TEAM_ID.eq(1610612741)].copy()
        official = pd.read_csv(official_path)
        for path, endpoint in (
            (shot_path, "https://stats.nba.com/stats/shotchartdetail"),
            (official_path, "https://stats.nba.com/stats/leaguedashplayerstats"),
        ):
            sources.append({
                "season": season,
                "season_type": season_type,
                "endpoint": endpoint,
                "file": str(path.relative_to(data_dir)),
                "source_file_modified_utc": datetime.fromtimestamp(
                    path.stat().st_mtime, timezone.utc
                ).isoformat(),
            })
        if season_type == "Playoffs":
            team_path = data_dir / "raw/league-playoff-team-totals" / f"{season}.csv.gz"
            sources.append({
                "season": season,
                "season_type": season_type,
                "endpoint": "https://stats.nba.com/stats/leaguedashteamstats",
                "file": str(team_path.relative_to(data_dir)),
                "source_file_modified_utc": datetime.fromtimestamp(
                    team_path.stat().st_mtime, timezone.utc
                ).isoformat(),
            })
        required_shots = {"PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "SHOT_TYPE",
                          "SHOT_DISTANCE", "SHOT_MADE_FLAG", "LOC_Y", "GAME_ID"}
        required_official = {"PLAYER_ID", "GP", "FG3A", "FG3M"}
        if not required_shots <= set(shots) or not required_official <= set(official):
            raise ValueError(f"{season}: source schema is missing required fields")
        if shots.empty:
            raise ValueError(f"{season} {season_type}: no Bulls shot rows")
        threes = shots.loc[shots.SHOT_TYPE.eq("3PT Field Goal")]
        official_3pa = int(official.FG3A.sum())
        official_3pm = int(official.FG3M.sum())
        if len(threes) != official_3pa or int(threes.SHOT_MADE_FLAG.sum()) != official_3pm:
            raise ValueError(f"{season} {season_type}: shot log does not reconcile to official 3PA/3PM")

        selected = eligible(shots)
        counts = selected.groupby("PLAYER_ID", as_index=False).agg(
            deep_3pa=("SHOT_MADE_FLAG", "size"), deep_3pm=("SHOT_MADE_FLAG", "sum")
        )
        names = shots[["PLAYER_ID", "PLAYER_NAME"]].drop_duplicates("PLAYER_ID", keep="last")
        player_year = official[["PLAYER_ID", "GP"]].merge(
            names, on="PLAYER_ID", how="left", validate="one_to_one"
        ).merge(counts, on="PLAYER_ID", how="left", validate="one_to_one")
        player_year[["deep_3pa", "deep_3pm"]] = player_year[["deep_3pa", "deep_3pm"]].fillna(0).astype(int)
        player_year["season"] = season
        player_year["season_type"] = season_type
        player_year["league_rate"] = rates.get(season, float("nan"))
        player_year["expected_makes"] = player_year.deep_3pa * player_year.league_rate
        player_seasons.append(player_year)

        missing_distance = threes.SHOT_DISTANCE.isna()
        frontcourt_40_plus = threes.SHOT_DISTANCE.ge(40) & threes.LOC_Y.lt(MIDCOURT_Y)
        audits.append({
            "season": season,
            "season_type": season_type,
            "shot_rows": len(shots),
            "official_3pa": official_3pa,
            "official_3pm": official_3pm,
            "shot_log_3pa": len(threes),
            "shot_log_3pm": int(threes.SHOT_MADE_FLAG.sum()),
            "missing_distance_3pa": int(missing_distance.sum()),
            "missing_distance_3pm": int(threes.loc[missing_distance, "SHOT_MADE_FLAG"].sum()),
            "eligible_3pa": len(selected),
            "eligible_3pm": int(selected.SHOT_MADE_FLAG.sum()),
            "excluded_40_plus_3pm": int(threes.loc[threes.SHOT_DISTANCE.ge(40), "SHOT_MADE_FLAG"].sum()),
            "excluded_frontcourt_40_plus_3pa": int(frontcourt_40_plus.sum()),
            "excluded_frontcourt_40_plus_3pm": int(threes.loc[frontcourt_40_plus, "SHOT_MADE_FLAG"].sum()),
        })

    player_seasons = pd.concat(player_seasons, ignore_index=True)
    career = player_seasons.groupby("PLAYER_ID", as_index=False).agg(
        gp=("GP", "sum"), deep_3pa=("deep_3pa", "sum"),
        deep_3pm=("deep_3pm", "sum"), expected_makes=("expected_makes", "sum")
    )
    latest_names = player_seasons.drop_duplicates("PLAYER_ID", keep="last")[["PLAYER_ID", "PLAYER_NAME"]]
    career = career.merge(latest_names, on="PLAYER_ID", validate="one_to_one")
    career = career.sort_values(
        ["deep_3pm", "deep_3pa", "PLAYER_NAME"], ascending=[False, False, True]
    ).reset_index(drop=True)
    career["rank"] = career.deep_3pm.rank(method="min", ascending=False).astype(int)
    top = career.head(15).copy()
    selected_years = player_seasons.loc[
        player_seasons.PLAYER_ID.isin(top.PLAYER_ID)
        & player_seasons.deep_3pa.gt(0)
    ]
    if top.expected_makes.isna().any() or selected_years.league_rate.isna().any():
        raise ValueError("A selected player's season is missing its league baseline")
    top["attempts_per_game"] = top.deep_3pa / top.gp
    top["three_pct"] = top.deep_3pm / top.deep_3pa * 100
    top["league_three_pct"] = top.expected_makes / top.deep_3pa * 100
    top["relative_pp"] = top.three_pct - top.league_three_pct
    top = top.rename(columns={"PLAYER_ID": "player_id", "PLAYER_NAME": "player_name"})

    games_path = data_dir / "raw/bulls-playoff-games.csv.gz"
    sources.append({
        "season": "1996-97 to 2025-26",
        "season_type": "Playoffs coverage",
        "endpoint": "https://stats.nba.com/stats/leaguegamefinder",
        "file": str(games_path.relative_to(data_dir)),
        "source_file_modified_utc": datetime.fromtimestamp(
            games_path.stat().st_mtime, timezone.utc
        ).isoformat(),
    })
    pd.DataFrame(audits).to_csv(data_dir / "season_audit.csv", index=False)
    pd.DataFrame(sources).to_csv(data_dir / "source_manifest.csv", index=False)
    player_seasons.to_csv(data_dir / "player_seasons.csv", index=False)
    top.to_csv(data_dir / "top15.csv", index=False)
    (data_dir / "generation.json").write_text(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "definition": "NBA regular-season and playoff Bulls 3PT shots, 27-39 whole feet, LOC_Y < 417.5",
        "player_league_comparison": "same-range league FG% by season and phase, weighted by each player's attempts",
    }, indent=2) + "\n")
    return top


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--league-cache", type=Path)
    args = parser.parse_args()
    top = prepare(args.data_dir, args.league_cache)
    print(top[["rank", "player_name", "deep_3pm", "deep_3pa", "attempts_per_game",
               "three_pct", "league_three_pct", "relative_pp"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
