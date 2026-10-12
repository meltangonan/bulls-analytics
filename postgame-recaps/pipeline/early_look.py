"""A first look at a finished game from the box score on disk, while the slower feeds are still unpublished.

    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/early_look.py <game_id>

The run-postgame-recap skill runs this once the build has pulled the box score (NBA.com publishes it first),
so its updates during the wait can say something real: the result, whether the player rows add up to the team
totals (the build checks this again before any slide is drawn), the leaders, and what changes the layout
(overtime, players used, the longest name). It reads only what pull_game.py saved; nothing here reaches a slide.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recap_data as rd  # noqa: E402
from recap_data import BULLS  # the featured team: FOCUS_TEAM_ID on a dry run  # noqa: E402
from paths import game_dir  # noqa: E402


def look(game_id: str) -> list[str]:
    g = game_dir(game_id)
    players, teams, ff = rd.read(g, "players.csv"), rd.read(g, "teams.csv"), rd.read(g, "ff_team.csv")
    if players.empty or teams.empty or teams.points.fillna(0).sum() == 0:
        return ["box score not pulled yet; run this again after the next poll"]
    chi, opp = teams[teams.teamId == BULLS].iloc[0], teams[teams.teamId != BULLS].iloc[0]
    ot = max(0, (round(rd.minutes(chi.minutes)) - 240) // 25)  # team minutes: 5 players x 48, plus 25 per overtime
    result = "W" if chi.points > opp.points else "L"
    out = [f"{result} {chi.teamTricode} {int(chi.points)}, {opp.teamTricode} {int(opp.points)}" + (f" ({ot}OT)" if ot > 1 else " (OT)" if ot else "")]
    # NBA.com publishes four factors minutes after the box score; until then the file has no columns at all
    wrong = [w for w in rd.feeds_agree(players, teams, ff.reindex(columns=["teamId"]) if ff.empty else ff)
             if "four factors" not in w or not ff.empty]
    out.append("box score: " + ("; ".join(wrong) if wrong else "player rows add up to the team totals"
                                + ("" if ff.empty else ", four factors match")))
    played = players[players.minutes.map(rd.minutes).gt(0)]
    for team, label in ((chi.teamId, chi.teamTricode), (opp.teamId, opp.teamTricode)):
        top = played[played.teamId == team].sort_values("points", ascending=False).head(3 if team == BULLS else 1)
        out.append(f"{label} leaders: " + "; ".join(
            f"{r.familyName} {int(r.points)} pts, {int(r.reboundsTotal)} reb, {int(r.assists)} ast" for r in top.itertuples()))
    bulls = played[played.teamId == BULLS]
    longest = max(bulls.firstName + " " + bulls.familyName, key=len)
    out.append(f"layout: {len(bulls)} {chi.teamTricode} players used (8 to 14 in the saved games); longest name {longest} ({len(longest)} letters)")
    return out


if __name__ == "__main__":
    print("\n".join(look(sys.argv[1])))
