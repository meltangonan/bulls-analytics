"""Recheck a posted recap against NBA.com: list every slide number NBA.com has changed since the post.

    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/recheck.py 0012600030

NBA.com corrects box scores after games. Game 1 (Oct 7) was corrected overnight: a missed shot, a block and an
offensive rebound were added, an assist moved and a dunk was relabelled a layup, which changed numbers on the posted
slides. On Oct 9, three of four dry-run games from the night before had changed fast break points and nothing else.
This compares the feeds saved when the slides were built (the game folder's as-posted/ if present, else the game
folder) with what NBA.com serves now: the box score (minutes included), line score, four factors, misc points,
game-flow counts, and the featured team's shots by zone and by shot type. It reads only; nothing saved is
overwritten. Exit code 0 means no change, 1 means at least one change (listed).
"""
import sys
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import (boxscorefourfactorsv3, boxscoremiscv3, boxscoresummaryv3,
                                     boxscoretraditionalv3, shotchartdetail)

from bulls.data.fetch import _NBA_HEADERS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pull_game import BULLS, SEASON_TYPES, box, season_of  # noqa: E402  the same requests the build uses

from paths import ROOT, game_dir  # noqa: E402
BOX = {"minutes": "minutes", "points": "PTS", "fieldGoalsMade": "FGM", "fieldGoalsAttempted": "FGA", "threePointersMade": "3PM",
       "threePointersAttempted": "3PA", "freeThrowsMade": "FTM", "freeThrowsAttempted": "FTA",
       "reboundsOffensive": "OREB", "reboundsTotal": "REB", "assists": "AST", "steals": "STL", "blocks": "BLK",
       "turnovers": "TO", "plusMinusPoints": "+/-"}
FF = {"effectiveFieldGoalPercentage": "eFG%", "teamTurnoverPercentage": "TOV%",
      "offensiveReboundPercentage": "OREB%", "freeThrowAttemptRate": "FT rate"}
MISC = {"pointsPaint": "points in the paint", "pointsFastBreak": "fast break points",
        "pointsSecondChance": "second chance points", "pointsOffTurnovers": "points off turnovers"}
LINE = {f"period{i}Score": f"Q{i} points" for i in range(1, 5)} | {"score": "final score"}
FLOW = {"leadChanges": "lead changes", "timesTied": "times tied", "biggestLead": "biggest lead",
        "biggestScoringRun": "longest run", "turnoversTotal": "turnovers (with team)"}


def changes(old: pd.DataFrame, new: pd.DataFrame, key: str, cols: dict, who) -> list:
    out = []
    if old.empty or new.empty:
        return [] if old.empty and new.empty else ["a feed is missing on one side; compare by hand"]
    o, n = old.set_index(key), new.set_index(key)
    for k in o.index.union(n.index):
        for c, label in cols.items():
            if c not in o or c not in n:
                continue
            a = o[c].get(k) if k in o.index else None
            b = n[c].get(k) if k in n.index else None
            blank = lambda v: v is None or v == "" or pd.isna(v)  # a DNP's minutes: NaN in the CSV, "" fresh
            if blank(a) and blank(b):
                continue
            if a != b and not (isinstance(a, float) and isinstance(b, float) and round(a, 3) == round(b, 3)):
                out.append(f"{who(o, n, k)} {label}: {a} -> {b}")
    return out


def shot_changes(old: pd.DataFrame, new: pd.DataFrame) -> list:
    """The featured team's shots as the slide counts them: made-attempted in all, by zone and by shot type."""
    if old.empty or new.empty:
        return [] if old.empty and new.empty else ["shots: a feed is missing on one side; compare by hand"]
    count = lambda f, by: {k: (int(v.sum()), len(v)) for k, v in f.groupby(by).SHOT_MADE_FLAG}
    out = [] if (int(old.SHOT_MADE_FLAG.sum()), len(old)) == (int(new.SHOT_MADE_FLAG.sum()), len(new)) else [
        f"shots, all: {int(old.SHOT_MADE_FLAG.sum())}-{len(old)} -> {int(new.SHOT_MADE_FLAG.sum())}-{len(new)}"]
    for by, label in (("SHOT_ZONE_BASIC", "zone"), ("ACTION_TYPE", "shot type")):
        a, b = count(old, by), count(new, by)
        out += [f"shots, {label} {k}: {'-'.join(map(str, a.get(k, (0, 0))))} -> {'-'.join(map(str, b.get(k, (0, 0))))}"
                for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    return out


def main(game_id: str) -> None:
    g = game_dir(game_id)
    saved = g / "as-posted" if (g / "as-posted").exists() else g
    read = lambda name: pd.read_csv(saved / name) if (saved / name).exists() and (saved / name).stat().st_size > 1 else pd.DataFrame()
    kw = dict(game_id=game_id, headers=_NBA_HEADERS, timeout=60)
    team = lambda o, n, k: (o if k in o.index else n).loc[k, "teamTricode"]
    player = lambda o, n, k: f"{(o if k in o.index else n).loc[k, 'familyName']} ({team(o, n, k)})"
    summary = boxscoresummaryv3.BoxScoreSummaryV3(**kw).get_data_frames()
    stats_new = next(f for f in summary if "leadChanges" in f)
    found = (changes(read("teams.csv"), box(boxscoretraditionalv3.BoxScoreTraditionalV3, game_id, 2), "teamId", BOX, team)
             + changes(read("players.csv"), box(boxscoretraditionalv3.BoxScoreTraditionalV3, game_id, 0), "personId", BOX, player)
             + changes(read("ff_team.csv"), box(boxscorefourfactorsv3.BoxScoreFourFactorsV3, game_id, 1), "teamId", FF, team)
             + changes(read("misc_teams.csv"), box(boxscoremiscv3.BoxScoreMiscV3, game_id, 1), "teamId", MISC, team)
             + changes(read("summary_linescore.csv"), summary[4], "teamId", LINE, team)
             + changes(read("summary_stats.csv"), stats_new, "teamId", FLOW, team))
    # Shots joined the as-posted copy on Oct 9; for games posted before that, the game folder's own pull.
    shots = read("shots_raw_chi.csv")
    if shots.empty and (g / "shots_raw_chi.csv").exists():
        shots = pd.read_csv(g / "shots_raw_chi.csv")
    shots_new = shotchartdetail.ShotChartDetail(
        team_id=int(shots.TEAM_ID.iloc[0]) if not shots.empty else BULLS, player_id=0, game_id_nullable=game_id,
        season_nullable=season_of(game_id), season_type_all_star=SEASON_TYPES[game_id[:3]],
        context_measure_simple="FGA", headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
    found += shot_changes(shots, shots_new)
    print(f"{game_id}: compared with {saved.relative_to(ROOT)}")
    print("\n".join(found) if found else "no changes: the posted numbers still match NBA.com")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main(sys.argv[1])
