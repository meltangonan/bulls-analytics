"""Prepare Bulls single-season and-1 leaders, 1996-97 through 2025-26.

An and-1 here is a made Chicago field goal plus a one-shot free-throw trip by the same
player at the same game clock, with an opponent foul at that moment. NBA.com publishes no
season and-1 count, so the counts are made here from its play-by-play (`PlayByPlayV3`),
the feed both public and-1 columns are derived from. Play-by-play begins in 1996-97;
earlier seasons return empty responses, which is what sets the window.

Counting here rather than taking a provider's column is deliberate. Against these same
logs, Basketball Reference agreed on 59 of 61 early Chicago player-seasons while pbpstats
missed 19 and-1s across 1996-97 to 1998-99, including five of Michael Jordan's in 1996-97.
Both remain audit columns. pbpstats supplies on-court offensive possessions; Basketball
Reference's complete league table supplies NBA rank, which a Chicago-only count cannot.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = Path("/Users/meltangonan/projects/bulls-analytics")
sys.path.insert(0, str(PRIMARY))
DATA = ROOT / "docs/visuals/2026-09-16-and-one-leaders/data"
# Raw logs are ~200 KB a game; the tracked artefact is the per-game count table.
PBP_CACHE = PRIMARY / "cache/nba.com/and-one-pbp"
PBPSTATS_URL = ("https://api.pbpstats.com/get-totals/nba?Season={season}"
                "&SeasonType=Regular%20Season&Type=Player{team}")
BBR_LEAGUE_URL = "https://www.basketball-reference.com/leagues/NBA_{year}_play-by-play.html"
BULLS = 1610612741
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(1996, 2026)]
TOP_N = 15
TWO, THREE = "2pt And 1 Free Throw Trips", "3pt And 1 Free Throw Trips"
# A one-shot trip after a made basket. "Free Throw Technical" and "1 of 2" are not and-1s;
# the flagrant form is the same play with the foul upgraded on review.
AND_ONE_FREE_THROWS = ("Free Throw 1 of 1", "Free Throw Flagrant 1 of 1")
# The NBA name file carries a suffix this player does not use publicly or on our pages.
DISPLAY_NAMES = {202710: "Jimmy Butler"}


def season_games(season: str) -> list[str]:
    from nba_api.stats.endpoints import leaguegamefinder
    from bulls.data.fetch import _NBA_HEADERS

    games = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=BULLS, season_nullable=season, season_type_nullable="Regular Season",
        headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
    return sorted(games["GAME_ID"].unique())


def game_log(game_id: str, season: str) -> pd.DataFrame:
    from nba_api.stats.endpoints import playbyplayv3
    from bulls.data.fetch import _NBA_HEADERS

    path = PBP_CACHE / f"{season}_{game_id}.json"
    if not path.exists():
        frame = playbyplayv3.PlayByPlayV3(game_id=game_id, headers=_NBA_HEADERS,
                                          timeout=60).get_data_frames()[0]
        if not len(frame):
            raise ValueError(f"{season} {game_id}: empty play-by-play")
        PBP_CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(frame.to_json(orient="records"))
        time.sleep(0.7)
    return pd.DataFrame(json.loads(path.read_text()))


def count_game(frame: pd.DataFrame) -> list[dict]:
    """One row per Chicago player with at least one and-1 in this game."""
    bulls = frame[frame["teamId"] == BULLS]
    made = bulls[(bulls["isFieldGoal"] == 1) & (bulls["shotResult"] == "Made")]
    shots = {(row.personId, row.period, row.clock): row for row in made.itertuples()}
    rows: dict[int, dict] = {}
    for trip in bulls[bulls["subType"].isin(AND_ONE_FREE_THROWS)].itertuples():
        shot = shots.get((trip.personId, trip.period, trip.clock))
        if shot is None:
            continue  # a lone one-shot trip: away-from-play, or a foul on a miss
        moment = frame[(frame["period"] == trip.period) & (frame["clock"] == trip.clock)]
        if not len(moment[(moment["actionType"] == "Foul") & (moment["teamId"] != BULLS)]):
            continue  # no opponent foul at this moment, so not a foul on the shot
        row = rows.setdefault(int(trip.personId), dict(
            player_id=int(trip.personId), player_name=trip.playerName,
            and1s=0, and1s_3pt=0, and1s_flagrant=0, and1s_made_ft=0))
        row["and1s"] += 1
        row["and1s_3pt"] += int(shot.shotValue == 3)
        row["and1s_flagrant"] += int("Flagrant" in str(trip.subType))
        row["and1s_made_ft"] += int(not str(trip.description).startswith("MISS"))
    return list(rows.values())


def own_counts(refresh: bool) -> pd.DataFrame:
    """Count every Chicago and-1 from the game logs, keeping the per-game table."""
    path = DATA / "and_ones_by_game.csv"
    if path.exists() and not refresh:
        saved = pd.read_csv(path)
        if set(saved["season"]) == set(SEASONS):
            return saved
    records, counted = [], {}
    for season in SEASONS:
        ids = season_games(season)
        for game_id in ids:
            for row in count_game(game_log(game_id, season)):
                records.append(dict(season=season, game_id=game_id, **row))
        counted[season] = len(ids)
        print(f"{season}: {len(ids)} games counted")
    out = pd.DataFrame(records)
    out.attrs["games"] = counted
    out.to_csv(path, index=False)
    pd.DataFrame(sorted(counted.items()), columns=["season", "games"]).to_csv(
        DATA / "games_counted.csv", index=False)
    return out


def pbpstats_rows(scope: str, season: str, refresh: bool) -> list[dict]:
    path = DATA / "raw" / f"pbpstats_{scope}_{season}.json"
    if refresh or not path.exists():
        url = PBPSTATS_URL.format(season=season, team=f"&TeamId={BULLS}" if scope == "chi" else "")
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=180) as response:
                    payload = json.loads(response.read())
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(15)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(url=url, retrieved_utc=datetime.now(timezone.utc)
                                        .isoformat(timespec="seconds"), response=payload)))
        time.sleep(2.0)
    return json.loads(path.read_text())["response"]["multi_row_table_data"]


def pbpstats_frame(refresh: bool) -> pd.DataFrame:
    """Chicago on-court offensive possessions, plus pbpstats' own and-1 column."""
    records = []
    for season in SEASONS:
        rows = pbpstats_rows("chi", season, refresh)
        if not rows:
            raise ValueError(f"pbpstats returned no Chicago rows for {season}")
        for r in rows:
            records.append(dict(season=season, player_id=int(r["EntityId"]),
                                games=r["GamesPlayed"], off_poss=r.get("OffPoss"),
                                pbpstats_and1s=(r.get(TWO) or 0) + (r.get(THREE) or 0)))
    out = pd.DataFrame(records)
    if out.duplicated(["season", "player_id"]).any():
        raise ValueError("Duplicate pbpstats player rows within a season")
    return out


