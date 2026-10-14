"""Team ranks mockup data: 2025-26 regular-season team stats (per game) from NBA.com, saved raw, plus ranks.json.

Reuses the saved CSVs when all four and their pulled.txt date are present. Run from the repo root:
    PYTHONPATH=. venv/bin/python postgame-recaps/team-ranks-mock/pull_team_ranks.py
"""
import json, sys, time
import pandas as pd
from pathlib import Path
sys.path.insert(0, ".")
from nba_api.stats.endpoints import leaguedashteamstats
from bulls.data.fetch import _NBA_HEADERS
OUT = Path("postgame-recaps/team-ranks-mock")
MEASURES = ("Base", "Advanced", "Misc", "Four Factors")
SNAPSHOTS = {m: OUT / f"{m.replace(' ', '_').lower()}.csv" for m in MEASURES}
PULLED = OUT / "pulled.txt"
if not PULLED.exists() or not all(f.exists() for f in SNAPSHOTS.values()):
    for m, f in SNAPSHOTS.items():
        leaguedashteamstats.LeagueDashTeamStats(season="2025-26", season_type_all_star="Regular Season",
            measure_type_detailed_defense=m, per_mode_detailed="PerGame", headers=_NBA_HEADERS,
            timeout=60).get_data_frames()[0].to_csv(f, index=False); time.sleep(1)
    PULLED.write_text(time.strftime("%Y-%m-%d") + "\n")
T = {m: pd.read_csv(f).set_index("TEAM_ID") for m, f in SNAPSHOTS.items()}
B = T["Base"]; assert len(B) == 30
# 3PA share is ours (NBA.com has no column): FG3A / FGA, ranked high to low with ties sharing the best rank.
share = (B.FG3A / B.FGA * 100).round(1)
share_rank = share.rank(ascending=False, method="min").astype(int)
STATS = [("Overall", "Offensive rating", "Advanced", "OFF_RATING", 1, ""),
         ("Overall", "Defensive rating", "Advanced", "DEF_RATING", 1, ""),
         ("Overall", "Net rating", "Advanced", "NET_RATING", 1, ""),
         ("Overall", "Pace", "Advanced", "PACE", 1, ""),
         ("Style", "3-point attempt share", None, None, 1, "%"),
         ("Style", "Fast break points", "Misc", "PTS_FB", 1, ""),
         ("Style", "Points in the paint", "Misc", "PTS_PAINT", 1, ""),
         ("Style", "Assist percentage", "Advanced", "AST_PCT", 1, "%"),
         ("Style", "Assist-to-turnover ratio", "Advanced", "AST_TO", 2, ""),
         ("Four factors", "Effective FG%", "Four Factors", "EFG_PCT", 1, "%"),
         ("Four factors", "Turnover rate", "Four Factors", "TM_TOV_PCT", 1, "%"),
         ("Four factors", "Offensive rebound rate", "Four Factors", "OREB_PCT", 1, "%"),
         ("Four factors", "Free throw rate", "Four Factors", "FTA_RATE", 1, "%")]
CHI = 1610612741
rows = []
for g, label, tab, col, dec, suf in STATS:
    if tab is None:
        vals, ranks = share, share_rank
    else:
        df = T[tab]; vals, ranks = df[col], df[col + "_RANK"].astype(int)
    pct = suf == "%" and tab in ("Advanced", "Four Factors") and vals.max() <= 1
    v = vals * 100 if pct else vals
    rows.append({"group": g, "label": label, "value": round(float(v[CHI]), dec), "suffix": suf, "rank": int(ranks[CHI]),
                 "tied": int((ranks == ranks[CHI]).sum()), "dec": dec,
                 "all": sorted([[round(float(v[t]), dec), int(ranks[t])] for t in v.index], key=lambda x: x[1])})
meta = {"season": "2025-26", "gp": int(B.loc[CHI, "GP"]), "w": int(B.loc[CHI, "W"]), "l": int(B.loc[CHI, "L"]),
        "pulled": PULLED.read_text().strip(), "rows": rows}
(OUT / "ranks.json").write_text(json.dumps(meta, indent=1))
for r in rows: print(f"{r['group']:12} {r['label']:28} {r['value']:>7}{r['suffix']:2} #{r['rank']} tied {r['tied']}")
