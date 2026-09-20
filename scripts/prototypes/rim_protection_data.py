"""Prepare rim-protection player seasons from NBA tracking, 2013-14 onward.

Rim defense is NBA.com's "Defense" tracking measure: shots within six feet of
the rim while the player was within five feet of the shooter and the rim.
League-wide player rows form the qualified background; Chicago rows are
reconciled against the Bulls team total before any Bulls season is labelled.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashptstats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bulls.data.fetch import _NBA_HEADERS

DATA = ROOT / "docs/visuals/2026-09-18-rim-protection-landscape/data"
BULLS = 1610612741
SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(2013, 2026)]


def fetch(kind: str, season: str, refresh: bool = False) -> pd.DataFrame:
    """kind: players (league-wide), bulls (TeamID-filtered players), teams."""
    path = DATA / "raw" / f"{kind}_{season}.json"
    if refresh or not path.exists():
        params = dict(
            season=season,
            season_type_all_star="Regular Season",
            player_or_team="Team" if kind == "teams" else "Player",
            pt_measure_type="Defense",
            per_mode_simple="Totals",
            team_id_nullable=str(BULLS) if kind == "bulls" else "",
        )
        response = leaguedashptstats.LeagueDashPtStats(
            **params, headers=_NBA_HEADERS, timeout=60
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "endpoint": "LeagueDashPtStats",
            "parameters": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response": response.get_dict(),
        }, ensure_ascii=False))
        time.sleep(.6)
    result = json.loads(path.read_text())["response"]["resultSets"][0]
    frame = pd.DataFrame(result["rowSet"], columns=result["headers"])
    if frame.empty:
        raise ValueError(f"Missing {kind} rim-defense data for {season}")
    return frame


# Per-100 view (Tipoff's rim-protection method): a season qualifies with 1,500+
# minutes and a top-30 rim-attempt volume among that season's 1,500-minute
# players (stricter than Tipoff's top 50). Chicago seasons meet the same bar on
# Chicago minutes. Featured faces are those that saved more than one rim point
# per 100 possessions; the qualified Chicago list breaks cleanly there (1.41,
# then 0.40). Raising the minutes floor instead would loosen the volume cut,
# because fewer players compete for the same top-N places.
MIN_MINUTES = 1500
VOLUME_RANK = 30
FEATURE_SAVED_PER_100 = 1.0

# Top-15 table: Chicago seasons by total rim points saved. The minutes floor
# keeps out short-sample rates (Tony Bradley 2021-22 ranks 8th on 550 minutes
# without it). No tie at the cut: 15th is 19.4, 16th is 16.3.
TABLE_MIN_MINUTES = 1000
TABLE_ROWS = 15
# NBA.com's full-season 2024-25 aggregate disagrees with its own game-level
# data for every team (65,169 vs 55,537 league rim FGA). Month and half-season
# splits reconcile to each other and to the 2025-26 definition, so 2024-25 is
# rebuilt from two date-bounded halves. Every other season matches exactly.
SPLIT_SEASONS = {"2024-25": ("12/31/2024", "01/01/2025")}
COUNT_COLUMNS = ["GP", "MIN", "STL", "BLK", "DREB", "DEF_RIM_FGM", "DEF_RIM_FGA"]


def fetch_half(kind: str, season: str, half: str, refresh: bool = False) -> pd.DataFrame:
    path = DATA / "raw" / f"{kind}_{season}_{half}.json"
    if refresh or not path.exists():
        before, after = SPLIT_SEASONS[season]
        params = dict(
            season=season,
            season_type_all_star="Regular Season",
            player_or_team="Team" if kind == "teams" else "Player",
            pt_measure_type="Defense",
            per_mode_simple="Totals",
            team_id_nullable=str(BULLS) if kind == "bulls" else "",
            **({"date_to_nullable": before} if half == "h1" else {"date_from_nullable": after}),
        )
        response = leaguedashptstats.LeagueDashPtStats(**params, headers=_NBA_HEADERS, timeout=60)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "endpoint": "LeagueDashPtStats",
            "parameters": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response": response.get_dict(),
        }, ensure_ascii=False))
        time.sleep(.6)
    result = json.loads(path.read_text())["response"]["resultSets"][0]
    return pd.DataFrame(result["rowSet"], columns=result["headers"])


def season_rows(kind: str, season: str, refresh: bool = False) -> pd.DataFrame:
    """Season totals per player (or team), game-level where the aggregate is broken."""
    if season not in SPLIT_SEASONS:
        return fetch(kind, season, refresh)
    key = "TEAM_ID" if kind == "teams" else "PLAYER_ID"
    halves = pd.concat([fetch_half(kind, season, h, refresh) for h in ("h1", "h2")])
    names = halves.groupby(key)[["TEAM_ID" if kind != "teams" else "TEAM_ABBREVIATION"]].last()
    label = "PLAYER_NAME" if kind != "teams" else "TEAM_NAME"
    totals = halves.groupby(key)[COUNT_COLUMNS].sum()
    out = totals.join(halves.groupby(key)[label].last()).join(names).reset_index()
    return out


def add_measures(frame: pd.DataFrame, season: str, league_pct: float) -> pd.DataFrame:
    out = pd.DataFrame({
        "season": season,
        "player_id": frame.PLAYER_ID.astype(int),
        "player_name": frame.PLAYER_NAME.replace({"Jimmy Butler III": "Jimmy Butler"}),
        "team_id": frame.TEAM_ID.astype(int),
        "gp": frame.GP.astype(int),
        "rim_fgm": frame.DEF_RIM_FGM.astype(int),
        "rim_fga": frame.DEF_RIM_FGA.astype(int),
        "blocks": frame.BLK.astype(int),
    })
    out["rim_fga_per_game"] = out.rim_fga / out.gp
    out["rim_fg_pct"] = 100 * out.rim_fgm / out.rim_fga
    out["league_rim_fg_pct"] = 100 * league_pct
    out["pct_vs_league"] = out.rim_fg_pct - out.league_rim_fg_pct
    # Makes a league-average rim defender would have allowed on the same
    # attempts, minus the makes this player actually allowed.
    out["rim_makes_saved"] = out.rim_fga * league_pct - out.rim_fgm
    return out


def fetch_possessions(kind: str, season: str, refresh: bool = False) -> pd.DataFrame:
    """Chicago-only (kind='adv_bulls') or league-wide possessions and minutes."""
    path = DATA / "raw" / f"{kind}_{season}.json"
    if refresh or not path.exists():
        params = dict(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="Totals",
            team_id_nullable=str(BULLS) if kind == "adv_bulls" else "",
        )
        response = leaguedashplayerstats.LeagueDashPlayerStats(**params, headers=_NBA_HEADERS, timeout=60)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "endpoint": "LeagueDashPlayerStats",
            "parameters": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response": response.get_dict(),
        }, ensure_ascii=False))
        time.sleep(.6)
    result = json.loads(path.read_text())["response"]["resultSets"][0]
    frame = pd.DataFrame(result["rowSet"], columns=result["headers"])
    # The Advanced frame reports MIN per game even under Totals.
    return pd.DataFrame({
        "season": season,
        "player_id": frame.PLAYER_ID.astype(int),
        "minutes": frame.MIN * frame.GP,
        "possessions": frame.POSS.astype(int),
    })


def per_100(frame: pd.DataFrame, possessions: pd.DataFrame) -> pd.DataFrame:
    out = frame.merge(possessions, on=["season", "player_id"], how="left", validate="one_to_one")
    if out.possessions.isna().any():
        raise ValueError("Rim-defense rows without possessions")
    out["rim_fga_per_100"] = 100 * out.rim_fga / out.possessions
    out["rim_points_saved"] = 2 * out.rim_makes_saved
    out["rim_points_saved_per_100"] = 100 * out.rim_points_saved / out.possessions
    return out


def per_100_views(league: pd.DataFrame, bulls: pd.DataFrame, refresh: bool = False):
    league = per_100(league, pd.concat([fetch_possessions("adv_players", s, refresh) for s in SEASONS]))
    bulls = per_100(bulls, pd.concat([fetch_possessions("adv_bulls", s, refresh) for s in SEASONS]))
    eligible = league.loc[league.minutes >= MIN_MINUTES].copy()
    eligible["volume_rank"] = eligible.groupby("season").rim_fga.rank(ascending=False, method="min")
    background = eligible.loc[eligible.volume_rank <= VOLUME_RANK].copy()
    cut = background.groupby("season").rim_fga.min().rename("season_volume_cut")
    bulls = bulls.join(cut, on="season")
    bulls["qualified_per_100"] = (bulls.minutes >= MIN_MINUTES) & (bulls.rim_fga >= bulls.season_volume_cut)
    qualified = bulls.loc[bulls.qualified_per_100].sort_values(
        ["rim_points_saved_per_100", "rim_fga", "season"], ascending=[False, False, True], kind="stable",
    ).copy()
    qualified.insert(0, "rank", range(1, len(qualified) + 1))
    qualified["featured"] = qualified.rim_points_saved_per_100 > FEATURE_SAVED_PER_100
    featured = set(zip(qualified.loc[qualified.featured, "season"], qualified.loc[qualified.featured, "player_id"]))
    background["featured"] = [(s, p) in featured for s, p in zip(background.season, background.player_id)]
    # The all-defender average matches the y-axis zero, which is also measured
    # against every defender. Possession-weighted and pooled across seasons.
    league_avg = 100 * league.rim_fga.sum() / league.possessions.sum()
    return background, qualified, league_avg


def nba_rank(value: float, season: str, player_id: int, league: pd.DataFrame) -> int:
    """Rank a Chicago season among every NBA player in that same season.

    Ranking within the season keeps the comparison era-fair and reads the way
    the and-1 table's NBA RANK column does. The player's own league row is
    excluded: for a traded player it covers both teams, so it would otherwise
    outrank his Chicago stint.
    """
    others = league.loc[(league.season == season) & (league.player_id != player_id)]
    return int((others.rim_points_saved > value).sum()) + 1


def table_rows(bulls: pd.DataFrame, league: pd.DataFrame) -> pd.DataFrame:
    pool = bulls.loc[bulls.minutes >= TABLE_MIN_MINUTES].sort_values(
        ["rim_points_saved", "rim_fga", "season"], ascending=[False, False, True], kind="stable",
    )
    top = pool.head(TABLE_ROWS).copy()
    if len(pool) > TABLE_ROWS and pool.rim_points_saved.iloc[TABLE_ROWS - 1] == pool.rim_points_saved.iloc[TABLE_ROWS]:
        raise ValueError("Tie at the table cut; state a tiebreak before publishing")
    top.insert(0, "rank", range(1, len(top) + 1))
    top["nba_rank"] = [
        nba_rank(r.rim_points_saved, r.season, r.player_id, league) for r in top.itertuples()
    ]
    return top


def main(refresh: bool = False) -> None:
    league_rows, bulls_rows, audits = [], [], []
    for season in SEASONS:
        players, bulls, teams = (season_rows(k, season, refresh) for k in ("players", "bulls", "teams"))
        league_fgm, league_fga = players.DEF_RIM_FGM.sum(), players.DEF_RIM_FGA.sum()
        if league_fga != teams.DEF_RIM_FGA.sum() or league_fgm != teams.DEF_RIM_FGM.sum():
            raise ValueError(f"{season}: league player rows do not sum to team rows")
        team = teams.loc[teams.TEAM_ID == BULLS].iloc[0]
        if bulls.DEF_RIM_FGA.sum() != team.DEF_RIM_FGA or bulls.DEF_RIM_FGM.sum() != team.DEF_RIM_FGM:
            raise ValueError(f"{season}: Chicago player rows do not reconcile to the team total")
        if bulls.PLAYER_ID.duplicated().any():
            raise ValueError(f"{season}: duplicate Chicago player rows")
        league_pct = league_fgm / league_fga
        league_rows.append(add_measures(players, season, league_pct))
        bulls_rows.append(add_measures(bulls, season, league_pct))
        full = fetch("teams", season, refresh)
        audits.append({
            "season": season,
            "source_path": "date halves" if season in SPLIT_SEASONS else "full season",
            "league_rim_fga": int(league_fga),
            "league_rim_fg_pct": round(100 * league_pct, 2),
            "full_season_aggregate_rim_fga": int(full.DEF_RIM_FGA.sum()),
            "chicago_team_rim_fga": int(team.DEF_RIM_FGA),
            "chicago_player_sum_rim_fga": int(bulls.DEF_RIM_FGA.sum()),
            "chicago_rows": len(bulls),
            "chicago_rows_labelled_other_team": int((bulls.TEAM_ID != BULLS).sum()),
        })
        print(audits[-1], flush=True)

    league = pd.concat(league_rows, ignore_index=True)
    bulls = pd.concat(bulls_rows, ignore_index=True)
    background_100, bulls_100, league_avg_100 = per_100_views(league, bulls, refresh)
    (DATA / "chart_reference.json").write_text(json.dumps({
        "league_rim_fga_per_100_all_defenders": round(league_avg_100, 4),
        "definition": "Pooled 2013-14 to 2025-26 rim FGA defended / player possessions x 100, every defender",
    }, indent=2))
    outputs = {
        "top15_table": table_rows(per_100(bulls, pd.concat(
            [fetch_possessions("adv_bulls", season, refresh) for season in SEASONS])),
            per_100(league, pd.concat(
                [fetch_possessions("adv_players", season, refresh) for season in SEASONS]))),
        "league_background_per100": background_100,
        "bulls_qualified_per100": bulls_100,
        "league_player_seasons": league,
        "bulls_player_seasons": bulls,
        "season_audit": pd.DataFrame(audits),
    }
    for name, frame in outputs.items():
        frame.round(4).to_csv(DATA / f"{name}.csv", index=False)
    (DATA / "source.json").write_text(json.dumps({
        "endpoint": "LeagueDashPtStats",
        "measure": "Defense (DEF_RIM_FGM, DEF_RIM_FGA)",
        "definition": "Opponent shots within 6 feet of the rim while the player was within 5 feet of the shooter and the rim.",
        "league_source": "league-wide player response",
        "chicago_source": "TeamID 1610612741 filtered player response; reconciles to the Chicago team row every season",
        "season_type": "Regular Season",
        "seasons": SEASONS,
        "qualifier_per_100": f"{MIN_MINUTES}+ minutes and top {VOLUME_RANK} in rim FGA defended among that season's {MIN_MINUTES}-minute players; Chicago seasons use Chicago minutes against the same season cut",
        "nba_rank": "Rank of that Chicago season's rim points saved among every NBA player in the same season; the player's own league row is excluded because a traded player's league row covers both teams",
        "selection_table": f"Top {TABLE_ROWS} Chicago seasons by total rim points saved, {TABLE_MIN_MINUTES}+ Chicago minutes",
        "selection_per_100": f"Qualified Chicago seasons saving more than {FEATURE_SAVED_PER_100} rim point per 100 possessions; rim points saved = 2 x (rim FGA x league rim FG% minus rim FGM allowed)",
        "possessions_source": "LeagueDashPlayerStats Advanced POSS (league-wide and TeamID-filtered)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "2024-25 full-season aggregates are inflated about 17% league-wide against NBA.com's own game-level data; 2024-25 is rebuilt from two date-bounded halves.",
            "Defended attempts relative to league restricted-area FGA drift from about 0.87 (2013-19) to 1.05 (2023-24) and 0.91 (2024-26), so raw per-game volume is not strictly comparable across eras. FG% is compared to each season's own league average.",
            "Credit goes to the closest defender, not necessarily the one who altered the shot.",
            "Traded players' league-wide rows combine all teams; Chicago rows cover Chicago games only.",
        ],
    }, indent=2))
    pd.set_option("display.width", 200)
    print(bulls_100[["rank", "season", "player_name", "minutes", "rim_fga", "rim_fga_per_100",
                     "pct_vs_league", "rim_points_saved_per_100", "featured"]].round(2).to_string(index=False))
    print("per-100 background:", len(background_100), "| featured matched:", int(background_100.featured.sum()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    main(parser.parse_args().refresh)
