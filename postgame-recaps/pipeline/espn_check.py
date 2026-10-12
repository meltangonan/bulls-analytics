"""Cross-check a game's saved NBA.com feeds against ESPN's copy of the same game; list every number that differs.

    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/espn_check.py 0012600037

NBA.com stays the source of every published number (the user's rule, 2026-10-11: NBA.com wins; a difference is
flagged and Claude makes the judgment call in the review). ESPN gets the same official scorekeeping through its
own pipeline, so a difference points at a feed NBA.com served incomplete or stale (MIN at MIA, 2026-10-10: a shot
feed holding 72 of 87 attempts), at our own code, or at a stat correction one site has made and the other not yet.
It cannot catch a scorekeeper's error: both sites carry it. postgame_recap.py runs this once the data is ready
and never waits or stops on it.

Compared for both teams, against the files the slides are built from:
- the final score and the four quarter scores (summary_linescore.csv);
- every player's minutes (ESPN rounds to the minute), points, makes and attempts, rebounds, assists, steals,
  blocks, turnovers, fouls and +/-, who played (players.csv) and who started (recap_data.starters);
- the team box and fouls (teams.csv); paint, fast-break and off-turnover points, team and total turnovers,
  biggest lead and lead changes (summary_stats.csv, where the slides take them from);
- every field-goal attempt in NBA.com's shot feeds (shots_raw_chi.csv, shots_raw_opp.csv), matched to ESPN's
  play-by-play by period, game clock (within a second) and shooter: present, made or missed, 2 or 3 points;
- each team's running score through the game, recomputed from the made shots and free throws in pbp.csv as the
  slides do, against ESPN's scoring plays.
Not compared: what ESPN does not publish (second-chance and bench points, four factors, tracking, matchups),
overtime periods one by one (NBA.com's line score stops at Q4; the final score covers them) and shot locations
(ESPN's coordinates are not on NBA.com's scale).

ESPN's feed is unofficial and undocumented and can change without notice, so a failure to reach or read it is
reported as "could not run", never as agreement. ESPN's game summary (header, box score, plays) is saved as
espn_summary.json in the game folder. ESPN dates games in UTC; its scoreboard is searched by NBA.com's Eastern
date, and players are matched by name without accents, punctuation or suffixes (NBA.com "Brandon Boston",
ESPN "Brandon Boston Jr.").

Exit 0: everything compared agrees; 1: differences, listed; 2: could not check. The last line is the summary.
"""
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import game_dir  # noqa: E402
from recap_data import minutes, read, starters  # noqa: E402

API = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
PLAYER = {  # players.csv column: ESPN box key; "a-b" pairs are made-attempted
    "points": "points", "fieldGoalsMade-fieldGoalsAttempted": "fieldGoalsMade-fieldGoalsAttempted",
    "threePointersMade-threePointersAttempted": "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
    "freeThrowsMade-freeThrowsAttempted": "freeThrowsMade-freeThrowsAttempted",
    "reboundsOffensive": "offensiveRebounds", "reboundsDefensive": "defensiveRebounds", "reboundsTotal": "rebounds",
    "assists": "assists", "steals": "steals", "blocks": "blocks", "turnovers": "turnovers",
    "foulsPersonal": "fouls", "plusMinusPoints": "plusMinus"}
TEAM = {  # teams.csv column: ESPN team statistic
    "fieldGoalsMade-fieldGoalsAttempted": "fieldGoalsMade-fieldGoalsAttempted",
    "threePointersMade-threePointersAttempted": "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
    "freeThrowsMade-freeThrowsAttempted": "freeThrowsMade-freeThrowsAttempted",
    "reboundsOffensive": "offensiveRebounds", "reboundsDefensive": "defensiveRebounds", "reboundsTotal": "totalRebounds",
    "assists": "assists", "steals": "steals", "blocks": "blocks", "turnovers": "turnovers", "foulsPersonal": "fouls"}
