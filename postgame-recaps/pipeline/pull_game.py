"""Mockup-stage fetch of every NBA.com table the postgame recap mockup uses, for one game.

Run from the repo root with the primary venv:
    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/pull_game.py 0022500248
Writes postgame-recaps/seasons/<season>/<id>/ (stress-tests/<id>/ for test games). Add --league to also refresh the
league-wide 2025-26 team-game tables that the four-factor percentiles and the accounting use.

BoxScoreSummaryV2 is deliberately not used: it returned empty line scores for this game (nba_api
warns it is unreliable after April 2025). Quarter scores come from the play-by-play instead.
Shots are pulled with the season type the game ID encodes (001 preseason, 002 regular season, 004
playoffs); bulls.data.fetch.get_game_shots hardcodes the regular season and returns nothing for preseason.
Endpoints that publish nothing for a game (tracking and matchups can lag or be absent) are saved as
empty tables and reported, never treated as zero.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from nba_api.stats.endpoints import (
    boxscoreadvancedv3, boxscorefourfactorsv3, boxscorematchupsv3, boxscoresummaryv3,
    boxscoremiscv3, boxscoreplayertrackv3, boxscorescoringv3, boxscoretraditionalv3,
    commonteamroster, leaguegamelog, playbyplayv3, scheduleleaguev2, shotchartdetail, teamgamelogs,
)

import pandas as pd
import requests

from bulls.data.fetch import _NBA_HEADERS, get_player_headshot

BULLS = int(os.environ.get("FOCUS_TEAM_ID", 1610612741))  # the featured team
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import BASELINES, LOGOS, PORTRAITS, game_dir  # noqa: E402


SEASON_TYPES = {"001": "Pre Season", "002": "Regular Season", "004": "Playoffs", "005": "PlayIn"}


def pause():
    time.sleep(1)


def season_of(game_id: str) -> str:
    start = 2000 + int(game_id[3:5])
    return f"{start}-{str(start + 1)[-2:]}"


# Feeds the published slides draw on. While any is missing the pull exits NOT_READY and postgame_recap.py pulls
# again; the rest (advanced, scoring, matchups, tracking, opponent shots) feed back-pocket pages only.
REQUIRED = {"summary_game.csv": "summary", "summary_info.csv": "summary", "summary_arena.csv": "summary (arena)",
            "summary_linescore.csv": "line score", "summary_stats.csv": "summary (game flow counts)",
            "players.csv": "box score", "teams.csv": "box score", "ff_team.csv": "four factors",
            "pbp.csv": "play-by-play", "misc_teams.csv": "misc (head-to-head)", "shots_raw_chi.csv": "Bulls shots",
            "roster.csv": "roster", "player_games.csv": "player game log",
            "league_games.csv": "league game log", "schedule.csv": "schedule"}
NOT_READY = 75


def box(cls, game_id: str, index: int) -> pd.DataFrame:
    """One table of a V3 box score, asked for first exactly as NBA.com's own game page asks, then with nba_api's
    defaults. stats.nba.com caches each exact request separately; on 2026-10-07 the website's request
    (LeagueID=00, EndRange=28800) had four factors, advanced and misc filled 2 to 5 minutes before nba_api's."""
    for website in (True, False):
        try:
            e = cls(game_id=game_id, headers=_NBA_HEADERS, timeout=60, get_request=False)
            if website:
                # RangeType 0 makes NBA.com ignore StartRange/EndRange, so overtime is never cut off (2OT checked
                # Oct 8); RangeType 2 with this EndRange returns regulation only. Set it explicitly to keep it so.
                e.parameters.update({"LeagueID": "00", "EndRange": "28800", "RangeType": "0"})
            e.get_request()
            frame = e.get_data_frames()[index]
            if not frame.empty:
                return frame
        except Exception:  # an unpublished feed comes back without its tables; try the other request
            pass
    return pd.DataFrame()


