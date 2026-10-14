"""Rank Bulls rookies by points in their NBA debut, since the 1976-77 merger.

Cohort: every player whose first NBA regular-season game was for Chicago, drafted or not.
The top fifteen by points are shown, plus everyone tied with fifteenth, in the game table with points
in the red card column. The table is HTML in the house type (Geist), styled after the postgame recap
(first name over last name, draft chips, square W/L chips, red points tiles), rendered by Chromium at 3x
into a transparent PNG for the Canva page, which carries the title, subtitle, mark, notes and footer.

``top_game_performances`` owns NBA.com collection and reconciliation. NBA.com has a Bulls
player row with points for every game from 1976-77; before 1983-84 some steals, blocks and
turnovers are blank. A blank shown on the page is filled from Basketball-Reference only when
that box score has the value; otherwise it stays empty, never zero.
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import commonallplayers, drafthistory
from PIL import Image
from playwright.sync_api import sync_playwright

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import HEADSHOT_CACHE, cut_out_flat_background
from scripts.prototypes import top_game_performances as base


PROJECT = "bulls-rookie-debuts"
FIRST_END_YEAR = 1977  # 1976-77, the first season after the ABA-NBA merger
MERGER_DRAFT_YEAR = 1976
TOP_N = 15
DATA_DIR = _REPO / "docs" / "visuals" / "2026-09-28-bulls-rookie-debuts" / "data"
FIRST_SEASONS_PATH = DATA_DIR / "nba_common_all_players.csv"
DRAFT_PATH = DATA_DIR / "nba_draft_history.csv"
CAREER_PATH = DATA_DIR / "career_team_seasons.csv"
BBR_FILLS_PATH = DATA_DIR / "bbr_box_score_fills.csv"
# The NBA CDN serves a silhouette for these six. Four reuse portraits framed for earlier posts;
# Jay Williams reuses the rookie post's cut-out and Scott May's is a background-removed web
# portrait (data/portraits_source/SOURCES.md); both are framed here like NBA headshots.
FRAMED_PORTRAITS = {
    76497: _REPO / "docs/visuals/2026-09-20-sophomore-game-scores/data/portraits/76497.png",  # Dailey
    2033: _REPO / "docs/visuals/2026-09-03-bench-points-season/data/portraits/2033.png",  # Fizer
    2648: _REPO / "docs/visuals/2026-09-25-bulls-debut-games/data/portraits/2648.png",  # Dupree
    78523: _REPO / "docs/visuals/2026-09-25-bulls-debut-games/data/portraits/78523.png",  # Wiggins
}
PORTRAIT_SOURCES = {
    77490: DATA_DIR / "portraits_source" / "Scott May.png",
    2398: _REPO / "docs/visuals/2026-09-18-rookie-game-scores/data/portraits/2398.png",  # Jay Williams
}
SHOWN_STATS = ["reb", "ast", "fgm", "fga", "fg3m", "fg3a", "stl", "blk", "tov"]
FIRST_THREE_POINT_SEASON_END = 1980  # the NBA added the 3-point line in 1979-80
OUT = _REPO / "output" / PROJECT
FONTS = Path.home() / "Library" / "Fonts"
# The table is laid out in Canva page pixels: 1030 wide, placed at x=25, y=204 on the 1080x1440
# page under the serif title and subtitle (approved page: v26, 2026-10-13), exported at 3x.
WIDTH = 1030
SCALE = 3
ROW = 72
FACE = 96
COLS = "44px 92px 214px 150px 92px 56px 56px 78px 72px 56px 56px 56px"


def _snapshot(path: Path, factory, source: str, refresh: bool) -> pd.DataFrame:
    if path.exists() and not refresh:
        return pd.read_csv(path)
    frame = base._request_frame(factory, source)
    frame["captured_at"] = datetime.now(base.SNAPSHOT_TZ).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def fetch_first_seasons(refresh: bool = False) -> pd.DataFrame:
    return _snapshot(FIRST_SEASONS_PATH, lambda: commonallplayers.CommonAllPlayers(
        is_only_current_season=0, headers=_NBA_HEADERS, timeout=60), "CommonAllPlayers", refresh)


def fetch_draft_history(refresh: bool = False) -> pd.DataFrame:
    return _snapshot(DRAFT_PATH, lambda: drafthistory.DraftHistory(
        headers=_NBA_HEADERS, timeout=60), "DraftHistory", refresh)


def attach_draft_and_entry(first: pd.DataFrame, first_seasons: pd.DataFrame,
                           draft: pd.DataFrame) -> pd.DataFrame:
    seasons = first_seasons[["PERSON_ID", "FROM_YEAR"]].rename(columns={"PERSON_ID": "player_id"})
    picks = draft[["PERSON_ID", "SEASON", "ROUND_NUMBER", "OVERALL_PICK", "TEAM_ID",
                   "TEAM_ABBREVIATION"]].rename(columns={
        "PERSON_ID": "player_id", "SEASON": "draft_year", "ROUND_NUMBER": "draft_round",
        "OVERALL_PICK": "draft_pick", "TEAM_ID": "draft_team_id", "TEAM_ABBREVIATION": "draft_team"})
    audit = first.merge(seasons, on="player_id", how="left", validate="one_to_one")
    if audit["FROM_YEAR"].isna().any():
        raise ValueError(f"CommonAllPlayers has no first season for {audit.loc[audit.FROM_YEAR.isna(), 'player'].tolist()}.")
    audit["first_nba_season_end"] = audit.pop("FROM_YEAR").astype(int) + 1
    # Before 1989 a player could be drafted more than once; the latest pick before his
    # first Bulls game holds his rights. Earlier picks stay visible in the audit.
    picks = picks.merge(audit[["player_id", "season_end_year"]], on="player_id")
    picks = picks[picks["draft_year"] < picks["season_end_year"]].drop(columns="season_end_year")
    all_picks = (picks.sort_values("draft_year")
                 .assign(pick=lambda f: f["draft_year"].astype(str) + " " + f["draft_team"])
                 .groupby("player_id")["pick"].agg("; ".join).rename("all_draft_picks"))
    latest = picks.sort_values("draft_year").groupby("player_id").tail(1)
    return (audit.merge(latest, on="player_id", how="left", validate="one_to_one")
            .merge(all_picks, on="player_id", how="left"))


def needs_career_check(audit: pd.DataFrame, cutoff: int) -> pd.Series:
    """Non-rookies by listed first season who scored enough in their first Bulls game to rank.

    CommonAllPlayers can date a player from his draft year (Randy Holcomb), so career team
    history decides whether he really played anywhere before Chicago.
    """
    return (~audit["rookie_debut"] & ~audit["aba_veteran"]
            & (audit["first_nba_season_end"] >= FIRST_END_YEAR) & (audit["points"] >= cutoff))


def classify(audit: pd.DataFrame, career: pd.DataFrame) -> pd.DataFrame:
    """Mark rookie debuts: the player's first Bulls game is his first NBA game."""
    audit = audit.copy()
    first_season = (career.assign(end_year=career["SEASON_ID"].str[:4].astype(int) + 1)
                    .groupby("PLAYER_ID")["end_year"].min())
    career_first = audit["player_id"].map(first_season)
    checked = career_first.notna()
    entry = audit["first_nba_season_end"].where(~checked, career_first).astype(int)
    audit["entry_rule"] = checked.map({True: "career team history", False: "CommonAllPlayers FROM_YEAR"})
    # ABA players joined the NBA in 1976-77 and are listed as first-year players then; a real
    # 1976-77 rookie was drafted in 1976.
    audit["aba_veteran"] = audit["first_nba_season_end"].eq(FIRST_END_YEAR) & ~(
        audit["draft_year"] >= MERGER_DRAFT_YEAR)
    audit["rookie_debut"] = entry.eq(audit["season_end_year"]) & ~audit["aba_veteran"]
    audit["eligible"] = audit["rookie_debut"]
    return audit


