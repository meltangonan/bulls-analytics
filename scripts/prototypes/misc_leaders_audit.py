"""Independent audit of the four Misc-stat leaderboards.

1. Team reconciliation: sum of Bulls player rows == Bulls team total (LeagueDashTeamStats), every season.
2. Game logs: for every displayed row, PlayerGameLogs (Misc + Base, Bulls games) sum to the season
   total, games played and PTS.
3. Fresh re-fetch: today's LeagueDashPlayerStats Bulls Misc/Base == the saved responses.
Outputs audit_team_totals.csv and audit_game_logs.csv into each post's data/ folder.
Runs on whichever of the four post folders exist in this checkout.
"""
import json, sys, time
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nba_api.stats.endpoints import leaguedashteamstats, playergamelogs, leaguedashplayerstats
from bulls.data.fetch import _NBA_HEADERS

BULLS = 1610612741
S = ROOT / "cache/misc_leaders_audit"  # ignored response cache
S.mkdir(parents=True, exist_ok=True)
POSTS = {  # slug: (stat column, points column name in top15.csv)
    "fast-break-points": ("PTS_FB", "fast_break_points"),
    "points-in-the-paint": ("PTS_PAINT", "points"),
    "points-off-turnovers": ("PTS_OFF_TOV", "points"),
    "second-chance-points": ("PTS_2ND_CHANCE", "points"),
}
POSTS = {k: v for k, v in POSTS.items() if (ROOT / f"docs/visuals/2026-09-29-{k}").exists()}
STATS = [v[0] for v in POSTS.values()]
SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(1996, 2026)]
RAW = ROOT / f"docs/visuals/2026-09-29-{next(iter(POSTS))}/data/raw"  # Bulls Misc responses are identical across posts


def cached(name, fn):
    p = S / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    for attempt in range(4):
        try:
            d = fn().get_dict(); break
        except Exception as e:
            print("retry", name, e); time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError(name)
    p.write_text(json.dumps(d)); time.sleep(0.6)
    return d


def frame(d, i=0):
    r = d["resultSets"][i]; return pd.DataFrame(r["rowSet"], columns=r["headers"])


def saved(kind, season):
    r = json.loads((RAW / f"{kind}-bulls-{season}.json").read_text())["resultSets"][0]
    return pd.DataFrame(r["rowSet"], columns=r["headers"])


# 1. Team reconciliation ---------------------------------------------------------------
team_rows = []
for s in SEASONS:
    t = frame(cached(f"team-misc-{s}", lambda: leaguedashteamstats.LeagueDashTeamStats(
        season=s, measure_type_detailed_defense="Misc", per_mode_detailed="Totals",
        season_type_all_star="Regular Season", headers=_NBA_HEADERS, timeout=60)))
    t = t[t.TEAM_ID == BULLS].iloc[0]
    p = saved("misc", s)
    row = {"season": s}
    for c in STATS:
        row[f"{c}_players"] = int(pd.to_numeric(p[c]).sum()); row[f"{c}_team"] = int(t[c])
    team_rows.append(row)
team = pd.DataFrame(team_rows)
for c in STATS:
    team[f"{c}_diff"] = team[f"{c}_players"] - team[f"{c}_team"]
print("TEAM: max abs diff per stat:", {c: int(team[f"{c}_diff"].abs().max()) for c in STATS})

# 2 + 3. Displayed rows: game logs and fresh season totals -----------------------------
fresh_cache = {}
def fresh(kind, s):
    if (kind, s) not in fresh_cache:
        fresh_cache[(kind, s)] = frame(cached(f"fresh-{kind}-{s}", lambda: leaguedashplayerstats.LeagueDashPlayerStats(
            season=s, measure_type_detailed_defense=kind.capitalize(), per_mode_detailed="Totals",
            season_type_all_star="Regular Season", team_id_nullable=BULLS, headers=_NBA_HEADERS, timeout=60)))
    return fresh_cache[(kind, s)]

results = {}
for slug, (col, pcol) in POSTS.items():
    d = ROOT / f"docs/visuals/2026-09-29-{slug}/data"
    top = pd.read_csv(d / "top15.csv")
    out = []
    for r in top.itertuples():
        s, pid = r.season, int(r.player_id)
        gm = frame(cached(f"gl-misc-{pid}-{s}", lambda: playergamelogs.PlayerGameLogs(
            season_nullable=s, player_id_nullable=pid, team_id_nullable=BULLS,
            measure_type_player_game_logs_nullable="Misc", season_type_nullable="Regular Season",
            headers=_NBA_HEADERS, timeout=60)))
        gb = frame(cached(f"gl-base-{pid}-{s}", lambda: playergamelogs.PlayerGameLogs(
            season_nullable=s, player_id_nullable=pid, team_id_nullable=BULLS,
            measure_type_player_game_logs_nullable="Base", season_type_nullable="Regular Season",
            headers=_NBA_HEADERS, timeout=60)))
        fm = fresh("misc", s); fm = fm[fm.PLAYER_ID == pid].iloc[0]
        fb = fresh("base", s); fb = fb[fb.PLAYER_ID == pid].iloc[0]
        shown = int(getattr(r, pcol))
        total_pts = round(float(shown) / float(r.share_of_points)) if r.share_of_points else None
        out.append({
            "season": s, "player": r.player_name, "shown": shown,
            "gamelog_sum": int(pd.to_numeric(gm[col]).sum()), "gamelog_games": len(gm),
            "shown_games": int(r.games), "fresh_season": int(fm[col]), "fresh_gp": int(fm.GP),
            "gamelog_pts": int(pd.to_numeric(gb.PTS).sum()), "fresh_pts": int(fb.PTS),
            "share_shown_pct": round(100 * float(r.share_of_points)),
            "share_from_gamelogs_pct": round(100 * shown / pd.to_numeric(gb.PTS).sum()),
            "per_game_shown": round(float(getattr(r, pcol + "_per_game" if pcol != "points" else "points_per_game")), 1),
            "per_game_from_gamelogs": round(pd.to_numeric(gm[col]).sum() / len(gm), 1),
        })
    a = pd.DataFrame(out)
    a["ok"] = ((a.shown == a.gamelog_sum) & (a.shown == a.fresh_season) & (a.shown_games == a.gamelog_games)
               & (a.shown_games == a.fresh_gp) & (a.gamelog_pts == a.fresh_pts)
               & (a.share_shown_pct == a.share_from_gamelogs_pct) & (a.per_game_shown == a.per_game_from_gamelogs))
    a.to_csv(d / "audit_game_logs.csv", index=False)
    team[["season", f"{col}_players", f"{col}_team", f"{col}_diff"]].to_csv(d / "audit_team_totals.csv", index=False)
    results[slug] = a
    print(f"\n== {slug}: {int(a.ok.sum())}/15 rows pass; team seasons reconciled: {int((team[f'{col}_diff'] == 0).sum())}/30")
    bad = a[~a.ok]
    if len(bad):
        print(bad.to_string(index=False))