# What each saved file is, for sources.json (the capture record: which NBA.com request, when, how many rows).
ENDPOINTS = {
    "players.csv": "boxscoretraditionalv3, players", "teams.csv": "boxscoretraditionalv3, team totals",
    "ff_team.csv": "boxscorefourfactorsv3, teams", "pbp.csv": "playbyplayv3",
    "advanced_players.csv": "boxscoreadvancedv3, players", "misc_teams.csv": "boxscoremiscv3, teams",
    "matchups.csv": "boxscorematchupsv3", "track_players.csv": "boxscoreplayertrackv3, players",
    "track_teams.csv": "boxscoreplayertrackv3, teams", "scoring_players.csv": "boxscorescoringv3, players",
    "scoring_teams.csv": "boxscorescoringv3, teams", "roster.csv": "commonteamroster, Bulls",
    "shots_raw_chi.csv": "shotchartdetail, featured team, every field-goal attempt",
    "shots_raw_opp.csv": "shotchartdetail, opponent, every field-goal attempt",
    "player_games.csv": "leaguegamelog P, this season type", "league_games.csv": "leaguegamelog T, this season type",
    "schedule.csv": "scheduleleaguev2, Bulls games",
    **{f"{name}.csv": f"boxscoresummaryv3, table {i}" for i, name in {
        0: "summary_game", 1: "summary_info", 2: "summary_arena", 4: "summary_linescore", 7: "summary_stats",
        8: "summary_availability"}.items()},
}
CAPTURED = {}


def record(path: Path, frame: pd.DataFrame) -> None:
    CAPTURED[path.name] = {"source": ENDPOINTS.get(path.name, "derived"), "rows": len(frame),
                           "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def save(frame_fn, path: Path, missing: list) -> None:
    """Save one table; an endpoint that errors or returns no rows is recorded, not zero-filled."""
    try:
        frame = frame_fn()
    except Exception as exc:  # an unpublished feed comes back without its tables (nba_api raises)
        frame = pd.DataFrame()
        missing.append(f"{path.name}: not published ({type(exc).__name__})")
    if frame.empty and not any(m.startswith(path.name) for m in missing):
        missing.append(f"{path.name}: not published (no rows)")
    frame.to_csv(path, index=False)
    record(path, frame)
    pause()


def shot_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """The columns the zones chart expects, from raw ShotChartDetail rows."""
    if raw.empty:
        return pd.DataFrame()
    return pd.DataFrame({
        "loc_x": raw.LOC_X, "loc_y": raw.LOC_Y, "shot_made": raw.SHOT_MADE_FLAG == 1,
        "shot_type": raw.SHOT_TYPE.map(lambda x: "3PT" if "3PT" in str(x) else "2PT"),
        "shot_zone": raw.SHOT_ZONE_BASIC, "shot_distance": raw.SHOT_DISTANCE, "game_id": raw.GAME_ID,
        "player_id": raw.PLAYER_ID, "player_name": raw.PLAYER_NAME, "shot_zone_area": raw.SHOT_ZONE_AREA,
    })


SUMMARY_TABLES = {0: "summary_game", 1: "summary_info", 2: "summary_arena", 4: "summary_linescore",
                  7: "summary_stats", 8: "summary_availability"}


def pull_summary(game_id: str, out: Path, missing: list) -> None:
    """Date, arena, records, quarter scores, NBA's own lead/run counts, and feed-availability flags."""
    frames = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, headers=_NBA_HEADERS, timeout=60).get_data_frames()
    for index, name in SUMMARY_TABLES.items():
        save(lambda index=index: frames[index], out / f"{name}.csv", missing)


def pull_player_games(season: str, season_type: str, out: Path, missing: list) -> None:
    """Game logs of Bulls players, for season leaders and notables (preseason and regular season are separate);
    recap_data.py keeps games on or before the recap's date. PlayerGameLogs drops preseason, LeagueGameLog does not."""
    def frame():
        f = leaguegamelog.LeagueGameLog(season=season, season_type_all_star=season_type,
                                        player_or_team_abbreviation="P", headers=_NBA_HEADERS, timeout=90).get_data_frames()[0]
        # Every game of anyone who played for the Bulls, on any team, so "season high" counts games before a trade.
        return f[f.PLAYER_ID.isin(f.loc[f.TEAM_ID == BULLS, "PLAYER_ID"])]
    save(frame, out / "player_games.csv", missing)


