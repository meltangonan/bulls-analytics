"""Compute every number on the postgame recap pages for one game, into one JSON file.

    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/recap_data.py 0022500248

Reads the game folder (paths.game_dir, written by pull_game.py) and the baseline in baselines/league-2025-26/.
Writes output/postgame-recap/<id>/recap.json. The page (recap_template.html) only draws; it never
calculates. A page whose source feed is missing is set to null and the page builder skips it.

Baseline: league averages (points per possession, offensive-rebound rate, scatter reference line)
come from one completed regular season, BASELINE_SEASON.
"""
from __future__ import annotations

import json
import os
import math
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import accounting as acc  # noqa: E402
from bulls.analysis.shot_families import classify_series  # noqa: E402

# The featured team: the Bulls, unless FOCUS_TEAM_ID names another (used to dry-run on other games).
BULLS = int(os.environ.get("FOCUS_TEAM_ID", 1610612741))
FALLBACK = os.environ.get("RECAP_FALLBACK") == "1"
# Pages drawn from the second wave of NBA.com feeds (four factors, misc, the Bulls shot feed). With RECAP_EARLY=1
# the build leaves them pending and checks and draws the rest; postgame_recap.py renders that once for review.
LATE_PAGES = ["Team stats", "Shot chart", "Game breakdown"]
TRI = "CHI"  # set from the box score in build()
from paths import BASELINES, EARLY, OUTPUT, game_dir  # noqa: E402
BASELINE_SEASON = "2025-26"
SEASON_TYPES = {"001": "Preseason", "002": "Regular season", "004": "Playoffs", "005": "Play-in"}
PERIOD_NAMES = ["1ST", "2ND", "3RD", "4TH"]


class NotReady(Exception):
    """NBA.com has not finished publishing or correcting this game; postgame_recap.py waits and pulls again."""


NOT_READY = 75  # exit code for NotReady, so the caller can tell "wait" from "broken"


def read(folder: Path, name: str, **kw) -> pd.DataFrame:
    path = folder / name
    if not path.exists() or path.stat().st_size <= 1:
        return pd.DataFrame()
    return pd.read_csv(path, **kw)


def minutes(value) -> float:
    if not isinstance(value, str) or ":" not in value:
        return 0.0
    m, s = value.split(":")
    return int(m) + int(s) / 60


def clock_left(clock: str) -> float:
    m = re.match(r"PT(\d+)M([\d.]+)S", str(clock))
    return int(m[1]) * 60 + float(m[2]) if m else 0.0


def period_start(period: int) -> float:
    return 12 * min(period - 1, 4) + 5 * max(period - 5, 0)


def period_length(period: int) -> float:
    return 12 if period <= 4 else 5


def period_label(period: int) -> str:
    return PERIOD_NAMES[period - 1] if period <= 4 else ("OT" if period == 5 else f"{period - 4}OT")


def game_score(r) -> float:
    return (r.points + 0.4 * r.fieldGoalsMade - 0.7 * r.fieldGoalsAttempted
            - 0.4 * (r.freeThrowsAttempted - r.freeThrowsMade) + 0.7 * r.reboundsOffensive
            + 0.3 * r.reboundsDefensive + r.steals + 0.7 * r.assists + 0.7 * r.blocks
            - 0.4 * r.foulsPersonal - r.turnovers)


def short(name: str) -> str:
    return name.split(" ", 1)[1] if " " in name else name


def scoring_events(pbp: pd.DataFrame, chi_home: bool) -> pd.DataFrame:
    """One row per scoring change, with elapsed minutes and the Bulls margin after it.

    PlayByPlayV3 writes 0 into both score columns on non-scoring rows, so a running maximum
    recovers the true score before any margin is taken.
    """
    p = pbp.copy()
    # Only scoring actions carry a trustworthy score: a "Start of 3rd Period" row once carried a
    # later score (0012600030) and the running maximum hid five minutes of baskets behind it.
    scored = p.actionType.isin(["Made Shot", "Free Throw"])
    home = pd.to_numeric(p.scoreHome.where(scored), errors="coerce").fillna(0).cummax()
    away = pd.to_numeric(p.scoreAway.where(scored), errors="coerce").fillna(0).cummax()
    p["chi"], p["opp"] = (home, away) if chi_home else (away, home)
    p["t"] = [period_start(per) + period_length(per) - clock_left(c) / 60 for per, c in zip(p.period, p.clock)]
    p["margin"] = p.chi - p.opp
    p["personId"] = p.personId if "personId" in p else None
    changed = (p.chi.diff().fillna(p.chi) != 0) | (p.opp.diff().fillna(p.opp) != 0)
    return p[changed].reset_index(drop=True)


def score_steps(pbp: pd.DataFrame) -> list:
    """Scoring rows whose score change is not exactly the points scored, by the team that scored.

    Walking the made shots and made free throws in order, each must add its value (shotValue for a made
    shot, 1 for a free throw) to the scoring side's total and leave the other side unchanged. Clean feeds
    pass with no exceptions (all 14 saved games but the scrambled DEN at UTA feed); one bad row means the
    play-by-play cannot be trusted for the margin line, runs, breakdown or clutch points.
    """
    made_ft = (pbp.actionType == "Free Throw") & pbp.scoreHome.notna() & ~pbp.description.fillna("").str.startswith("MISS")
    rows = pbp[(pbp.actionType == "Made Shot") | made_ft]
    home = away = 0
    bad = []
    for r in rows.itertuples():
        pts = int(r.shotValue) if r.actionType == "Made Shot" else 1
        step = (int(r.scoreHome) - home, int(r.scoreAway) - away)
        if step != ((pts, 0) if r.location == "h" else (0, pts)):
            bad.append(f"action {r.actionNumber} (Q{r.period} {r.clock}): {r.description}")
        home, away = int(r.scoreHome), int(r.scoreAway)
    return bad


def bulls_games(league_games: pd.DataFrame) -> pd.DataFrame:
    """The Bulls' games from LeagueGameLog, with the margin taken from the two teams' points in the same log.

    LeagueGameFinder is not used: after an overnight stat correction (2026-10-08) it showed the Bulls'
    Oct 7 win as +0 while both teams' points were still right, so no provider plus-minus is trusted.
    """
    if league_games.empty:
        return league_games
    lg = league_games.assign(gid=league_games.GAME_ID.astype(str).str.zfill(10))
    opp = lg[lg.TEAM_ID != BULLS].groupby("gid").PTS.first()
    me = lg[lg.TEAM_ID == BULLS].copy()
    me["PLUS_MINUS"] = me.PTS - me.gid.map(opp)
    return me.dropna(subset=["PLUS_MINUS"]).drop(columns="gid")


