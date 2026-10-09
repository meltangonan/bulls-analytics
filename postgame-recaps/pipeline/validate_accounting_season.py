"""Check that the four-factor accounting reconciles to the final margin in every 2025-26 Bulls game.

Run from the repo root with the primary venv:
    PYTHONPATH=. venv/bin/python postgame-recaps/pipeline/validate_accounting_season.py
Play-by-play is cached in output/postgame-recap/pbp/ (ignored by git). Writes
data/accounting-season-2025-26.csv. Every game must show play-by-play points equal to the official
score and a reconciliation error of zero; the script exits non-zero otherwise.
"""
import sys
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import playbyplayv3

sys.path.insert(0, str(Path(__file__).resolve().parent))
import accounting as acc  # noqa: E402
from bulls.data.fetch import _NBA_HEADERS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
from paths import OUTPUT, STRESS  # noqa: E402
CACHE = OUTPUT / "pbp"


def pbp_for(game_id: str) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{game_id}.csv"
    if not path.exists():
        for _ in range(3):
            try:
                playbyplayv3.PlayByPlayV3(game_id=game_id, headers=_NBA_HEADERS, timeout=60
                                          ).get_data_frames()[0].to_csv(path, index=False)
                break
            except Exception:
                time.sleep(3)
        time.sleep(0.6)
    return pd.read_csv(path)


def main() -> int:
    lg = acc.lg
    rows = []
    for g in lg[lg.TEAM_ABBREVIATION == "CHI"].sort_values("GAME_DATE").itertuples():
        both = lg[lg.GAME_ID == g.GAME_ID]
        teams = {int(r.TEAM_ID): r.TEAM_ABBREVIATION for r in both.itertuples()}
        opp = next(t for t in teams.values() if t != "CHI")
        cats, possessions, pts = acc.account(pbp_for(g.GAME_ID), teams)
        centred = acc.centred(cats, possessions)
        official = {r.TEAM_ABBREVIATION: int(r.PTS) for r in both.itertuples()}
        margin = official["CHI"] - official[opp]
        edge = {k: centred["CHI"][k] - centred[opp][k] for k in centred["CHI"]}
        extra = acc.V * (possessions["CHI"] - possessions[opp])
        rows.append(dict(date=g.GAME_DATE[:10], opp=opp, ot=g.MIN > 240, margin=margin, pts_ok=pts == official,
                         recon=round(sum(edge.values()) + extra - margin, 6),
                         **{k: round(v, 1) for k, v in edge.items()}, extra=round(extra, 1)))
    d = pd.DataFrame(rows)
    d.to_csv(STRESS / "accounting-season-2025-26.csv", index=False)
    ok = bool(d.pts_ok.all() and d.recon.abs().max() < 1e-6)
    print(f"{len(d)} games, points match {int(d.pts_ok.sum())}, max error {d.recon.abs().max()}, ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