SUMMARY = {  # summary_stats.csv column: ESPN team statistic
    "pointsInThePaint": "pointsInPaint", "pointsFastBreak": "fastBreakPoints", "turnoversTeam": "teamTurnovers", "turnoversTotal": "totalTurnovers", "biggestLead": "largestLead",
    "leadChanges": "leadChanges"}
# ESPN files points off turnovers under the team that committed the turnovers, NBA.com under the team that scored
# them: NBA.com's DEN 6, CHI 15 is ESPN's CHI 6, DEN 15 (CHI at DEN, 2025-26). Compared across, team to opponent.
OFF_TURNOVERS = ("pointsFromTurnovers", "turnoverPoints")
LABEL = {"points": "PTS", "fieldGoalsMade-fieldGoalsAttempted": "FG", "threePointersMade-threePointersAttempted": "3P",
         "freeThrowsMade-freeThrowsAttempted": "FT", "reboundsOffensive": "OREB", "reboundsDefensive": "DREB",
         "reboundsTotal": "REB", "assists": "AST", "steals": "STL", "blocks": "BLK", "turnovers": "TO",
         "foulsPersonal": "PF", "plusMinusPoints": "+/-", "pointsInThePaint": "points in the paint",
         "pointsFastBreak": "fast break points", "pointsFromTurnovers": "points off turnovers",
         "turnoversTeam": "team turnovers", "turnoversTotal": "total turnovers", "biggestLead": "biggest lead",
         "leadChanges": "lead changes"}


class CannotCheck(Exception):
    """ESPN has no usable copy of the game yet: not found, not final, or unreachable."""