def repair_scores(pbp: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """The play-by-play with each scoring row's running score recomputed from the plays themselves (shotValue
    for a made shot, 1 for a made free throw, added in feed order), and how many rows changed.

    Used only when the plays reach NBA.com's quarter scores but a running score printed on a row is wrong
    (MIN at MIA, 2026-10-10: a re-entered and-one printed 84-87 on the shot and 82-87 on its free throw, and
    NBA.com had not corrected it 50 minutes after Final). The repair is then held to the same tests as any
    feed: the score steps, and the game-flow counts against NBA.com's own (build() raises NotReady otherwise).
    """
    made_ft = (pbp.actionType == "Free Throw") & pbp.scoreHome.notna() & ~pbp.description.fillna("").str.startswith("MISS")
    rows = pbp.index[(pbp.actionType == "Made Shot") | made_ft]
    pts = pbp.loc[rows].apply(lambda r: int(r.shotValue) if r.actionType == "Made Shot" else 1, axis=1)
    home, away = (pts * (pbp.loc[rows, "location"] == "h")).cumsum(), (pts * (pbp.loc[rows, "location"] == "v")).cumsum()
    fixed = pbp.copy()
    changed = int(((fixed.loc[rows, "scoreHome"] != home) | (fixed.loc[rows, "scoreAway"] != away)).sum())
    fixed.loc[rows, "scoreHome"], fixed.loc[rows, "scoreAway"] = home, away
    return fixed, changed


def logs_match(game_id: str, players: pd.DataFrame, teams: pd.DataFrame, player_games: pd.DataFrame,
               league_games: pd.DataFrame) -> list:
    """Where NBA.com's game logs disagree with tonight's final box score.

    The season page, season leaders and notables read the game logs, which carry a game while it is still
    live and can lag the final box score. Every log must show tonight exactly as the box score does.
    """
    gid = lambda f: f.GAME_ID.astype(str).str.zfill(10) == game_id
    cols = {"PTS": "points", "REB": "reboundsTotal", "AST": "assists", "STL": "steals", "BLK": "blocks", "FG3M": "threePointersMade"}
    off = lambda log, key, row: key not in log.index or any(int(log.loc[key, k]) != int(getattr(row, v)) for k, v in cols.items())
    out = []
    lg = league_games[gid(league_games)].set_index("TEAM_ID") if not league_games.empty else pd.DataFrame()
    if lg.empty or any(off(lg, r.teamId, r) for r in teams.itertuples()):
        out.append("league game log (LeagueGameLog, teams)")
    pg = player_games[gid(player_games) & (player_games.TEAM_ID == BULLS)].set_index("PLAYER_ID") if not player_games.empty else pd.DataFrame()
    played = players[(players.teamId == BULLS) & players.minutes.map(minutes).gt(0)]
    if pg.empty or any(off(pg, r.personId, r) for r in played.itertuples()):
        out.append("player game log (LeagueGameLog, players)")
    return out


def feeds_agree(players: pd.DataFrame, teams: pd.DataFrame, ff: pd.DataFrame) -> list:
    """Where the separately cached box-score tables disagree: player rows against team totals, and NBA.com's
    four-factor eFG% and FT rate against the box score's own makes and attempts. A correction that has reached
    one request and not another shows up here (all 15 saved games agree)."""
    cols = ["points", "reboundsTotal", "reboundsOffensive", "assists", "fieldGoalsMade", "fieldGoalsAttempted",
            "threePointersMade", "threePointersAttempted", "freeThrowsMade", "freeThrowsAttempted", "steals",
            "blocks", "turnovers"]
    sums, out = players.groupby("teamId")[cols].sum(), []
    for r in teams.itertuples():
        if r.teamId not in sums.index or any(int(sums.loc[r.teamId, c]) != int(getattr(r, c)) for c in cols):
            out.append(f"{r.teamTricode} player rows do not add up to the team totals")
        f = ff[ff.teamId == r.teamId]
        efg = (r.fieldGoalsMade + 0.5 * r.threePointersMade) / r.fieldGoalsAttempted
        if f.empty or abs(efg - f.effectiveFieldGoalPercentage.iloc[0]) > 0.0015 \
                or abs(r.freeThrowsAttempted / r.fieldGoalsAttempted - f.freeThrowAttemptRate.iloc[0]) > 0.0015:
            out.append(f"{r.teamTricode} four factors do not match the box score")
    return out


def compare_flow(ours: dict, nba: dict, margin: int) -> tuple[str, str]:
    """Our game-flow counts against NBA.com's: "match" or what differs, plus a note on any NBA value skipped.

    A winner led by at least its final margin, so NBA.com's biggest lead below that margin is impossible
    and is left out of the comparison (HOU won 135-117 at DAL on 2026-10-09 and NBA.com still listed both
    teams' biggest lead as 0 nine hours later). Ours must pass the same test to be kept; every other count
    must still match exactly.
    """
    note = ""
    for side, lead in (("chi_lead", margin), ("opp_lead", -margin)):
        if lead > 0 and nba[side] < lead <= ours[side]:
            note = f"NBA.com's biggest lead of {nba[side]} is below the {lead}-point final margin, so ours was kept"
            nba = {**nba, side: ours[side]}
    return ("match" if ours == nba else f"differs: ours {ours}, NBA {nba}"), note


def picks(g: Path) -> dict:
    """The user's editorial calls for one game, from picks.json in its folder (optional): "mvp" (a personId),
    "drop_awards" (titles such as "#closer") and "moments" ([{"action": actionNumber, "label": ...}], scoring
    plays to label on the margin line). Calls, not numbers: every figure still comes from NBA.com's feeds."""
    f = g / "picks.json"
    return json.loads(f.read_text()) if f.exists() else {}


def flow(pbp: pd.DataFrame, chi_home: bool, opp_tri: str, moments: list = ()) -> dict:
    ev = scoring_events(pbp, chi_home)
    periods = int(pbp.period.max())
    total = period_start(periods) + period_length(periods)
    series = [[0.0, 0]] + [[round(t, 2), int(m)] for t, m in zip(ev.t, ev.margin)] + [[round(total, 2), int(ev.margin.iloc[-1])]]

    sign = np.sign(ev.margin.to_numpy())
    nonzero = sign[sign != 0]
    lead_changes = int((nonzero[1:] != nonzero[:-1]).sum())
    ties = int(((ev.margin == 0) & (ev.chi > 0)).sum())

    runs, team, run, best = [], None, 0, {TRI: 0, opp_tri: 0}
    prev_c, prev_o = 0, 0
    for c, o in zip(ev.chi, ev.opp):
        scorer, pts = (TRI, c - prev_c) if c != prev_c else (opp_tri, o - prev_o)
        run = run + pts if scorer == team else pts
        team = scorer
        best[team] = max(best[team], int(run))
        prev_c, prev_o = c, o

    hi_i, lo_i = int(ev.margin.idxmax()), int(ev.margin.idxmin())
    notes = []
    if ev.margin[hi_i] >= 5:
        notes.append({"t": float(ev.t[hi_i]), "m": int(ev.margin[hi_i]), "label": f"Up {int(ev.margin[hi_i])}", "kind": "high"})
    if ev.margin[lo_i] <= -5:
        notes.append({"t": float(ev.t[lo_i]), "m": int(ev.margin[lo_i]), "label": f"Down {-int(ev.margin[lo_i])}", "kind": "low"})
    final = int(ev.margin.iloc[-1])
    if final != 0:
        winner_side = np.sign(final)
        flips = [i for i in range(1, len(ev)) if np.sign(ev.margin[i]) == winner_side and np.sign(ev.margin[i - 1]) != winner_side]
        if flips:
            i = flips[-1]
            late = ev.period[i] >= 5 or (ev.period[i] == 4 and clock_left(ev.clock[i]) <= 360)
            if late and abs(final) <= 10:
                r = ev.iloc[i]
                what = "3" if r.actionType == "Made Shot" and int(r.shotValue) == 3 else ("free throw" if r.actionType == "Free Throw" else "basket")
                left = clock_left(ev.clock[i])
                notes.append({"t": float(ev.t[i]), "m": int(ev.margin[i]), "kind": "decider",
                              "label": f"{r.playerName} {what}",
                              "sub": f"{int(left // 60)}:{int(left % 60):02d} left" + ("" if ev.period[i] == 4 else f", {period_label(int(ev.period[i]))}")})
    for m in moments:
        row = ev[ev.actionNumber == m["action"]]
        if row.empty:
            raise ValueError(f"picks.json moment {m} is not a scoring play in the play-by-play")
        r = row.iloc[-1]
        notes.append({"t": float(r.t), "m": int(r.margin), "label": m["label"], "kind": "moment"})
    return {"series": series, "periods": periods, "total": total,
            "chi_lead": max(0, int(ev.margin.max())), "opp_lead": max(0, -int(ev.margin.min())),
            "lead_changes": lead_changes, "ties": ties, "run_chi": best[TRI], "run_opp": best[opp_tri],
            "notes": notes}


def four_factors(ff: pd.DataFrame, teams: pd.DataFrame, opp_tri: str, from_box: bool = False) -> dict:
    """NBA.com's official four factors (turnover % counts team turnovers), plus eFG%'s two parts.

    from_box (NBA.com's four factors cover only part of the game, past the deadline): eFG% and FT rate from the
    box score, which reproduces NBA.com's values to rounding (36 complete team-games, largest gap 0.05 points),
    and no TOV% or OREB%, which NBA.com computes from team turnovers, team rebounds and its own possessions
    (box-score versions were 2 to 4 points off typically, up to 11). The page prints a hyphen and says why."""
    cols = [("EFG%", "effectiveFieldGoalPercentage", True), ("TOV%", "teamTurnoverPercentage", False),
            ("OREB%", "offensiveReboundPercentage", True), ("FT RATE", "freeThrowAttemptRate", True)]
    t = teams.set_index("teamTricode")
    if from_box:
        box = {"effectiveFieldGoalPercentage": lambda r: (r.fieldGoalsMade + 0.5 * r.threePointersMade) / r.fieldGoalsAttempted,
               "freeThrowAttemptRate": lambda r: r.freeThrowsAttempted / r.fieldGoalsAttempted}
        rows = [[label, *[round(float(box[col](t.loc[tri])) * 100, 1) if col in box else None for tri in (TRI, opp_tri)], higher]
                for label, col, higher in cols]
    else:
        rows = [[label, *[round(float(ff.loc[ff.teamTricode == tri, col].iloc[0]) * 100, 1) for tri in (TRI, opp_tri)], higher]
                for label, col, higher in cols]
    split = []
    for tri in (TRI, opp_tri):
        r = t.loc[tri]
        two_a = r.fieldGoalsAttempted - r.threePointersAttempted
        split.append([round(100 * (r.fieldGoalsMade - r.threePointersMade) / two_a, 1) if two_a else None,
                      round(100 * r.threePointersMade / r.threePointersAttempted, 1) if r.threePointersAttempted else None])
    return {"rows": rows, "efg_split": split, "source": "box" if from_box else "nba"}


def shots_from_pbp(pbp: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """The team's field goal attempts from the play-by-play, in the shot feed's columns (ShotChartDetail names).

    On the 13 saved games every attempt is in the play-by-play, and the 1,220 matched to the shot feed have the
    same location, result, 2 or 3 points and shot type (subType is ShotChartDetail's ACTION_TYPE). What the
    play-by-play lacks is NBA.com's zone label, so the zones chart places these shots by their coordinates,
    which put 1,217 of the 1,220 in the same zone (the other three sit on a zone boundary)."""
    fg = pbp[(pbp.isFieldGoal == 1) & (pbp.teamId == team_id)]
    return pd.DataFrame({
        "GAME_ID": fg.gameId, "GAME_EVENT_ID": fg.actionNumber, "PLAYER_ID": fg.personId, "PLAYER_NAME": fg.playerName,
        "TEAM_ID": fg.teamId, "PERIOD": fg.period, "ACTION_TYPE": fg.subType,
        "SHOT_TYPE": fg.shotValue.map(lambda v: "3PT Field Goal" if v == 3 else "2PT Field Goal"),
        "SHOT_DISTANCE": fg.shotDistance, "LOC_X": fg.xLegacy, "LOC_Y": fg.yLegacy,
        "SHOT_MADE_FLAG": (fg.shotResult == "Made").astype(int)}).reset_index(drop=True)


def ff_minutes_short(ff: pd.DataFrame, teams: pd.DataFrame) -> str:
    """When NBA.com's four factors cover fewer minutes than the box score, say how many ("" when complete):
    MIN at MIA, 2026-10-10, published four factors for 203 of 240 team-minutes and kept them past 50 minutes."""
    have = ff.minutes.map(minutes).min() if not ff.empty else 0
    game = teams.minutes.map(minutes).max()
    return f"{have:.0f} of {game:.0f} minutes" if have < game - 0.5 else ""


def head_to_head(teams: pd.DataFrame, misc: pd.DataFrame, stats: pd.DataFrame, opp_tri: str) -> list:
    t = {r.teamTricode: r for r in teams.itertuples()}
    c, o = t[TRI], t[opp_tri]

    # The bar and the bold side follow makes, not percentage (user, 2026-10-12): 13-18 and 32-46 free throws are
    # both about 70% but 19 points apart, and a percentage bar drew them even. The text keeps the percentage.
    def shoot(label, m, a):
        cm, ca, om, oa = getattr(c, m), getattr(c, a), getattr(o, m), getattr(o, a)
        cp, op = (100 * cm / ca if ca else 0), (100 * om / oa if oa else 0)
        return [label, f"{cm}-{ca} ({cp:.1f}%)", f"({op:.1f}%) {om}-{oa}", cm, om, 1]

    rows = [shoot("Field goals", "fieldGoalsMade", "fieldGoalsAttempted"),
            shoot("3-pointers", "threePointersMade", "threePointersAttempted"),
            shoot("Free throws", "freeThrowsMade", "freeThrowsAttempted")]
    for label, col in (("Rebounds", "reboundsTotal"), ("Offensive rebounds", "reboundsOffensive"),
                       ("Assists", "assists"), ("Steals", "steals"), ("Blocks", "blocks")):
        rows.append([label, str(getattr(c, col)), str(getattr(o, col)), getattr(c, col), getattr(o, col), 1])
    if not stats.empty:
        s = {r.teamTricode: r for r in stats.itertuples()}
        rows.append(["Turnovers", str(int(s[TRI].turnoversTotal)), str(int(s[opp_tri].turnoversTotal)),
                     int(s[TRI].turnoversTotal), int(s[opp_tri].turnoversTotal), 0])
    # From the game summary, which NBA.com publishes for the whole game with the box score; the misc feed holds
    # the same four counts (144 of 144 equal on the saved complete games) but can stop early (MIN at MIA,
    # 2026-10-10: 203 of 240 minutes, still so 55 minutes after Final).
    if not stats.empty:
        for label, col in (("Points in the paint", "pointsInThePaint"), ("Fast break points", "pointsFastBreak"),
                           ("Second chance points", "pointsSecondChance"), ("Points off turnovers", "pointsFromTurnovers")):
            rows.append([label, str(int(getattr(s[TRI], col))), str(int(getattr(s[opp_tri], col))),
                         int(getattr(s[TRI], col)), int(getattr(s[opp_tri], col)), 1])
    return rows


# Numbers the user confirmed where NBA.com's roster is wrong (2026-10-09: it listed Buddy Hield as #8, Caleb
# Wilson's number; Hield wears 7).
JERSEY_FIX = {1627741: "7"}


def fold(name) -> str:
    """'Jović' and 'Jovic' compare equal: the play-by-play spells some names without accents."""
    return unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower().strip()


def starters(players: pd.DataFrame, pbp: pd.DataFrame, team_id: int | None = None) -> set:
    """personIds of a team's starting five (the Bulls by default).

    The box score marks starters with a position (F, F, C, G, G). NBA.com's preseason box also marks one or two
    more, always centers who came off the bench (6 of 8 saved 2026-27 preseason games; MEM's Quinten Post in
    0012600037, ORL's Bitadze and Vucevic in 0012600041). With more than five marked, keep those on the floor
    at the opening tip: their first first-period play comes before any "SUB: <name> FOR" bringing them in
    (ESPN's starters agree on every saved game it covers). Anything but five stops the build for review rather
    than print a guess.
    """
    team_id = BULLS if team_id is None else team_id
    t = players[players.teamId == team_id]
    marked = t[t.position.notna() & (t.position.astype(str).str.strip() != "")]
    if len(marked) > 5:
        q1 = pbp[(pbp.period == 1) & (pbp.teamId == team_id)].sort_values("actionNumber")
        subs = q1[q1.actionType == "Substitution"]
        incoming = subs.description.str.extract(r"^SUB: (.+?) FOR ", expand=False).map(fold)

        def at_tip(r) -> bool:
            plays = q1.actionNumber[q1.personId == r.personId]
            if plays.empty:  # no first-period play: unproven, so the count check below stops the build
                return False
            names = {fold(r.familyName), fold(f"{str(r.firstName)[:1]}. {r.familyName}")}  # "B. Brown" when two share one
            return not incoming[subs.actionNumber < plays.min()].isin(names).any()

        marked = marked[marked.apply(at_tip, axis=1)]
    if len(marked) != 5:
        raise ValueError(f"cannot settle {t.teamTricode.iloc[0]}'s starting five: NBA.com marks "
                         f"{', '.join(t.familyName[t.position.notna()])}; the play-by-play keeps {len(marked)}")
    return set(marked.personId.astype(int))


def box(players: pd.DataFrame, roster: pd.DataFrame, starter_ids: set, team_minutes: str | None = None) -> dict:
    """Bulls rows. Jersey numbers come from the roster pulled with the game (the box score's jerseyNum is
    blank, current games included; rechecked 2026-10-07); no number rather than a guess."""
    p = players[players.teamId == BULLS].copy()
    p["min"] = p.minutes.map(minutes)
    def jersey(v) -> str:
        """'3', not '3.0': pandas reads the column as decimals when any number is missing; '00' stays '00'."""
        if pd.isna(v) or str(v).strip() in ("", "nan"):
            return ""
        t = str(v).strip()
        return t[:-2] if t.endswith(".0") else t
    num = {int(k): jersey(v) for k, v in zip(roster.PLAYER_ID, roster.NUM)} if not roster.empty else {}
    num.update({int(r.personId): jersey(r.jerseyNum) for r in p.itertuples() if jersey(r.jerseyNum)})
    num.update(JERSEY_FIX)
    # Two players in one game cannot share a number (camp rosters list pairs who never play together, such as
    # Peterson and Claxton at 9). When two who played tonight share one, a confirmed number keeps it and every
    # unconfirmed holder prints none (Game 1: Miller and Boston at 11).
    seen = pd.Series({k: v for k, v in num.items() if k in set(p.personId[p["min"] > 0]) and v})
    num.update({k: "" for k in seen[seen.duplicated(keep=False)].index if k not in JERSEY_FIX})
    played = p[p["min"] > 0]
    dnp = p[p["min"] == 0]

    def row(r):
        return [int(r.personId), f"{r.firstName} {r.familyName}", int(round(r.min)), int(r.points), int(r.reboundsTotal),
                int(r.assists), int(r.fieldGoalsMade), int(r.fieldGoalsAttempted), int(r.threePointersMade),
                int(r.threePointersAttempted), int(r.freeThrowsMade), int(r.freeThrowsAttempted), int(r.steals),
                int(r.blocks), int(r.turnovers), int(r.plusMinusPoints), num.get(r.personId, "")]

    starters = played[played.personId.isin(starter_ids)]
    bench = played.drop(starters.index)
    order = lambda frame: frame.sort_values(["points", "min"], ascending=False)
    # Minutes totals add the exact minutes and round once; rounding each player first drifts (238 of 240).
    team_min = int(round(minutes(team_minutes))) if team_minutes else int(round(played["min"].sum()))
    return {"minutes": [int(round(starters["min"].sum())), int(round(bench["min"].sum())), team_min],
            "starters": [row(r) for r in order(starters).itertuples()],
            "bench": [row(r) for r in order(bench).itertuples()],
            "dnp": [f"{r.firstName} {r.familyName}" for r in dnp.itertuples()]}


def shot_types(raw: pd.DataFrame) -> list:
    if raw.empty:
        return []
    fam = classify_series(raw.ACTION_TYPE)
    made = raw.SHOT_MADE_FLAG == 1
    groups = [("Layups", ["Layups"]), ("Dunks", ["Dunks"]), ("Floaters", ["Floaters"]),
              ("Pull-ups", ["Pull-ups", "Step-backs"]), ("Standard jump shots", ["Standard jumpers"]),
              ("Other", ["Turnarounds/fades", "Running jumpers", "Tip-ins", "Hooks"])]
    return [[label, int(made[fam.isin(f)].sum()), int(fam.isin(f).sum())] for label, f in groups if fam.isin(f).sum()]


EAST = {"ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS"}


def east_place(league_games: pd.DataFrame, dates: list) -> list:
    conf = EAST if TRI in EAST else set(league_games.TEAM_ABBREVIATION) - EAST
    # A game still in progress is in the log with no result (Game 1's log held GSW at POR at half-time); it must
    # count for no one, not as a loss. The featured team's own rows stay (its game tonight is final).
    settled = league_games.WL.isin(["W", "L"]) | (league_games.TEAM_ABBREVIATION == TRI)
    east = league_games[league_games.TEAM_ABBREVIATION.isin(conf) & settled]
    out = []
    for date in dates:
        played = east[east.GAME_DATE <= date]
        w = played.WL.eq("W").groupby(played.TEAM_ABBREVIATION).mean()
        out.append([int((w > w[TRI]).sum()) + 1, bool((w == w[TRI]).sum() > 1)])
    return out


def season(team_games: pd.DataFrame, schedule: pd.DataFrame, league_games: pd.DataFrame, game_id: str) -> dict:
    g = team_games.copy()
    g["GAME_ID"] = g.GAME_ID.astype(str).str.zfill(10)
    g = g.sort_values("GAME_DATE")
    date = g.loc[g.GAME_ID == game_id, "GAME_DATE"].iloc[0]
    played = g[g.GAME_DATE <= date]
    games = [[r.GAME_DATE[:10], r.MATCHUP.split()[-1], 0 if "@" in r.MATCHUP else 1, int(r.PLUS_MINUS)] for r in played.itertuples()]
    kind = game_id[:3]
    scheduled = int(schedule.gameId.astype(str).str.zfill(10).str[:3].eq(kind).sum()) if not schedule.empty else 0
    slots = 82 if kind == "002" else max(scheduled, len(played))
    wins = sum(1 for x in games if x[3] > 0)
    # Month labels across every slot, played or not, from the schedule: [slot index, "Nov"].
    sched = schedule.assign(gid=schedule.gameId.astype(str).str.zfill(10)) if not schedule.empty else schedule
    dates = (pd.to_datetime(sched.loc[sched.gid.str[:3] == kind, "gameDate"]).sort_values().dt.strftime("%Y-%m-%d").tolist()
             if not sched.empty else [])
    dates = dates if len(dates) >= len(games) else [x[0] for x in games]
    months, seen = [], None
    for i, d in enumerate(dates):
        if d[:7] != seen:
            seen = d[:7]
            months.append([i, pd.Timestamp(d).strftime("%b")])
    upcoming = []
    if not sched.empty and "homeTeam_teamTricode" in sched:
        rest = sched[(sched.gid.str[:3] == kind) & (pd.to_datetime(sched.gameDate) > pd.Timestamp(date[:10]))]
        for r in rest.assign(d=pd.to_datetime(rest.gameDate)).sort_values("d").itertuples():
            home = r.homeTeam_teamTricode == TRI
            upcoming.append([r.awayTeam_teamTricode if home else r.homeTeam_teamTricode, int(home)])
    # Games over .500 after each game (wins minus losses), and tonight's place in the East.
    over = np.cumsum([1 if x[3] > 0 else -1 for x in games]).tolist()
    east = east_place(league_games, [x[0] for x in games[-2:]]) if not league_games.empty else None
    return {"games": games, "slots": slots, "wins": wins, "losses": len(games) - wins, "over": over,
            "conf": "East" if TRI in EAST else "West", "east": east[-1] if east else None, "east_prev": east[0] if east and len(games) > 1 else None, "months": months, "upcoming": upcoming}


def breakdown(pbp: pd.DataFrame, teams: pd.DataFrame, opp_tri: str) -> dict:
    ids = {int(r.teamId): r.teamTricode for r in teams.itertuples()}
    split = {}
    cats, poss, pts = acc.account(pbp, ids, split)
    official = {r.teamTricode: int(r.points) for r in teams.itertuples()}
    if pts != official:
        raise NotReady(f"play-by-play points {pts} do not match the box score {official}")
    c = acc.centred(cats, poss)
    edge = {k: c[TRI][k] - c[opp_tri][k] for k in c[TRI]}
    extra = acc.V * (poss[TRI] - poss[opp_tri])
    margin = official[TRI] - official[opp_tri]
    if abs(sum(edge.values()) + extra - margin) > 1e-6:
        raise ValueError("four-factor accounting does not reconcile to the margin")
    rows = [["Shooting", edge["shoot"]], ["Turnovers", edge["tov"]], ["Rebounding", edge["reb"]],
            ["Free throws", edge["ft"]], ["Other", edge["other"]]]
    if poss[TRI] != poss[opp_tri]:
        rows.append(["Extra possession" if extra > 0 else "Fewer possessions", extra])
    # Worked numbers for the page's explainer, from the same baseline the bars use.
    # Three decimals, so the page's worked arithmetic reproduces its own totals.
    example = {"v": round(acc.V, 3), "make2": round(2 - acc.V, 3), "make3": round(3 - acc.V, 3), "miss_value": round(acc.P * acc.V, 3),
               "miss": round(acc.P * acc.V - acc.V, 3), "oreb_pct": int(round(acc.P * 100)), "oreb": round(acc.V - acc.P * acc.V, 3)}
    # Each team's four factors in points against an average team on its own possessions (no total:
    # the two teams' rows differ from the margin by the extra-possession and other lines).
    teams_vs = {t: {"shoot": c[t]["shoot"], "shoot3": split[t][3] - acc.base_shot[3] * poss[t],
                    "shoot2": split[t][2] - acc.base_shot[2] * poss[t], "tov": c[t]["tov"], "reb": c[t]["reb"], "ft": c[t]["ft"]}
                for t in (TRI, opp_tri)}
    shots = {}
    for t in (TRI, opp_tri):
        sh = pbp[(pbp.teamTricode == t) & pbp.actionType.isin(["Made Shot", "Missed Shot"])]
        m2 = int(((sh.actionType == "Made Shot") & (sh.shotValue == 2)).sum())
        m3 = int(((sh.actionType == "Made Shot") & (sh.shotValue == 3)).sum())
        miss = int((sh.actionType == "Missed Shot").sum())
        formula = m2 * (2 - acc.V) + m3 * (3 - acc.V) + miss * (acc.P * acc.V - acc.V)
        shots[t] = {"m2": m2, "m3": m3, "miss": miss, "raw": round(cats[t]["shoot"], 2),
                    "shown": round(m2 * example["make2"] + m3 * example["make3"] + miss * example["miss"], 3),
                    "expected": round(acc.base["shoot"] * poss[t], 2), "vs": round(c[t]["shoot"], 2),
                    "formula_ok": abs(formula - cats[t]["shoot"]) < 0.05}
    return {"shots": shots, "teams": {t: {k: round(float(v), 1) for k, v in d.items()} for t, d in teams_vs.items()},
            "rows": [[k, round(v, 1)] for k, v in rows], "margin": margin,
            "possessions": [poss[TRI], poss[opp_tri]], "ppp": round(acc.V, 2), "example": example}


def awards(players: pd.DataFrame, raw: pd.DataFrame, pbp: pd.DataFrame, chi_home: bool, starter_ids: set,
           pick: dict | None = None) -> list:
    p = players[(players.teamId == BULLS) & players.minutes.map(minutes).gt(0)].copy()
    if p.empty:
        return []
    p["name"] = p.firstName + " " + p.familyName
    p["gmsc"] = game_score(p)  # Game Score picks the top performers; it is not printed
    p["starter"] = p.personId.isin(starter_ids)
    p = p.set_index("personId", drop=False)
    fg = lambda i: f"{p.fieldGoalsMade[i]}-{p.fieldGoalsAttempted[i]} FG"
    cands = []  # (title, series, floor, line)

    def add(title, series, floor, line):
        series = series.dropna()
        if len(series) and series.max() >= floor:
            cands.append((title, series, floor, line))

    pick = pick or {}
    tp = int(pick["mvp"]) if "mvp" in pick else p.gmsc.idxmax()
    if tp not in p.index:
        raise ValueError(f"picks.json mvp {tp} did not play for the Bulls")
    tens = {"points": "PTS", "reboundsTotal": "REB", "assists": "AST", "steals": "STL", "blocks": "BLK"}
    cats = p[list(tens)].ge(10).sum(axis=1)
    hit =[f"{int(p.loc[tp, c])} {label}" for c, label in tens.items() if p.loc[tp, c] >= 10]
    if len(hit) >= 3:
        line = ", ".join(hit)
    else:
        scale = {"reboundsTotal": ("REB", 10, 5), "assists": ("AST", 10, 5), "steals": ("STL", 3, 2),
                 "blocks": ("BLK", 3, 2), "threePointersMade": ("3PM", 4, 3)}
        extra = sorted(((p.loc[tp, c] / unit, c) for c, (_, unit, floor) in scale.items() if p.loc[tp, c] >= floor), reverse=True)[:2]
        line = ", ".join([f"{p.points[tp]} PTS on {fg(tp)}"] + [f"{int(p.loc[tp, c])} {scale[c][0]}" for _, c in extra])
    out = [["#mvp", int(tp), p.loc[tp, "name"], line]]

    td = cats.drop(tp)
    add("#tripledouble", td.where(td >= 3), 1, lambda i: f"{p.points[i]} PTS, {p.reboundsTotal[i]} REB, {p.assists[i]} AST")
    shooters = p[p.fieldGoalsAttempted >= 10]
    add("#efficient", (shooters.fieldGoalsMade / shooters.fieldGoalsAttempted), 0.70,
        lambda i: f"{fg(i)} ({100 * p.fieldGoalsMade[i] / p.fieldGoalsAttempted[i]:.0f}%)")
    add("#sniper", p.threePointersMade - p.threePointersAttempted / 1000, 5, lambda i: f"{p.threePointersMade[i]}-{p.threePointersAttempted[i]} from three")
    add("#cookiemonster", p.steals, 4, lambda i: f"{p.steals[i]} steals")
    add("#blockparty", p.blocks, 4, lambda i: f"{p.blocks[i]} blocks")
    add("#windex", p.reboundsTotal, 15, lambda i: f"{p.reboundsTotal[i]} rebounds")
    add("#boardman", p.reboundsOffensive, 5, lambda i: f"{p.reboundsOffensive[i]} offensive rebounds")
    add("#dimer", p.assists, 8, lambda i: f"{p.assists[i]} assists")
    add("#sparkplug", p.gmsc[~p.starter].drop(tp, errors="ignore"), 15, lambda i: f"{p.points[i]} PTS on {fg(i)} off the bench")

    ev = scoring_events(pbp, chi_home)
    ev["before"] = ev.margin.shift().fillna(0)
    ev["chi_pts"] = ev.chi.diff().fillna(ev.chi)
    late = ev[(ev.period >= 4) & ev.clock.map(clock_left).le(300) & ev.before.abs().le(5) & ev.chi_pts.gt(0)]
    clutch = late.groupby("personId").chi_pts.sum()
    clutch = clutch[clutch.index.isin(p.index)]
    add("#closer", clutch, 5, lambda i: f"{int(clutch[i])} clutch PTS")

    if not raw.empty:
        raw = raw.assign(fam=classify_series(raw.ACTION_TYPE), made=raw.SHOT_MADE_FLAG == 1)
        dunks = raw[(raw.fam == "Dunks") & raw.made].groupby("PLAYER_ID").size()
        add("#highflyer", dunks, 5, lambda i: f"{dunks[i]} dunks")

    cands = [c for c in cands if c[0] not in pick.get("drop_awards", [])]
    wins = {int(tp): 1}
    ranked = []
    for order, (title, series, floor, line) in enumerate(cands):
        leader = series.idxmax()
        ranked.append((-(series[leader] / floor), order, title, leader, line))
    for _, _, title, i, line in sorted(ranked):
        if wins.get(int(i), 0) < 2:
            wins[int(i)] = wins.get(int(i), 0) + 1
            out.append([title, int(i), p.loc[i, "name"], line(i)])
    return out


def scatter(adv: pd.DataFrame, opp_tri: str) -> list:
    if adv.empty:
        return []
    a = adv[(adv.possessions >= 20) & adv.teamTricode.isin([TRI, opp_tri])]
    return [[r.familyName, r.teamTricode, float(r.offensiveRating), float(r.defensiveRating), int(r.possessions)] for r in a.itertuples()]


def matchups(m: pd.DataFrame, players: pd.DataFrame, opp_tri: str) -> list | None:
    if m.empty:
        return None
    opp = players[players.teamTricode == opp_tri].sort_values("points", ascending=False).head(3)
    out = []
    for star in opp.itertuples():
        x = m[m.personIdOff == star.personId].sort_values("partialPossessions", ascending=False)
        if x.empty:
            continue
        keep = list(x.index[:3])
        worst = x.playerPoints.idxmax()
        if worst not in keep and x.playerPoints[worst] >= 6:
            keep.append(worst)
        rows = [[r.familyNameDef, round(r.partialPossessions, 1), int(r.playerPoints), int(r.matchupFieldGoalsMade),
                 int(r.matchupFieldGoalsAttempted), int(r.personIdDef)] for r in x.loc[keep].itertuples()]
        rest = x.drop(keep)
        if len(rest):
            rows.append(["Others", round(rest.partialPossessions.sum(), 1), int(rest.playerPoints.sum()),
                         int(rest.matchupFieldGoalsMade.sum()), int(rest.matchupFieldGoalsAttempted.sum()), 0])
        out.append([f"{star.firstName} {star.familyName}", int(star.points), rows])
    return out or None


def tracking(teams: pd.DataFrame, players: pd.DataFrame, available: pd.DataFrame, opp_tri: str) -> dict | None:
    if teams.empty or (not available.empty and int(available.ptAvailable.iloc[0]) == 0) or teams.touches.sum() == 0:
        return None
    t = {r.teamTricode: r for r in teams.itertuples()}
    c, o = t[TRI], t[opp_tri]

    def made(r, m, a):
        return f"{int(getattr(r, m))}-{int(getattr(r, a))}", (100 * getattr(r, m) / getattr(r, a) if getattr(r, a) else 0)

    rows = []
    for label, m, a, hi in (("Uncontested FG", "uncontestedFieldGoalsMade", "uncontestedFieldGoalsAttempted", 1),
                            ("Contested FG", "contestedFieldGoalsMade", "contestedFieldGoalsAttempted", 1),
                            ("Opponent FG at rim when defending", "defendedAtRimFieldGoalsMade", "defendedAtRimFieldGoalsAttempted", 0)):
        (cl, cp), (ol, op) = made(c, m, a), made(o, m, a)
        rows.append([label, f"{cl} ({cp:.1f}%)", f"({op:.1f}%) {ol}", round(cp, 1), round(op, 1), hi])
    for label, col in (("Touches", "touches"), ("Passes", "passes"), ("Secondary assists", "secondaryAssists"),
                       ("Free throw assists", "freeThrowAssists"), ("Rebound chances", "reboundChancesTotal")):
        rows.append([label, str(int(getattr(c, col))), str(int(getattr(o, col))), int(getattr(c, col)), int(getattr(o, col)), 1])
    rows.append(["Miles run", f"{c.distance:.1f}", f"{o.distance:.1f}", float(c.distance), float(o.distance), 1])
    p = players[(players.teamTricode == TRI) & (players.touches > 0)].sort_values("touches", ascending=False)
    prow = [[r.familyName, int(r.touches), int(r.passes), f"{int(r.uncontestedFieldGoalsMade)}-{int(r.uncontestedFieldGoalsAttempted)}",
             f"{int(r.contestedFieldGoalsMade)}-{int(r.contestedFieldGoalsAttempted)}",
             f"{int(r.defendedAtRimFieldGoalsMade)}-{int(r.defendedAtRimFieldGoalsAttempted)}", round(float(r.distance), 2)] for r in p.itertuples()]
    tracked = int(c.contestedFieldGoalsAttempted + c.uncontestedFieldGoalsAttempted)
    return {"rows": rows, "players": prow, "tracked_fga": tracked}


def scoring(teams: pd.DataFrame, players: pd.DataFrame, box_players: pd.DataFrame, opp_tri: str) -> dict | None:
    if teams.empty or players.empty:
        return None
    t = {r.teamTricode: r for r in teams.itertuples()}

    def shares(r):
        return [round(100 * r.percentagePointsPaint, 1), round(100 * r.percentagePointsMidrange2pt, 1),
                round(100 * r.percentagePoints3pt, 1), round(100 * r.percentagePointsFreeThrow, 1)]

    c, o = t[TRI], t[opp_tri]
    sp = players[players.teamTricode == TRI].merge(box_players[["personId", "fieldGoalsMade"]], on="personId")
    sp["unassisted"] = (sp.percentageUnassistedFGM * sp.fieldGoalsMade).round().astype(int)
    sp = sp[sp.fieldGoalsMade > 0].sort_values(["fieldGoalsMade", "unassisted"], ascending=False)
    return {"shares": [shares(c), shares(o)],
            "fastbreak": [round(100 * c.percentagePointsFastBreak), round(100 * o.percentagePointsFastBreak)],
            "off_to": [round(100 * c.percentagePointsOffTurnovers), round(100 * o.percentagePointsOffTurnovers)],
            "assisted": [["All field goals", round(100 * c.percentageAssistedFGM, 1), round(100 * o.percentageAssistedFGM, 1)],
                         ["2-pointers", round(100 * c.percentageAssisted2pt, 1), round(100 * o.percentageAssisted2pt, 1)],
                         ["3-pointers", round(100 * c.percentageAssisted3pt, 1), round(100 * o.percentageAssisted3pt, 1)]],
            "unassisted": [[r.familyName, int(r.fieldGoalsMade), int(r.unassisted)] for r in sp.itertuples()]}


def leaders(players: pd.DataFrame, opp_tri: str) -> list:
    p = players[players.minutes.map(minutes).gt(0)]
    rows = []
    for label, col in (("Points", "points"), ("Rebounds", "reboundsTotal"), ("Assists", "assists")):
        row = [label]
        for tri in (TRI, opp_tri):
            q = p[p.teamTricode == tri]
            best = q[col].max()
            top = q[q[col] == best]
            names = top.familyName.tolist()
            shown = ", ".join(names[:2]) + (f" +{len(names) - 2}" if len(names) > 2 else "")
            row.append([shown, str(int(best)), [int(i) for i in top.personId[:2]]])
        rows.append(row)
    return rows


SEASON_STATS = (("Points", "PTS"), ("Rebounds", "REB"), ("Assists", "AST"), ("Steals", "STL"), ("Blocks", "BLK"),
                ("3-pointers made", "FG3M"))
# The leaders grid's shooting column, from summed makes and attempts, never an average of game percentages.
# Below MIN_FGA field-goal attempts per game played it is a hyphen: 1-for-1 is not a leader. The user chose
# plain FG% (2026-10-12) over eFG% and TS%: familiar, and every shot counts as one; centers leading is accepted.
EFFICIENCY = "FG%"
MIN_FGA = 5


def season_leaders(player_games: pd.DataFrame, game_id: str) -> dict | None:
    if player_games.empty:
        return None
    player_games = player_games[player_games.TEAM_ID == BULLS]
    # Regular season: from game 5, before which per-game averages are just a few box scores. Preseason: from
    # game 1 (user, 2026-10-09: the slide can be left out of a post when one game says too little).
    tonight = player_games.loc[player_games.GAME_ID.astype(str).str.zfill(10) == game_id, "GAME_DATE"].max()
    if game_id[:3] == "002" and player_games[player_games.GAME_DATE <= tonight].GAME_ID.nunique() < 5:
        return None
    g = player_games.assign(gid=player_games.GAME_ID.astype(str).str.zfill(10))
    b = g[g.GAME_DATE <= g.loc[g.gid == game_id, "GAME_DATE"].iloc[0]]
    games = int(b.gid.nunique())
    need = math.ceil(0.5 * games)
    cols = [c for _, c in SEASON_STATS]
    keys = ["PLAYER_ID", "PLAYER_NAME"]
    x = b.groupby(keys)[cols].mean().round(1)
    x["gp"] = b.groupby(keys).size()
    t = b.groupby(keys)[["PTS", "FGM", "FG3M", "FGA", "FTA"]].sum()
    pct = {"TS%": t.PTS / (2 * (t.FGA + 0.44 * t.FTA)), "eFG%": (t.FGM + 0.5 * t.FG3M) / t.FGA,
           "FG%": t.FGM / t.FGA}[EFFICIENCY]
    x["eff"] = (100 * pct).round(1).where(t.FGA >= MIN_FGA * x.gp)
    x = x[x.gp >= need].reset_index()
    x = x.assign(last=x.PLAYER_NAME.str.split(" ", n=1).str[-1]).sort_values(["PTS", "last"], ascending=[False, True])
    rows = [[int(r.PLAYER_ID), r.PLAYER_NAME, *[float(getattr(r, c)) for c in cols],
             None if pd.isna(r.eff) else float(r.eff), int(r.gp)] for r in x.itertuples()]
    heads = ["3PM" if c == "FG3M" else c for c in cols] + [EFFICIENCY]
    return {"columns": heads, "rows": rows, "qualify": need, "games": games, "min_fga": MIN_FGA}


# Player stats worth a callout, with the floor below which a season high is not news.
PLAYER_NOTABLE = (("PTS", "points", 15), ("REB", "rebounds", 8), ("AST", "assists", 6), ("FG3M", "3-pointers", 3),
                  ("STL", "steals", 3), ("BLK", "blocks", 3))
TEAM_NOTABLE = (("PTS", "points"), ("AST", "assists"), ("FG3M", "3-pointers"), ("REB", "rebounds"),
                ("STL", "steals"), ("BLK", "blocks"))


def season_notables(game_id: str, player_games: pd.DataFrame, team_games: pd.DataFrame, league_games: pd.DataFrame,
                    opp_tri: str) -> list:
    """Exact, positive callouts against this season so far, as (priority, order, family, text).

    League ranks compare tonight with every NBA team game this season so far (counted once 150
    team games exist). Bulls and player season highs need 10 earlier Bulls games, and 5 earlier
    games for the player (any team, so a traded player's earlier games count). Ties say "tied".
    Regular season only.
    """
    if game_id[:3] != "002" or player_games.empty or team_games.empty:
        return []
    TEAM = team_games.TEAM_NAME.iloc[0].split()[-1] if "TEAM_NAME" in team_games else "Bulls"
    own = TEAM + ("'" if TEAM.endswith("s") else "'s")
    tg = team_games.assign(gid=team_games.GAME_ID.astype(str).str.zfill(10))
    me = tg[tg.gid == game_id].iloc[0]
    before = tg[tg.GAME_DATE < me.GAME_DATE]
    lg = league_games[league_games.GAME_DATE <= me.GAME_DATE] if not league_games.empty else league_games
    out = []

    def place(n):
        return "most" if n == 1 else f"{ord_(n)}-most"

    for col, word in TEAM_NOTABLE:
        v = int(me[col])
        if len(lg) >= 150:
            higher, equal = int((lg[col] > v).sum()), int((lg[col] == v).sum())
            if higher < 3:
                tied = "tied for " if equal > 1 else ""
                out.append((0, 0, col, f"{v} {word}: {tied}{place(higher + 1)} by any NBA team this season"))
                continue
        if len(before) >= 10 and v >= before[col].max():
            tied = v == before[col].max()
            out.append((1, 0, col, f"{v} {word}: {'tied for ' if tied else ''}the {own} most this season"))
    margin = int(me.PLUS_MINUS)
    if margin > 0 and len(before) >= 10 and margin >= before.PLUS_MINUS.max():
        out.append((1, 0, "MARGIN", f"{sgn_(margin)} win: {'tied for ' if margin == before.PLUS_MINUS.max() else ''}the {own} biggest this season"))
    allowed = int(me.PTS - me.PLUS_MINUS)
    if len(before) >= 10 and allowed <= (before.PTS - before.PLUS_MINUS).min():
        low = (before.PTS - before.PLUS_MINUS).min()
        out.append((1, 0, "ALLOWED", f"Held {opp_tri} to {allowed}: {'tied for ' if allowed == low else ''}the fewest the {TEAM} have allowed this season"))

    # Players: season highs, counting every game this season on any team.
    pg = player_games.assign(gid=player_games.GAME_ID.astype(str).str.zfill(10))
    tonight = pg[(pg.gid == game_id) & (pg.TEAM_ID == BULLS)]
    for r in tonight.itertuples():
        prior = pg[(pg.PLAYER_ID == r.PLAYER_ID) & (pg.GAME_DATE < r.GAME_DATE)]
        if len(prior) < 5:
            continue
        name = r.PLAYER_NAME.split(" ", 1)[-1]
        hits = []  # (stat order, value, "15 rebounds", tied?)
        for k, (col, word, floor) in enumerate(PLAYER_NOTABLE):
            v, best = int(getattr(r, col)), int(prior[col].max())
            if v >= floor and v >= best:
                hits.append((k, v, f"{v} {word}", v == best))
        if not hits:
            continue
        if len(hits) == 1:
            k, v, what, tied = hits[0]
            out.append((2 + k / 10, -v, "player", f"{name}: {what}, {'tying his season high' if tied else 'his most this season'}"))
        elif all(not h[3] for h in hits) or all(h[3] for h in hits):
            k, v = hits[0][0], hits[0][1]
            what = " and ".join(h[2] for h in hits[:2])
            out.append((2 + k / 10, -v, "player", f"{name}: {what}, both {'tying his season highs' if hits[0][3] else 'his most this season'}"))
        else:
            k, v = hits[0][0], hits[0][1]
            parts = [f"{what}, {'tying his season high' if tied else 'his most this season'}" for _, _, what, tied in hits[:2]]
            out.append((2 + k / 10, -v, "player", f"{name}: {parts[0]}, and {parts[1]}"))
    return out


def league_team_games() -> pd.DataFrame:
    """Every 2025-26 regular-season team game, the qualifier tables' reference."""
    return with_opponent(pd.read_csv(BASELINES / f"league-{BASELINE_SEASON}" / f"league_teamgames_{BASELINE_SEASON}.csv.gz"))


def with_opponent(games: pd.DataFrame) -> pd.DataFrame:
    """Each team-game row with its opponent's makes and attempts beside it (FGM_OPP, FGA_OPP)."""
    both = games.merge(games[["GAME_ID", "TEAM_ID", "FGM", "FGA"]], on="GAME_ID", suffixes=("", "_OPP"))
    return both[both.TEAM_ID != both.TEAM_ID_OPP]


# Notable qualifiers (Notion "Game recaps", Notable qualifiers): a Bulls team stat in the top 5% of 2025-26 team
# games. (key, family, value, higher is better, eligible, text); percentages compare at their printed 0.1%.
QUALIFIERS = (
    ("assist_rate", "AST", lambda r: r.AST / r.FGM, True, None, lambda r, team, opp: f"{team}: {r.AST} assists on {r.FGM} field goals"),
    ("threes", "FG3M", lambda r: r.FG3M, True, None, lambda r, team, opp: f"{team}: {r.FG3M} threes"),
    ("three_pct", "FG3M", lambda r: np.round(r.FG3M / r.FG3A, 3), True, lambda r: r.FG3A >= 30,
     lambda r, team, opp: f"{team}: {r.FG3M}-{r.FG3A} from three ({100 * r.FG3M / r.FG3A:.1f}%)"),
    ("fg_pct", "FG", lambda r: np.round(r.FGM / r.FGA, 3), True, None,
     lambda r, team, opp: f"{team}: {100 * r.FGM / r.FGA:.1f}% shooting ({r.FGM}-{r.FGA})"),
    ("points", "PTS", lambda r: r.PTS, True, None, lambda r, team, opp: f"{team}: {r.PTS} points"),
    ("steals", "STL", lambda r: r.STL, True, None, lambda r, team, opp: f"{team}: {r.STL} steals"),
    ("blocks", "BLK", lambda r: r.BLK, True, None, lambda r, team, opp: f"{team}: {r.BLK} blocks"),
    ("offensive_rebounds", "OREB", lambda r: r.OREB, True, None, lambda r, team, opp: f"{team}: {r.OREB} offensive rebounds"),
    ("turnovers", "TOV", lambda r: r.TOV, False, None, lambda r, team, opp: f"{team}: {r.TOV} turnovers"),
    ("opp_fg_pct", "FG_OPP", lambda r: np.round(r.FGM_OPP / r.FGA_OPP, 3), False, None,
     lambda r, team, opp: f"{team}: held {opp} to {100 * r.FGM_OPP / r.FGA_OPP:.1f}% shooting"),
)


def qualifier_floors(base: pd.DataFrame) -> dict:
    """Each qualifier's printed floor: the least extreme value still in the top 5% of the reference games."""
    floors = {}
    for key, _, value, high, eligible, _ in QUALIFIERS:
        v = value(base[eligible(base)] if eligible else base)
        ok = sorted({x for x in v if ((v >= x) if high else (v <= x)).mean() <= 0.05})
        floors[key] = ok[0] if high else ok[-1]
    return floors


def tonight_line(game_id: str, league_games: pd.DataFrame, teams: pd.DataFrame, stats: pd.DataFrame) -> pd.Series | None:
    """Tonight's Bulls row from the game log, the same table as the reference games, or None unless every
    count the qualifiers read equals the box score (turnovers: the summary's total, team turnovers included)."""
    if league_games.empty or stats.empty:
        return None
    rows = with_opponent(league_games[league_games.GAME_ID.astype(str).str.zfill(10) == game_id])
    me = rows[rows.TEAM_ID == BULLS]
    if len(me) != 1:
        return None
    me = me.iloc[0]
    box = teams.set_index("teamId")
    tov = stats.set_index("teamId").turnoversTotal
    opp = int(me.TEAM_ID_OPP)
    pairs = {"FGM": "fieldGoalsMade", "FGA": "fieldGoalsAttempted", "FG3M": "threePointersMade",
             "FG3A": "threePointersAttempted", "OREB": "reboundsOffensive", "AST": "assists", "STL": "steals",
             "BLK": "blocks", "PTS": "points"}
    same = all(int(me[c]) == int(box.loc[BULLS, b]) for c, b in pairs.items())
    same &= int(me.TOV) == int(tov[BULLS])
    same &= int(me.FGM_OPP) == int(box.loc[opp, "fieldGoalsMade"]) and int(me.FGA_OPP) == int(box.loc[opp, "fieldGoalsAttempted"])
    return pd.Series({c: int(me[c]) for c in [*pairs, "TOV", "FGM_OPP", "FGA_OPP"]}) if same else None


def team_qualifiers(me: pd.Series | None, base: pd.DataFrame, team: str, opp_tri: str) -> list:
    """(share of reference games at or beyond tonight, key, family, text) for each stat in their top 5%."""
    if me is None:
        return []
    out = []
    for key, family, value, high, eligible, text in QUALIFIERS:
        if eligible and not eligible(me):
            continue
        ref = value(base[eligible(base)] if eligible else base)
        v = value(me)
        share = float(((ref >= v) if high else (ref <= v)).mean())
        if share <= 0.05:
            pct = math.ceil(round(share * 100, 6))
            rank = f"top {max(pct, 1)}% of NBA games last season" if share else "a mark no NBA team reached last season"
            out.append((share, key, family, f"{text(me, team, opp_tri)}, {rank}"))
    return out


def assisted_makes(pbp: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame | None:
    """The Bulls' made field goals with the passer's personId (NaN when unassisted), or None unless they
    reconcile with the box score's makes and assists. PlayByPlayV3 names the passer only in the shot's text,
    "(Giddey 3 AST)", by family name, sometimes without accents."""
    chi = players[players.teamId == BULLS]
    names = chi.familyName.map(fold)
    if names.duplicated().any():
        return None
    by_name = dict(zip(names, chi.personId))
    made = pbp[(pbp.teamId == BULLS) & (pbp.isFieldGoal == 1) & (pbp.shotResult == "Made")]
    named = made.description.str.extract(r"\(([^()]+?) \d+ AST\)")[0]
    passer = named.map(lambda n: by_name.get(fold(n), -1) if isinstance(n, str) else np.nan)
    if (passer == -1).any() or len(made) != int(chi.fieldGoalsMade.sum()) or passer.notna().sum() != int(chi.assists.sum()):
        return None
    return made.assign(passer=passer)


def top_connection(made: pd.DataFrame | None, players: pd.DataFrame, floor: int = 5) -> str | None:
    """'Giddey to Buzelis: 6 assists' when one passer-to-scorer pair alone leads with at least `floor`."""
    if made is None:
        return None
    pairs = made.dropna(subset=["passer"]).groupby(["passer", "personId"]).size().sort_values(ascending=False)
    if pairs.empty or pairs.iloc[0] < floor or (len(pairs) > 1 and pairs.iloc[1] == pairs.iloc[0]):
        return None
    family = players.set_index("personId").familyName
    (passer, scorer), n = pairs.index[0], int(pairs.iloc[0])
    return f"{family[int(passer)]} to {family[int(scorer)]}: {n} assists"


def notables(picked: dict, season: list, qualifiers: list, connection: str | None, limit: int = 3) -> list:
    """Up to three callouts: the user's picks ({key: text}; a pick that also qualifies gets the qualifier's
    wording), this season's ranks, then the qualifiers rarest first (one per family, none a season notable
    already covers), then the top assist connection."""
    found = {key: text for _, key, _, text in qualifiers}
    picked = [found.get(key, text) for key, text in picked.items()]
    used = {family for _, _, family, _ in season}
    ranked = list(season)
    for share, key, family, text in sorted(qualifiers):
        if text not in picked and family not in used:
            used.add(family)
            ranked.append((1.5, share, family, text))
    if connection:
        ranked.append((3, 0, "connection", connection))
    ranked.sort(key=lambda x: (x[0], x[1]))
    return (picked + [text for *_, text in ranked])[:limit]


def team_dunks(chi, pbp: pd.DataFrame, names: int = 3) -> str | None:
    """'Bulls: 15 team dunks, led by Buzelis (4), Wilson (3), Sellers (3)': made dunks by the most prolific,
    ties in the order of their first dunk; None without a dunk. Two Bulls sharing a family name show as 'C. Wilson'."""
    bulls = pbp[pbp.teamId == BULLS]
    made = bulls[(bulls.isFieldGoal == 1) & (bulls.shotResult == "Made") & bulls.subType.str.contains("Dunk", na=False)]
    if made.empty:
        return None
    people = bulls.drop_duplicates("personId").set_index("personId")
    shared = people.playerName.duplicated(keep=False)
    label = people.playerNameI.where(shared, people.playerName)
    by = made.groupby("personId", sort=False).size().sort_values(ascending=False, kind="stable")
    top = ", ".join(f"{label[pid]} ({n})" for pid, n in by.head(names).items())
    return f"{chi.teamName}: {len(made)} team dunks, led by {top}"


PICKED_NOTABLES = {
    "assist_rate": lambda chi, pbp: f"{chi.teamName}: {int(chi.assists)} assists on {int(chi.fieldGoalsMade)} field goals",
    "dunks": team_dunks,
}


def picked_notables(chi, pbp: pd.DataFrame, names: list) -> dict:
    unknown = [n for n in names if n not in PICKED_NOTABLES]
    if unknown:
        raise ValueError(f"picks.json notables {unknown} are not in {sorted(PICKED_NOTABLES)}")
    texts = {n: PICKED_NOTABLES[n](chi, pbp) for n in names}
    return {n: t for n, t in texts.items() if t is not None}


def ord_(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def sgn_(v: int) -> str:
    return f"+{v}" if v > 0 else str(v)


def record_of(row) -> str | None:
    return f"{int(row.teamWins)}-{int(row.teamLosses)}" if row is not None else None


def as_of(g: Path, date: pd.Timestamp) -> str:
    """When the box score behind these numbers was captured, in Chicago time, for the slide footer. NBA.com
    revises official stats after games (fast break points most often), so the slides say which moment they
    show. The date is added only when the capture was not on game day (a rebuild, a test game)."""
    sources = g / "sources.json"
    stamp = json.loads(sources.read_text())["files"].get("teams.csv", {}).get("captured_utc") if sources.exists() else None
    when = (pd.Timestamp(stamp) if stamp else pd.Timestamp((g / "teams.csv").stat().st_mtime, unit="s", tz="UTC")).tz_convert("America/Chicago")
    clock = when.strftime("%-I:%M %p").lower().replace("am", "a.m.").replace("pm", "p.m.") + " CT"
    return clock if when.date() == date.date() else f"{when.strftime('%b %-d')}, {clock}"


def build(game_id: str) -> dict:
    g = game_dir(game_id)
    (g / "shots_chi_pbp.csv").unlink(missing_ok=True)  # only this build's fallback may feed the zones chart
    teams, players, pbp = read(g, "teams.csv"), read(g, "players.csv"), read(g, "pbp.csv")
    lines, info, arena = read(g, "summary_linescore.csv"), read(g, "summary_info.csv"), read(g, "summary_arena.csv")
    game = read(g, "summary_game.csv")
    global TRI
    opp = teams[teams.teamId != BULLS].iloc[0]
    chi = teams[teams.teamId == BULLS].iloc[0]
    TRI = chi.teamTricode
    opp_tri = opp.teamTricode
    chi_home = int(game.homeTeamId.iloc[0]) == BULLS

    ls = {int(r.teamId): r for r in lines.itertuples()}
    periods = int(pbp.period.max())
    q = scoring_events(pbp, chi_home).groupby("period")[["chi", "opp"]].max()
    q = q.diff().fillna(q).astype(int)
    if int(q.chi.sum()) != int(chi.points) or int(q.opp.sum()) != int(opp.points):
        # The play-by-play and the box score are separate cached requests; one can trail the other.
        raise NotReady("play-by-play does not yet reach the box score's final score")
    # Check the play-by-play against NBA's official line score, quarter by quarter. A feed published
    # out of order (seen 2026-10-06, DEN at UTA) still sums to the final, so the sum alone is not enough.
    official_q = {int(r.teamId): [int(getattr(r, f"period{i}Score")) for i in range(1, 5)] for r in lines.itertuples()}
    pbp_ok = ([int(q.chi.get(i, 0)) for i in range(1, 5)] == official_q.get(BULLS)
              and [int(q.opp.get(i, 0)) for i in range(1, 5)] == official_q.get(int(opp.teamId)))
    steps, repairs = score_steps(pbp), []
    if pbp_ok and steps:
        pbp, changed = repair_scores(pbp)
        steps = score_steps(pbp)
        repairs.append(f"play-by-play: running score recomputed from the plays on {changed} rows NBA.com printed "
                       "wrong; the final, the quarter scores and NBA.com's game-flow counts match")
    if not pbp_ok or steps:
        raise NotReady("play-by-play does not match NBA.com's line score" if not pbp_ok
                       else f"play-by-play score steps are off at {len(steps)} rows, first {steps[0]}")
    stale = logs_match(game_id, players, teams, read(g, "player_games.csv"), read(g, "league_games.csv"))
    if stale:
        raise NotReady("game logs do not yet match the final box score: " + "; ".join(stale))
    ff = read(g, "ff_team.csv")
    split, short = ([], "") if EARLY else (feeds_agree(players, teams, ff), ff_minutes_short(ff, teams))
    from_box = bool(split) and bool(short) and all("four factors" in m for m in split) and FALLBACK
    if from_box:
        repairs.append(f"four factors: NBA.com's cover {short}; EFG% and FT rate computed from the box score, "
                       "TOV% and OREB% left out")
    elif split:
        raise NotReady("box-score feeds disagree: " + "; ".join(split) + (f" (NBA.com's four factors cover {short})" if short else ""))
    date = pd.Timestamp(info.gameDate.iloc[0])
    result = "W" if chi.points > opp.points else "L"
    kind = SEASON_TYPES[game_id[:3]]
    rec = ls.get(BULLS)
    record = (f"{chi.teamName} {'improve' if result == 'W' else 'fall'} to {int(rec.teamWins)}-{int(rec.teamLosses)}"
              if game_id[:3] == "002" and rec is not None else kind)
    raw = read(g, "shots_raw_chi.csv")
    available = read(g, "summary_availability.csv")
    # The shot feed must hold every field goal attempt in the box score (MIN at MIA, 2026-10-10: 72 of 87, and
    # the shot chart printed a partial game's eFG% before Claude's review caught it). Past the deadline the
    # play-by-play's shots replace it (shots_from_pbp: they must number exactly the box score's attempts), written
    # to shots_chi_pbp.csv for the zones chart; otherwise the shot chart is left out and no award reads the feed.
    fga, fallback_file = int(chi.fieldGoalsAttempted), g / "shots_chi_pbp.csv"
    shots_complete, shots_source = len(raw) == fga, "nba"
    if not shots_complete and not FALLBACK and not EARLY:
        raise NotReady(f"Bulls shots feed has {len(raw)} of {fga} field goal attempts")
    if not shots_complete and not EARLY:
        from_pbp = shots_from_pbp(pbp, BULLS)
        if len(from_pbp) == fga:
            raw, shots_complete, shots_source = from_pbp, True, "pbp"
            pd.DataFrame({"loc_x": raw.LOC_X, "loc_y": raw.LOC_Y, "shot_made": raw.SHOT_MADE_FLAG == 1,
                          "shot_type": raw.SHOT_TYPE.str[:3], "shot_distance": raw.SHOT_DISTANCE, "game_id": raw.GAME_ID,
                          "player_id": raw.PLAYER_ID, "player_name": raw.PLAYER_NAME}).to_csv(fallback_file, index=False)
            repairs.append(f"shot chart from the play-by-play: NBA.com's shot feed has {len(read(g, 'shots_raw_chi.csv'))} "
                           f"of {fga} attempts, the play-by-play all {fga}; zones placed by shot location")
        else:
            repairs.append(f"shot chart left out: NBA.com's shot feed has {len(raw)} of {fga} attempts, the play-by-play {len(from_pbp)}")
            raw = raw.iloc[0:0]

    starter_ids = starters(players, pbp)
    pick = picks(g)
    made = assisted_makes(pbp, players)
    if made is None:
        repairs.append("assist detail left out: the play-by-play's assists do not reconcile with the box score")
    data = {
        "game_id": game_id, "kind": kind, "season_label": f"{2000 + int(game_id[3:5])}-{int(game_id[3:5]) + 1:02d}", "result": result, "home": chi_home,
        "date_label": date.strftime("%a, %b %-d, %Y").upper(),
        "date_short": date.strftime("%b %-d, %Y"),
        "as_of": as_of(g, date),
        "venue": f"{arena.arenaName.iloc[0]}, {arena.arenaCity.iloc[0]}".upper() if not arena.empty else "",
        "arena": arena.arenaName.iloc[0] if not arena.empty else "",
        "chi": {"name": chi.teamName.upper(), "team": chi.teamName, "city": chi.teamCity, "tri": TRI,
                "score": int(chi.points), "record": record_of(ls.get(BULLS))},
        "opp": {"name": opp.teamName.upper(), "tri": opp_tri, "city": opp.teamCity, "team": opp.teamName, "score": int(opp.points),
                "record": record_of(ls.get(int(opp.teamId)))},
        "record_line": record,
        "quarters": {"labels": [period_label(i) for i in range(1, periods + 1)],
                     "chi": [int(q.chi.get(i, 0)) for i in range(1, periods + 1)],
                     "opp": [int(q.opp.get(i, 0)) for i in range(1, periods + 1)]},
        "pbp_ok": bool(pbp_ok),
        "flow": flow(pbp, chi_home, opp_tri, pick.get("moments", [])),
        "four_factors": None if EARLY else four_factors(ff, teams, opp_tri, from_box),
        "h2h": None if EARLY else head_to_head(teams, read(g, "misc_teams.csv"), read(g, "summary_stats.csv"), opp_tri),
        "box": box(players, read(g, "roster.csv", dtype={"NUM": str}), starter_ids, str(chi.minutes)),
        "shooting": {"fgm": int(chi.fieldGoalsMade), "fga": int(chi.fieldGoalsAttempted),
                     "tpm": int(chi.threePointersMade), "tpa": int(chi.threePointersAttempted)},
        "shot_types": shot_types(raw),
        "season": season(bulls_games(read(g, "league_games.csv")), read(g, "schedule.csv"), read(g, "league_games.csv"), game_id),
        "breakdown": breakdown(pbp, teams, opp_tri),
        "awards": [] if EARLY else awards(players, raw, pbp, chi_home, starter_ids, pick),
        "pending": LATE_PAGES if EARLY else [],
        "scatter": scatter(read(g, "advanced_players.csv"), opp_tri),
        "league_rating": round(acc.V * 100, 1),
        "matchups": matchups(read(g, "matchups.csv"), players, opp_tri),
        "tracking": tracking(read(g, "track_teams.csv"), read(g, "track_players.csv"), available, opp_tri),
        "scoring": scoring(read(g, "scoring_teams.csv"), read(g, "scoring_players.csv"), players[players.teamId == BULLS], opp_tri),
        "leaders": leaders(players, opp_tri),
        "season_leaders": season_leaders(read(g, "player_games.csv"), game_id),
        "notables": notables(
            picked_notables(chi, pbp, pick.get("notables", [])),
            season_notables(game_id, read(g, "player_games.csv"), bulls_games(read(g, "league_games.csv")), read(g, "league_games.csv"), opp_tri),
            team_qualifiers(tonight_line(game_id, read(g, "league_games.csv"), teams, read(g, "summary_stats.csv")),
                            league_team_games(), chi.teamName, opp_tri),
            top_connection(made, players)),
        "assisted": None if made is None else [int(made.passer.notna().sum()), len(made)],
        "missing": [line for line in (g / "missing.txt").read_text().splitlines() if line] if (g / "missing.txt").exists() else [],
        "shots_complete": shots_complete, "shots_source": shots_source,
        "repairs": repairs,
    }
    stats = read(g, "summary_stats.csv")
    if not stats.empty:
        s = stats.set_index("teamTricode")
        nba = {"lead_changes": int(s.leadChanges.iloc[0]), "ties": int(s.timesTied.iloc[0]),
               "chi_lead": int(s.loc[TRI, "biggestLead"]), "opp_lead": int(s.loc[opp_tri, "biggestLead"]),
               "run_chi": int(s.loc[TRI, "biggestScoringRun"]), "run_opp": int(s.loc[opp_tri, "biggestScoringRun"])}
        ours = {k: data["flow"][k] for k in nba}
        data["flow"]["nba_check"], note = compare_flow(ours, nba, data["chi"]["score"] - data["opp"]["score"])
        if note:
            data["flow"]["nba_note"] = note
    if data["flow"].get("nba_check") != "match":
        raise NotReady(f"game flow does not match NBA.com's own counts ({data['flow'].get('nba_check', 'no NBA counts published')})")
    return data


def main(game_ids: list[str]) -> None:
    for game_id in game_ids:
        try:
            data = build(game_id)
        except NotReady as e:
            print(f"{game_id}: not ready: {e}", flush=True)
            sys.exit(NOT_READY)
        out = OUTPUT / game_id / "recap.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, default=lambda x: x.item() if hasattr(x, "item") else str(x)))
        skipped = [k for k in ("matchups", "tracking", "scoring") if data[k] is None]
        print(f"{game_id}{' (early pages)' if EARLY else ''}: {data['chi']['score']}-{data['opp']['score']} vs {data['opp']['tri']}, "
              f"flow check {data['flow'].get('nba_check')}, awards {len(data['awards'] or [])}, "
              f"skipped pages {skipped or 'none'}, missing feeds {data['missing'] or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1:])