def pull_league_games(season: str, season_type: str, out: Path, missing: list) -> None:
    """Every team's games of this season type, for the Bulls' place in the East after each game."""
    save(lambda: leaguegamelog.LeagueGameLog(season=season, season_type_all_star=season_type,
                                             player_or_team_abbreviation="T", headers=_NBA_HEADERS, timeout=90
                                             ).get_data_frames()[0], out / "league_games.csv", missing)


def pull_schedule(season: str, out: Path, missing: list) -> None:
    """The Bulls' scheduled games, so a season page can show the games still to play."""
    def frame():
        f = scheduleleaguev2.ScheduleLeagueV2(season=season, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
        return f[(f.homeTeam_teamId == BULLS) | (f.awayTeam_teamId == BULLS)][["gameId", "gameDate", "homeTeam_teamTricode", "awayTeam_teamTricode"]]
    save(frame, out / "schedule.csv", missing)


def pull_logos(teams: pd.DataFrame, missing: list) -> None:
    """Both teams' primary logos (SVG) from NBA.com's CDN, cached by tricode in logos/."""
    folder = LOGOS
    folder.mkdir(exist_ok=True)
    for r in teams.itertuples():
        path = folder / f"{r.teamTricode}.svg"
        if path.exists():
            continue
        response = requests.get(f"https://cdn.nba.com/logos/nba/{int(r.teamId)}/primary/L/logo.svg", timeout=30)
        if response.ok and response.text.lstrip().startswith("<"):
            path.write_text(response.text)
        else:
            missing.append(f"logo {r.teamTricode}")


def pull_game(game_id: str) -> list:
    out = game_dir(game_id)
    out.mkdir(parents=True, exist_ok=True)
    kw = dict(game_id=game_id, headers=_NBA_HEADERS, timeout=60)

    season, season_type, missing = season_of(game_id), SEASON_TYPES[game_id[:3]], []
    players, teams = box(boxscoretraditionalv3.BoxScoreTraditionalV3, game_id, 0), box(boxscoretraditionalv3.BoxScoreTraditionalV3, game_id, 2)
    pause()
    if teams.empty or players.empty:  # nothing else can be pulled without the box score
        (out / "missing.txt").write_text("teams.csv: not published\nplayers.csv: not published\n")
        return ["box score"]
    pull_summary(game_id, out, missing)
    pull_logos(teams, missing)
    players.to_csv(out / "players.csv", index=False)
    teams.to_csv(out / "teams.csv", index=False)
    record(out / "players.csv", players)
    record(out / "teams.csv", teams)
    save(lambda: box(boxscorefourfactorsv3.BoxScoreFourFactorsV3, game_id, 1), out / "ff_team.csv", missing)
    save(lambda: playbyplayv3.PlayByPlayV3(**kw).get_data_frames()[0], out / "pbp.csv", missing)
    save(lambda: box(boxscoreadvancedv3.BoxScoreAdvancedV3, game_id, 0), out / "advanced_players.csv", missing)
    save(lambda: box(boxscoremiscv3.BoxScoreMiscV3, game_id, 1), out / "misc_teams.csv", missing)
    save(lambda: box(boxscorematchupsv3.BoxScoreMatchupsV3, game_id, 0), out / "matchups.csv", missing)
    save(lambda: box(boxscoreplayertrackv3.BoxScorePlayerTrackV3, game_id, 0), out / "track_players.csv", missing)
    save(lambda: box(boxscoreplayertrackv3.BoxScorePlayerTrackV3, game_id, 1), out / "track_teams.csv", missing)
    save(lambda: box(boxscorescoringv3.BoxScoreScoringV3, game_id, 0), out / "scoring_players.csv", missing)
    save(lambda: box(boxscorescoringv3.BoxScoreScoringV3, game_id, 1), out / "scoring_teams.csv", missing)

    opponent = int(teams.loc[teams.teamId != BULLS, "teamId"].iloc[0])
    # Raw rows keep ACTION_TYPE, which the shot-type strip classifies with bulls.analysis.shot_families.
    for team, name in ((BULLS, "chi"), (opponent, "opp")):
        save(lambda team=team: shotchartdetail.ShotChartDetail(
            team_id=team, player_id=0, game_id_nullable=game_id, season_nullable=season,
            season_type_all_star=season_type, context_measure_simple="FGA", headers=_NBA_HEADERS, timeout=60,
        ).get_data_frames()[0], out / f"shots_raw_{name}.csv", missing)
        shot_rows(pd.read_csv(out / f"shots_raw_{name}.csv") if (out / f"shots_raw_{name}.csv").stat().st_size > 1 else pd.DataFrame()
                  ).to_csv(out / f"shots_{name}.csv", index=False)
    save(lambda: commonteamroster.CommonTeamRoster(team_id=BULLS, season=season, headers=_NBA_HEADERS,
                                                   timeout=60).get_data_frames()[0], out / "roster.csv", missing)
    pull_player_games(season, season_type, out, missing)
    pull_schedule(season, out, missing)
    pull_league_games(season, season_type, out, missing)
    # Headshots for every Bulls player and for the opponent's players who played (game leaders).
    played = players[(players.teamId == BULLS) | players.minutes.fillna("").astype(str).str.contains(":")]
    for pid in played.personId:
        if get_player_headshot(int(pid), cache_dir=str(PORTRAITS)) is None:
            missing.append(f"portrait {pid}")
    (out / "missing.txt").write_text("\n".join(missing) + ("\n" if missing else ""))
    (out / "sources.json").write_text(json.dumps({
        "game_id": game_id, "season": season, "season_type": season_type,
        "requests": "https://stats.nba.com/stats/<endpoint> through nba_api; box score V3 calls first with the "
                    "NBA.com website's parameters (LeagueID=00, EndRange=28800, RangeType=0), then nba_api's defaults",
        "files": dict(sorted(CAPTURED.items()))}, indent=1) + "\n")
    if missing:
        print("missing or empty:", "; ".join(missing))
    # The required feeds still missing, by plain name, for postgame_recap.py's log.
    return sorted({REQUIRED[m.split(":")[0]] for m in missing if m.split(":")[0] in REQUIRED})


def pull_league(season: str = "2025-26") -> Path:
    out = BASELINES / f"league-{season}"
    out.mkdir(parents=True, exist_ok=True)
    leaguegamelog.LeagueGameLog(season=season, season_type_all_star="Regular Season",
                                player_or_team_abbreviation="T", headers=_NBA_HEADERS, timeout=90
                                ).get_data_frames()[0].to_csv(out / f"league_teamgames_{season}.csv.gz", index=False); pause()
    for measure, name in (("Four Factors", "four_factors"), ("Advanced", "advanced")):
        teamgamelogs.TeamGameLogs(season_nullable=season, season_type_nullable="Regular Season",
                                  measure_type_player_game_logs_nullable=measure, headers=_NBA_HEADERS, timeout=90
                                  ).get_data_frames()[0].to_csv(out / f"league_{name}_{season}.csv.gz", index=False); pause()
    return out


if __name__ == "__main__":
    if "--league" in sys.argv:
        print("wrote", pull_league())
    try:
        waiting = pull_game(sys.argv[1])
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:  # a timeout or reset is not a failure
        waiting = [f"NBA.com did not answer ({type(e).__name__})"]
    if waiting:
        print("not published yet:", ", ".join(waiting), flush=True)
        sys.exit(NOT_READY)
    print("pulled", sys.argv[1])