def bbr_league_rows(refresh: bool) -> pd.DataFrame:
    """Basketball Reference's play-by-play and-1 column: NBA rank plus an audit.

    Cells are read by `data-stat` name, so a column reorder cannot shift values. Saved
    seasons are reused because Basketball Reference rate-limits scrapers.
    """
    path = DATA / "bbr_league_player_rows.csv"
    saved = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["season_end"])
    years = [int(season[:4]) + 1 for season in SEASONS]
    missing = [y for y in years if refresh or y not in set(saved["season_end"])]
    if not missing:
        return saved
    records = []
    for year in missing:
        url = BBR_LEAGUE_URL.format(year=year)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=180) as response:
            page = response.read().decode("utf-8", "replace")
        time.sleep(3.5)
        block = re.search(r'id="(?:all_)?pbp_stats".*?(<table.*?</table>)', page, re.S)
        if not block:
            raise ValueError(f"No Basketball Reference play-by-play table for {year}")
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", block.group(1), re.S):
            if 'scope="col"' in row_html:
                continue
            cells = {k: html.unescape(re.sub(r"<[^>]+>", "", v)).strip() for k, v in
                     re.findall(r'data-stat="([a-z_0-9]+)"[^>]*>(.*?)</t[dh]>', row_html, re.S)}
            name = cells.get("name_display", "")
            if name in ("", "Player", "Team Totals", "League Average"):
                continue
            records.append(dict(season_end=year, player_name=name,
                                team=cells.get("team_name_abbr", ""), games=int(cells["games"]),
                                mp=int(cells["mp"] or 0),
                                and1s=int(cells["and1s"]) if cells.get("and1s") else 0,
                                source_url=url, retrieved_utc=fetched))
        print(f"basketball-reference {year}: fetched")
    keep = saved[saved["season_end"].isin(set(years) - set(missing))] if len(saved) else saved
    out = pd.concat([keep, pd.DataFrame(records)], ignore_index=True)
    out.to_csv(path, index=False)
    return out


def full_names(player_ids) -> dict[int, str]:
    """Play-by-play gives surnames only in the early seasons; ids resolve the full name."""
    from nba_api.stats.static import players

    known = {int(p["id"]): p["full_name"] for p in players.get_players()}
    missing = sorted(set(int(i) for i in player_ids) - set(known))
    if missing:
        raise ValueError(f"No NBA static name for player ids: {missing}")
    return {int(i): DISPLAY_NAMES.get(int(i), known[int(i)]) for i in player_ids}