def get(path: str, **params) -> dict:
    try:
        r = requests.get(f"{API}/{path}", params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        raise CannotCheck(f"ESPN did not answer ({type(e).__name__}: {e})") from e


def name_key(name: str) -> str:
    """A name as both sites can agree on it: no accents, punctuation, spaces or Jr./Sr./II-IV suffix."""
    plain = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return "".join(w for w in re.sub(r"[^a-z ]", " ", plain).split() if w not in SUFFIXES)


def value(v) -> str:
    """One number as both sites print it: 100.0 and "100" read 100, "+5" reads 5, a blank reads blank."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ("", "--"):
        return ""
    s = str(v).strip().lstrip("+")
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else s
    except ValueError:
        return s


def pair(row, col: str) -> str:
    """players.csv/teams.csv "fieldGoalsMade-fieldGoalsAttempted" read as ESPN prints it, "30-80"."""
    if "-" not in col:
        return value(row[col])
    made, att = col.split("-")
    return f"{value(row[made])}-{value(row[att])}"


def find_event(g: Path) -> str:
    """ESPN's event ID for the game, from ESPN's scoreboard on NBA.com's Eastern date, by the two team nicknames."""
    info, teams = read(g, "summary_game.csv"), read(g, "teams.csv")
    if info.empty or teams.empty:
        raise CannotCheck("the game's NBA.com summary or box score is not on disk; pull the game first")
    day = str(info.gameEt.iloc[0])[:10].replace("-", "")
    ours = set(teams.teamName)
    for event in get("scoreboard", dates=day).get("events", []):
        if {c["team"]["name"] for c in event["competitions"][0]["competitors"]} == ours:
            return event["id"]
    raise CannotCheck(f"ESPN's scoreboard for {day} has no {' vs '.join(sorted(ours))} game")


def espn_players(summary: dict) -> dict:
    """ESPN's box score: {ESPN team ID: [{"id", "name", "starter", "played", stats...}]}."""
    out = {}
    for team in summary["boxscore"]["players"]:
        block = team["statistics"][0]
        out[team["team"]["id"]] = [
            {"id": a["athlete"]["id"], "name": a["athlete"]["displayName"], "starter": bool(a.get("starter")),
             "played": bool(a.get("stats")) and not a.get("didNotPlay"), **dict(zip(block["keys"], a.get("stats") or []))}
            for a in block["athletes"]]
    return out


def match_players(nba: pd.DataFrame, espn: list) -> tuple[dict, list, list]:
    """{NBA personId: ESPN row} by name key, then by family name when it is unique on both rosters; and the
    players left unmatched on each side."""
    by_key = {name_key(e["name"]): e for e in espn}
    found, left = {}, []
    for r in nba.itertuples():
        e = by_key.get(name_key(f"{r.firstName} {r.familyName}"))
        (found.__setitem__(r.personId, e) if e else left.append(r))
    taken = {id(e) for e in found.values()}
    rest = [e for e in espn if id(e) not in taken]
    family = lambda name: name_key(name.split(" ", 1)[-1])
    still = []
    for r in left:
        hits = [e for e in rest if family(e["name"]) == name_key(r.familyName)]
        if len(hits) == 1 and sum(name_key(x.familyName) == name_key(r.familyName) for x in left) == 1:
            found[r.personId] = hits[0]
            rest.remove(hits[0])
        else:
            still.append(r)
    return found, still, rest


def clock_seconds(text: str) -> int:
    """Seconds left in the period: ESPN prints "10:35", and "45.2" in the last minute."""
    m, _, s = str(text).rpartition(":")
    return int(m or 0) * 60 + int(float(s))


def compare_shots(nba: pd.DataFrame, espn: list, ids: dict, who: str) -> tuple[int, list]:
    """Each NBA.com shot-feed attempt matched to an ESPN field-goal attempt by period, clock (within a second)
    and shooter; returns (values compared, differences)."""
    if nba.empty:
        return 0, [f"{who} shots: NBA.com's shot feed is not on disk; not compared"]
    pool = list(espn)
    out, compared = [], 0
    for s in nba.itertuples():
        left = int(s.MINUTES_REMAINING) * 60 + int(s.SECONDS_REMAINING)
        hits = [e for e in pool if e["period"] == s.PERIOD and e["player"] == ids.get(s.PLAYER_ID) and abs(e["left"] - left) <= 1]
        where = f"Q{s.PERIOD} {left // 60}:{left % 60:02d} {s.PLAYER_NAME}"
        compared += 1
        if not hits:
            out.append(f"{who} shot {where} ({'made' if s.SHOT_MADE_FLAG else 'missed'}) is not in ESPN's play-by-play")
            continue
        e = min(hits, key=lambda e: abs(e["left"] - left))
        pool.remove(e)
        mine = ("made" if s.SHOT_MADE_FLAG else "missed", 3 if str(s.SHOT_TYPE).startswith("3") else 2)
        theirs = ("made" if e["made"] else "missed", e["value"])
        compared += 2
        if mine != theirs:
            out.append(f"{who} shot {where}: NBA.com {mine[0]} {mine[1]}, ESPN {theirs[0]} {theirs[1]}")
    compared += len(pool)
    for e in pool:
        where = f"{who} shot Q{e['period']} {e['left'] // 60}:{e['left'] % 60:02d} {e['name']} ({'made' if e['made'] else 'missed'} {e['value']})"
        # A missed end-of-period heave ESPN logs but neither box score counts (MEM at CHI, Oct 9: Essengue 1-6 on
        # both sites, a fourth-quarter heave on ESPN's play-by-play only): a note, not a difference.
        out.append(f"note: {where} is a heave on ESPN's play-by-play only" if e["heave"] and not e["made"]
                   else f"{where} is on ESPN but not in NBA.com's shot feed")
    return compared, out


def nba_scoring(pbp: pd.DataFrame, team_id: int) -> list:
    """The team's running score after each of its scoring plays, from the plays as the slides count them."""
    made_ft = (pbp.actionType == "Free Throw") & pbp.scoreHome.notna() & ~pbp.description.fillna("").str.startswith("MISS")
    rows = pbp[((pbp.actionType == "Made Shot") | made_ft) & (pbp.teamId == team_id)]
    pts = [int(r.shotValue) if r.actionType == "Made Shot" else 1 for r in rows.itertuples()]
    return [(r.period, str(r.clock), total) for r, total in zip(rows.itertuples(), pd.Series(pts).cumsum())]


def nba_clock(text: str) -> str:
    """NBA.com's "PT01M13.00S" as "1:13"."""
    m = re.match(r"PT(\d+)M(\d+)", str(text))
    return f"{int(m.group(1))}:{m.group(2)}" if m else str(text)


def compare_scoring(nba: list, espn: list, who: str) -> tuple[int, list]:
    """The first point where the two running scores part, if they do."""
    for i, (a, b) in enumerate(zip(nba, espn)):
        if a[2] != b[2]:
            return i + 1, [f"{who} running score parts at scoring play {i + 1}: NBA.com reaches {a[2]} "
                           f"(Q{a[0]} {nba_clock(a[1])}), ESPN {b[2]} (Q{b[0]} {b[1]})"]
    if len(nba) != len(espn):
        return len(nba), [f"{who} scoring plays: NBA.com {len(nba)}, ESPN {len(espn)}"]
    return len(nba), []


def check(g: Path, summary: dict) -> tuple[int, list]:
    """(values compared, differences) between the NBA.com feeds in g and ESPN's game summary."""
    comp = summary["header"]["competitions"][0]
    if not comp["status"]["type"].get("completed"):
        raise CannotCheck(f"ESPN does not show the game as final yet ({comp['status']['type'].get('detail')})")
    teams, players = read(g, "teams.csv"), read(g, "players.csv")
    lines, stats, pbp = read(g, "summary_linescore.csv"), read(g, "summary_stats.csv"), read(g, "pbp.csv")
    espn_team = {c["team"]["name"]: c for c in comp["competitors"]}
    espn_box = {t["team"]["id"]: {s["name"]: s["displayValue"] for s in t["statistics"]} for t in summary["boxscore"]["teams"]}
    espn_people = espn_players(summary)
    plays = summary.get("plays", [])
    names = {e["id"]: e["name"] for team in espn_people.values() for e in team}
    compared, out = 0, []

    def same(who: str, label: str, mine, theirs) -> None:
        nonlocal compared
        if value(theirs) == "":  # ESPN did not publish it (lead changes on some 2025-26 games): not a zero
            out.append(f"note: ESPN does not publish {who} {label} for this game; not compared")
            return
        compared += 1
        if value(mine) != value(theirs):
            out.append(f"{who} {label}: NBA.com {value(mine) or 'blank'}, ESPN {value(theirs) or 'blank'}")

    for t in teams.itertuples():
        c = espn_team[t.teamName]
        tri, eid = t.teamTricode, c["team"]["id"]
        line = lines[lines.teamId == t.teamId]
        same(tri, "final score", line.score.iloc[0] if not line.empty else t.points, c["score"])
        for q, ls in enumerate(c.get("linescores", [])[:4], start=1):
            same(tri, f"Q{q} points", line[f"period{q}Score"].iloc[0] if not line.empty else None, ls["displayValue"])
        row = teams[teams.teamId == t.teamId].iloc[0]
        for col, key in TEAM.items():
            same(tri, LABEL[col], pair(row, col), espn_box[eid].get(key))
        srow = stats[stats.teamId == t.teamId]
        for col, key in SUMMARY.items():
            same(tri, LABEL[col], srow[col].iloc[0] if not srow.empty else None, espn_box[eid].get(key))
        opponent = next(c2["team"]["id"] for c2 in comp["competitors"] if c2["team"]["id"] != eid)
        same(tri, LABEL[OFF_TURNOVERS[0]], srow[OFF_TURNOVERS[0]].iloc[0] if not srow.empty else None,
             espn_box[opponent].get(OFF_TURNOVERS[1]))

        # Players: everyone either site lists as having played.
        mine = players[players.teamId == t.teamId]
        try:  # the five the slides print (NBA.com's preseason box also marks bench centers)
            started = starters(players, pbp, t.teamId)
        except ValueError as e:  # the build stops on this too
            out.append(f"{tri} {e}")
            started = set(mine.personId[mine.position.notna()])
        ids, nba_only, espn_only = match_players(mine, espn_people.get(eid, []))
        for r in nba_only:
            if minutes(r.minutes) > 0:
                out.append(f"{tri} {r.firstName} {r.familyName} played on NBA.com but is not in ESPN's box score")
        for e in espn_only:
            if e["played"]:
                out.append(f"{tri} {e['name']} played on ESPN but is not in NBA.com's box score")
        for r in mine.itertuples():
            e = ids.get(r.personId)
            if e is None:
                continue
            who, played = f"{tri} {r.familyName}", minutes(r.minutes) > 0
            same(who, "played", "yes" if played else "no", "yes" if e["played"] else "no")
            same(who, "started", "yes" if r.personId in started else "no", "yes" if e["starter"] else "no")
            if not (played and e["played"]):
                continue
            compared += 1
            if abs(minutes(r.minutes) - float(e.get("minutes") or 0)) > 0.51:  # ESPN rounds 22:30 to 23
                out.append(f"{who} minutes: NBA.com {r.minutes}, ESPN {e.get('minutes')}")
            prow = mine[mine.personId == r.personId].iloc[0]
            for col, key in PLAYER.items():
                same(who, LABEL[col], pair(prow, col), e.get(key))

        # Shots and the running score, matched through the player IDs above.
        shooter = lambda p: p["participants"][0]["athlete"]["id"] if p.get("participants") else None  # then the blocker
        espn_shots = [{"period": p["period"]["number"], "left": clock_seconds(p["clock"]["displayValue"]),
                       "player": shooter(p), "name": names.get(shooter(p), "?"), "made": bool(p.get("scoringPlay")),
                       "value": p.get("pointsAttempted"), "heave": "Heave" in p.get("type", {}).get("text", "")}
                      for p in plays if p.get("shootingPlay") and p.get("pointsAttempted", 0) >= 2
                      and p.get("team", {}).get("id") == eid]
        to_espn = {pid: e["id"] for pid, e in ids.items()}
        shots = read(g, "shots_raw_chi.csv")
        shots = shots[shots.TEAM_ID == t.teamId] if not shots.empty else shots
        if shots.empty:
            other = read(g, "shots_raw_opp.csv")
            shots = other[other.TEAM_ID == t.teamId] if not other.empty else other
        n, diffs = compare_shots(shots, espn_shots, to_espn, tri)
        compared, out = compared + n, out + diffs

        if not pbp.empty:
            espn_runs, total = [], 0
            for p in plays:
                if p.get("scoringPlay") and p.get("team", {}).get("id") == eid:
                    total += int(p.get("scoreValue", 0))
                    espn_runs.append((p["period"]["number"], p["clock"]["displayValue"], total))
            n, diffs = compare_scoring(nba_scoring(pbp, t.teamId), espn_runs, tri)
            compared, out = compared + n, out + diffs
    return compared, out


def main(game_id: str) -> None:
    g = game_dir(game_id)
    try:
        event = find_event(g)
        summary = get("summary", event=event)
        snapshot = {"source": f"{API}/summary?event={event}", "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    **{k: summary.get(k) for k in ("header", "boxscore", "plays")}}
        (g / "espn_summary.json").write_text(json.dumps(snapshot))
        compared, diffs = check(g, summary)
    except CannotCheck as e:
        print(f"espn check: could not run: {e}; compare by hand or run espn_check.py again later")
        sys.exit(2)
    notes = [d for d in diffs if d.startswith("note: ")]
    diffs = [d for d in diffs if d not in notes]
    for line in notes:
        print(f"espn {line}")
    for line in diffs:
        print(f"espn differs: {line}")
    print(f"espn check: {compared} values compared with ESPN event {event}, "
          + (f"{len(diffs)} differ (NBA.com stays the source; Claude reviews each)" if diffs else "all agree"))
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main(sys.argv[1])