def competition_ranks(points: pd.Series) -> list[str]:
    rank = points.rank(method="min", ascending=False).astype(int)
    tied = points.duplicated(keep=False)
    return [f"T{r}" if t else str(r) for r, t in zip(rank, tied)]


def rank_debuts(eligible: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    ordered = eligible.sort_values(["points", "game_date", "player_id"],
                                   ascending=[False, True, True], kind="stable")
    cutoff = ordered["points"].iloc[top_n - 1]
    ranked = ordered[ordered["points"] >= cutoff].copy()
    ranked = ranked.reset_index(drop=True)
    ranked["rank"] = ranked["points"].rank(method="min", ascending=False).astype(int)
    ranked["rank_label"] = competition_ranks(ranked["points"])
    return ranked


def apply_bbr_fills(ranked: pd.DataFrame, fills: pd.DataFrame) -> pd.DataFrame:
    """Fill blank displayed NBA.com cells from saved Basketball-Reference box scores."""
    ranked = ranked.copy()
    ranked["filled_from_bbr"] = ""
    for fill in fills.itertuples():
        match = ranked["player_id"].eq(fill.player_id) & ranked["game_date"].eq(fill.game_date)
        if not match.any():
            continue
        if pd.notna(ranked.loc[match, fill.stat]).any():
            raise ValueError(f"{fill.player} {fill.stat} is not blank on NBA.com; no fill needed.")
        ranked.loc[match, fill.stat] = fill.value
        ranked.loc[match, "filled_from_bbr"] += f"{fill.stat} "
    return ranked


def blank_cells(ranked: pd.DataFrame) -> list[str]:
    blanks = []
    for row in ranked.itertuples():
        for stat in SHOWN_STATS:
            if stat.startswith("fg3") and row.season_end_year < FIRST_THREE_POINT_SEASON_END:
                continue
            if pd.isna(getattr(row, stat)):
                blanks.append(f"{row.player} {row.game_date} {stat}")
    return blanks


def validate(audit: pd.DataFrame, ranked: pd.DataFrame, working: pd.DataFrame) -> dict[str, object]:
    if audit["player_id"].duplicated().any():
        raise ValueError("A player has more than one first Bulls game.")
    eligible = audit[audit["eligible"]]
    if eligible["points"].isna().any():
        raise ValueError("An eligible debut has no points.")
    cutoff = int(ranked["points"].min())
    unchecked = needs_career_check(audit, cutoff) & audit["entry_rule"].ne("career team history")
    if unchecked.any():
        raise ValueError(f"First NBA season unverified for {audit.loc[unchecked, 'player'].tolist()}.")
    games = working[working["game_id"].isin(ranked["game_id"])]
    per_game = games.groupby("game_id").agg(player_points=("points", "sum"),
                                            team_points=("team_points", "first"))
    if not per_game["player_points"].eq(per_game["team_points"]).all():
        raise ValueError("Ranked debut games do not reconcile to the Bulls team score.")
    below = eligible[eligible["points"] < cutoff]
    next_points = int(below["points"].max())
    first_out = below[below["points"].eq(next_points)].sort_values("game_date")
    return {
        "first_games": len(audit),
        "rookie_debuts": int(audit["rookie_debut"].sum()),
        "eligible_debuts": len(eligible),
        "undrafted_debuts": int(eligible["draft_year"].isna().sum()),
        "aba_veterans_excluded": audit.loc[audit["aba_veteran"], "player"].tolist(),
        "career_checked": audit.loc[audit["entry_rule"].eq("career team history"), "player"].tolist(),
        "rows": len(ranked),
        "cutoff_points": cutoff,
        "first_out": f"{next_points} points: {', '.join(first_out['player'])}",
    }


def post_portraits() -> dict[int, Path]:
    cut = {player_id: cut_out_flat_background(source, DATA_DIR / "portraits" / f"{player_id}.png")
           for player_id, source in PORTRAIT_SOURCES.items()}
    return {**FRAMED_PORTRAITS, **cut}


def _stat(value) -> str:
    """A stat that was not recorded shows a plain hyphen, never zero (user, 2026-09-28)."""
    return "-" if pd.isna(value) else str(int(value))


def _made_attempted(made, attempted) -> str:
    return "-" if pd.isna(made) or pd.isna(attempted) else f"{int(made)}-{int(attempted)}"


def draft_label(row: pd.Series) -> str:
    if pd.isna(row["draft_year"]):
        return "UNDRAFTED"
    return f"RD{int(row['draft_round'])} PK{int(row['draft_pick'])}"


CSS = f"""
@font-face{{font-family:House;font-weight:400;src:local('Geist-Regular'),url('file://{FONTS}/Geist-Regular.otf')}}
@font-face{{font-family:House;font-weight:600;src:local('Geist-SemiBold'),url('file://{FONTS}/Geist-SemiBold.otf')}}
*{{box-sizing:border-box;margin:0}}
body{{width:{WIDTH}px;background:transparent;font-family:House;color:#242424;font-variant-numeric:tabular-nums}}
.row,.hd{{display:grid;grid-template-columns:{COLS};align-items:center}}
.hd{{height:40px;font-weight:600;font-size:19px;border-bottom:3px solid #242424}}
.hd div{{text-align:center}} .hd .l{{text-align:left}} .hd .p{{color:#CE1141}} .hd .nmh{{padding-left:8px}}
.row{{height:{ROW}px;position:relative}}
.band{{background:#E2DED9}}
.rk{{font-weight:600;font-size:24px;text-align:center}}
.pf{{height:{ROW}px;position:relative}}
.face{{position:absolute;left:-8px;bottom:0;width:{FACE}px;height:{FACE}px;overflow:hidden}}
.face img{{position:absolute;top:0}}
.nm{{display:flex;flex-direction:column;line-height:1;padding-left:8px}}
.nm small{{font-size:18px;margin-bottom:3px;display:flex;align-items:center;gap:8px}}
.nm b{{font-weight:600;font-size:29px;white-space:nowrap}}
.chip{{background:#242424;color:#E9E5E1;font-weight:600;font-size:12px;letter-spacing:.5px;padding:3px 5px}}
.dt{{display:flex;flex-direction:column;font-size:19px;line-height:1.15;color:#645D57}}
.opp{{display:flex;align-items:center;gap:6px}}
.wl{{font-style:normal;font-weight:600;color:#fff;font-size:15px;width:22px;height:22px;display:inline-flex;
  align-items:center;justify-content:center}}
.W{{background:#2E8540}} .L{{background:#CE1141}}
.pts{{display:flex;justify-content:center}}
.tile{{width:76px;height:60px;background:#CE1141;color:#fff;font-weight:600;font-size:34px;display:flex;
  align-items:center;justify-content:center;box-shadow:2px 2px 4px rgba(72,8,24,.25)}}
.v{{text-align:center;font-size:26px}}
"""


def _face(path: Path, z: int) -> str:
    if not path.exists():
        raise FileNotFoundError(f"No portrait at {path}.")
    width, height = Image.open(path).size
    side = min(int(height * 0.74), width)
    scale = FACE / side
    left = (width - side) // 2
    return (
        f'<div class="face" style="z-index:{z}"><img src="{path.as_uri()}" '
        f'style="width:{width * scale:.1f}px;height:{height * scale:.1f}px;left:{-left * scale:.1f}px"></div>'
    )


def table_html(ranked: pd.DataFrame) -> str:
    portraits = post_portraits()
    rows = []
    for index, (_, row) in enumerate(ranked.iterrows()):
        first, last = base._display_name(str(row["player"])).split(" ", 1)
        date, matchup, result = base._game_context_parts(row)
        player_id = int(row["player_id"])
        portrait = portraits.get(player_id, HEADSHOT_CACHE / f"{player_id}.png")
        stats = [_stat(row["reb"]), _stat(row["ast"]), _made_attempted(row["fgm"], row["fga"]),
                 _made_attempted(row["fg3m"], row["fg3a"]), _stat(row["stl"]), _stat(row["blk"]), _stat(row["tov"])]
        rows.append(
            f'<div class="row{" band" if index % 2 == 0 else ""}">'
            f'<div class="rk">{row["rank_label"]}</div>'
            f'<div class="pf">{_face(portrait, 10 + index)}</div>'
            f'<div class="nm"><small>{html.escape(first)}<span class="chip">{draft_label(row)}</span></small>'
            f'<b>{html.escape(last)}</b></div>'
            f'<div class="dt"><span>{date}</span><span class="opp">{html.escape(matchup)} '
            f'<i class="wl {result}">{result}</i></span></div>'
            f'<div class="pts"><div class="tile">{int(row["points"])}</div></div>'
            + "".join(f'<div class="v">{value}</div>' for value in stats) + "</div>")
    head = ('<div class="hd"><div>#</div><div></div><div class="l nmh">PLAYER</div><div class="l">NBA DEBUT</div>'
            '<div class="p">PTS</div><div>REB</div><div>AST</div><div>FG</div><div>3PT</div><div>STL</div>'
            '<div>BLK</div><div>TOV</div></div>')
    return f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>{head}{"".join(rows)}'


CHECK_JS = """() => {
  const fonts = [...document.fonts].filter(f => f.family === 'House');
  if (fonts.length < 2 || fonts.some(f => f.status !== 'loaded')) return {error: 'Geist did not load'};
  const overflow = [...document.querySelectorAll('.row > div:not(.pf), .hd > div')]
    .filter(c => c.scrollWidth > c.clientWidth + 1).map(c => c.textContent.trim());
  const below = Math.max(0, ...[...document.querySelectorAll('.face')].map(f =>
    f.getBoundingClientRect().bottom - f.parentElement.getBoundingClientRect().bottom));
  return {overflow, below, height: Math.ceil(document.body.getBoundingClientRect().height)};
}"""


def render_table(ranked: pd.DataFrame) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT / f"{PROJECT}-table.html"
    source.write_text(table_html(ranked))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 1400}, device_scale_factor=SCALE)
        page.goto(source.as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        report = page.evaluate(CHECK_JS)
        if "error" in report:
            raise RuntimeError(report["error"])
        if report["overflow"]:
            raise ValueError(f"Cells overflow: {report['overflow']}.")
        if report["below"] > 0.5:
            raise ValueError(f"A portrait reaches {report['below']:.1f}px below its row.")
        path = OUT / f"{PROJECT}-table.png"
        page.screenshot(path=str(path), clip={"x": 0, "y": 0, "width": WIDTH, "height": report["height"]},
                        omit_background=True)
        browser.close()
    print(f"{path.name}: {len(ranked)} rows, {WIDTH}x{report['height']} page px at {SCALE}x")
    return path


def canva_copy(report: dict[str, object]) -> str:
    return "\n".join([
        "CANVA COPY",
        "TITLE: BULLS’ BEST NBA DEBUTS",
        "SUBTITLE: Most points in an NBA debut by a Bulls rookie, since 1976-77",
        "FOOTER: Data via NBA.com, Basketball-Reference | 1976-77 to 2025-26 regular season",
        "NOTE: - = not recorded: no 3-point line until 1979-80, and turnovers weren't tracked until 1977-78.",
        f"AUDIT: {report['eligible_debuts']} Bulls rookie debuts; top {TOP_N} plus ties = "
        f"{report['rows']} rows at {report['cutoff_points']}+ points; first out {report['first_out']}.",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Bulls rookie-debut table.")
    parser.add_argument("--refresh", action="store_true", help="Refetch NBA.com snapshots.")
    args = parser.parse_args()

    players, teams = base.fetch_bulls_history(season_type="Regular Season",
                                              first_end_year=FIRST_END_YEAR)
    working = base.build_working_table(players, teams)
    first = attach_draft_and_entry(base.first_bulls_games(working),
                                   fetch_first_seasons(args.refresh), fetch_draft_history(args.refresh))
    unchecked = classify(first, pd.DataFrame(columns=["PLAYER_ID", "SEASON_ID", "TEAM_ID"]))
    cutoff = int(rank_debuts(unchecked[unchecked["eligible"]])["points"].min())
    checked = unchecked.loc[needs_career_check(unchecked, cutoff), "player_id"].tolist()
    audit = classify(first, base.fetch_career_seasons(checked, CAREER_PATH, refresh=args.refresh))
    ranked = apply_bbr_fills(rank_debuts(audit[audit["eligible"]]), pd.read_csv(BBR_FILLS_PATH))
    report = validate(audit, ranked, working)

    audit.to_csv(DATA_DIR / "first_bulls_games_audit.csv", index=False)
    audit[audit["eligible"]].sort_values("points", ascending=False).to_csv(
        DATA_DIR / "bulls_rookie_debuts.csv", index=False)
    ranked.to_csv(DATA_DIR / "top_rookie_debuts.csv", index=False)

    base.ensure_headshots(ranked["player_id"].tolist())
    base.ensure_historical_headshot_fallbacks(ranked["player_id"].tolist())
    print(f"Table: {render_table(ranked)}")
    copy = canva_copy(report)
    (DATA_DIR / "canva-copy.txt").write_text(copy + "\n")
    print(copy)
    print("Blank displayed cells:", blank_cells(ranked))
    print({k: v for k, v in report.items()})
    print(ranked[["rank_label", "player", "game_date", "matchup", "result", "points", "reb", "ast",
                  "fgm", "fga", "fg3m", "fg3a", "stl", "blk", "tov", "draft_team",
                  "filled_from_bbr"]].to_string(index=False))


if __name__ == "__main__":
    main()
