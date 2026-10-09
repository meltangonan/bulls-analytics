"""Exact four-factor accounting of one game's margin from play-by-play.

Every possession starts worth V (league points per possession). Each event moves
the possession's value; the move is booked to the factor that caused it. The
moves over a team's possessions add up to PTS - V * possessions exactly.
"""
import re
from pathlib import Path
import pandas as pd

LEAGUE = Path(__file__).resolve().parents[1] / "baselines" / "league-2025-26"
lg = pd.read_csv(LEAGUE / "league_teamgames_2025-26.csv.gz", dtype={"GAME_ID": str})
adv = pd.read_csv(LEAGUE / "league_advanced_2025-26.csv.gz", dtype={"GAME_ID": str})
V = lg.PTS.sum() / adv.POSS.sum()
ff = pd.read_csv(LEAGUE / "league_four_factors_2025-26.csv.gz", dtype={"GAME_ID": str})
# Official OREB% (team rebounds included), weighted by possessions. The two tables are joined on game and team:
# they do not come back in the same row order (found 2026-10-09; the row-wise product gave 0.3027, not 0.3023).
_joined = ff.merge(adv[["GAME_ID", "TEAM_ID", "POSS"]], on=["GAME_ID", "TEAM_ID"])
P = (_joined.OREB_PCT * _joined.POSS).sum() / _joined.POSS.sum()

def account(pbp, TEAMS, split=None):
    """split, if given, collects each team's shooting value by shot value: split[team][2 or 3]."""
    cats = {t: dict(shoot=0.0, tov=0.0, reb=0.0, ft=0.0, other=0.0) for t in TEAMS.values()}
    N = {t: 0 for t in TEAMS.values()}
    pts = {t: 0 for t in TEAMS.values()}
    st = {"off": None, "s": 0.0, "trip": False}
    def team_of(r):
        if isinstance(r.teamTricode, str):
            return r.teamTricode
        return TEAMS.get(int(r.personId)) if pd.notna(r.personId) else None
    def own(x):
        if st["off"] != x:
            if st["off"] is not None and st["s"]:
                cats[st["off"]]["other"] -= st["s"]
            st["off"], st["s"] = x, V
            N[x] += 1
    for r in pbp.itertuples():
        a, x = r.actionType, team_of(r)
        if st["trip"] and a in ("Made Shot", "Missed Shot", "Turnover"):
            # A trip cut short (lane violation, jump ball) never logs its last free throw.
            st["trip"] = False
            if x == st["off"]:
                cats[x]["other"] += V; st["s"] = V
            else:
                st["s"] = 0.0
        if a == "period":
            if st["off"] is not None and st["s"] and not st["trip"]:
                cats[st["off"]]["other"] -= st["s"]
            st.update(off=None, s=0.0, trip=False)
        elif a == "Made Shot":
            own(x); v = int(r.shotValue); pts[x] += v
            cats[x]["shoot"] += v - st["s"]
            if split is not None: split.setdefault(x, {2: 0.0, 3: 0.0})[v] += v - st["s"]
            st["s"] = 0.0
        elif a == "Missed Shot":
            own(x); cats[x]["shoot"] += P * V - st["s"]
            if split is not None: split.setdefault(x, {2: 0.0, 3: 0.0})[int(r.shotValue)] += P * V - st["s"]
            st["s"] = P * V
        elif a == "Rebound" and st["off"] is not None and not st["trip"]:
            if x == st["off"]:
                cats[x]["reb"] += V - st["s"]; st["s"] = V
            else:
                cats[st["off"]]["reb"] -= st["s"]; st.update(off=None, s=0.0)
        elif a == "Turnover":
            own(x); cats[x]["tov"] -= st["s"]; st.update(off=None, s=0.0)
        elif a == "Free Throw":
            made = 0 if str(r.description).startswith("MISS") else 1
            pts[x] += made; sub = str(r.subType)
            m = re.search(r"(\d) of (\d)", sub)
            if m is None or any(k in sub for k in ("Technical", "Flagrant", "Clear Path")):
                cats[x]["ft"] += made; continue  # bonus free throws: points without a possession
            if not st["trip"]:
                own(x); cats[x]["ft"] -= st["s"]; st["trip"] = True
            cats[x]["ft"] += made
            if m.group(1) == m.group(2):
                st["trip"] = False
                if made:
                    st.update(off=None, s=0.0)
                else:
                    st["s"] = P * V; cats[x]["ft"] += st["s"]
    return cats, N, pts

# Centre each factor on the league's average per possession, so a factor reads "vs. average".
L = adv.POSS.sum()
lg_fgm, lg_fga, lg_3 = lg.FGM.sum(), lg.FGA.sum(), lg.FG3M.sum()
base = dict(shoot=(2 * lg_fgm + lg_3 - lg_fga * V + (lg_fga - lg_fgm) * P * V) / L,
            reb=0.0, tov=-V * lg.TOV.sum() / L, other=0.0)
base["ft"] = -sum(base.values())
# The shooting baseline split by shot value, so 3PT and 2PT each read against the league; they sum to base["shoot"].
lg_3a = lg.FG3A.sum()
base_shot = {3: (3 * lg_3 - lg_3a * V + (lg_3a - lg_3) * P * V) / L,
             2: (2 * (lg_fgm - lg_3) - (lg_fga - lg_3a) * V + ((lg_fga - lg_3a) - (lg_fgm - lg_3)) * P * V) / L}
def centred(cats, N):
    out = {}
    for t in cats:
        out[t] = {k: cats[t][k] - base[k] * N[t] for k in cats[t]}
    return out