def _fold(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", text))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    by_game = own_counts(args.refresh)
    chicago = by_game.groupby(["season", "player_id"]).agg(
        log_name=("player_name", "last"), games_with_and1=("game_id", "nunique"),
        and1s=("and1s", "sum"), and1s_3pt=("and1s_3pt", "sum"),
        and1s_flagrant=("and1s_flagrant", "sum"), and1s_made_ft=("and1s_made_ft", "sum"),
    ).reset_index()
    chicago["player_name"] = chicago["player_id"].map(full_names(chicago["player_id"]))

    chicago = chicago.merge(pbpstats_frame(args.refresh), on=["season", "player_id"],
                            how="left", validate="one_to_one")
    if chicago["off_poss"].isna().any() or (chicago["off_poss"] <= 0).any():
        raise ValueError("A counted Chicago player-season has no pbpstats possessions")
    chicago["per_100"] = 100 * chicago["and1s"] / chicago["off_poss"]

    bbr = bbr_league_rows(args.refresh)
    bbr["season"] = bbr["season_end"].map(lambda y: f"{y - 1}-{str(y)[-2:]}")
    bbr["key"] = bbr["player_name"].map(_fold)
    # Rank on full seasons: the multi-team row for a traded player, otherwise his one row.
    multi = bbr["team"].astype(str).str.match(r"^(\d+TM|TOT)$")
    traded = set(zip(bbr.loc[multi, "season"], bbr.loc[multi, "key"]))
    whole = bbr[multi | ~pd.Series([k in traded for k in zip(bbr["season"], bbr["key"])],
                                   index=bbr.index)].copy()
    whole["nba_rank"] = whole.groupby("season")["and1s"].rank(method="min",
                                                             ascending=False).astype(int)
    chicago["key"] = chicago["player_name"].map(_fold)
    chicago = chicago.merge(
        whole.drop_duplicates(["season", "key"], keep=False)[["season", "key", "nba_rank"]],
        on=["season", "key"], how="left", validate="one_to_one")
    chicago = chicago.merge(
        bbr[bbr["team"] == "CHI"].drop_duplicates(["season", "key"], keep=False)[
            ["season", "key", "and1s"]].rename(columns={"and1s": "bbr_and1s"}),
        on=["season", "key"], how="left", validate="one_to_one")
    chicago["diff_bbr"] = chicago["and1s"] - chicago["bbr_and1s"]
    chicago["diff_pbpstats"] = chicago["and1s"] - chicago["pbpstats_and1s"]
    chicago.drop(columns="key").to_csv(DATA / "all_player_seasons.csv", index=False)

    ranked = chicago.sort_values(["and1s", "per_100", "season"],
                                 ascending=[False, False, True]).reset_index(drop=True)
    # Exactly fifteen rows: a tie at the cutoff is broken on and-1s per 100 possessions,
    # then on the older season. Jalen Rose 2002-03 loses the 39 cutoff to Luol Deng 2006-07
    # (0.59 against 0.65 per 100).
    top = ranked.head(TOP_N).copy()
    top["bulls_rank"] = range(1, len(top) + 1)
    if top["nba_rank"].isna().any():
        raise ValueError("A selected row has no Basketball Reference league row for its rank")
    top["nba_rank"] = top["nba_rank"].astype(int)
    keep = ["bulls_rank", "player_id", "player_name", "season", "games", "off_poss", "and1s",
            "and1s_3pt", "and1s_flagrant", "and1s_made_ft", "per_100", "nba_rank",
            "bbr_and1s", "pbpstats_and1s"]
    top[keep].to_csv(DATA / "top15.csv", index=False)
    top[["player_name", "season", "and1s", "bbr_and1s", "pbpstats_and1s", "and1s_flagrant",
         "nba_rank", "off_poss", "per_100"]].to_csv(DATA / "selection_audit.csv", index=False)

    rows = []
    for source, column in (("basketball-reference", "diff_bbr"), ("pbpstats", "diff_pbpstats")):
        matched = chicago[column].notna()
        for era, mask in (("1996-97..1999-00", chicago["season"] < "2000-01"),
                          ("2000-01..2025-26", chicago["season"] >= "2000-01"),
                          ("all", chicago["season"].notna())):
            part = chicago.loc[matched & mask, column]
            rows.append(dict(source=source, era=era, matched=len(part),
                             exact=int((part == 0).sum()), net=int(part.sum()),
                             max_abs=int(part.abs().max()) if len(part) else 0))
    audit = pd.DataFrame(rows)
    audit.to_csv(DATA / "source_audit.csv", index=False)

    print(top[["bulls_rank", "player_name", "season", "and1s", "per_100", "nba_rank",
               "bbr_and1s", "pbpstats_and1s"]].round(2).to_string(index=False))
    print(f"\ncounted {int(chicago['and1s'].sum())} Chicago and-1s in "
          f"{int(by_game['game_id'].nunique())} games across {len(SEASONS)} seasons")
    print(audit.to_string(index=False))


if __name__ == "__main__":
    main()
