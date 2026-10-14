"""Build the Lakers' top fifteen regular-season Game Scores by decade, 1983-84 to 2025-26.

The first Lakers test post for the team-expansion research (Notion: "Next team expansion
research"). Data comes from the Bulls decade builder in `top_game_performances.py` with the team
swapped in this file; the team profile that replaces the swap comes with the first post that
ships. 1983-84 is the first season whose NBA.com box scores carry every Game Score input:
earlier Lakers seasons lack steals, blocks, turnovers or offensive rebounds in some or all games.

The tables are HTML rendered by Chromium at 2x into transparent PNGs (as the career-marathons
post does), placed on Canva pages that carry the title, subtitle and footer. The build fails if
the fonts do not load, a column gap gets too tight, a cell overflows, or a portrait reaches below
its row.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts" / "prototypes"))

import pandas as pd
from PIL import Image
from playwright.sync_api import sync_playwright

import top_game_performances as base
from bulls.graphics.house import HEADSHOT_CACHE, ensure_headshots

LAKERS_TEAM_ID = 1610612747
LAKERS_PURPLE = "#552583"
FIRST_SEASON_END_YEAR = 1984
TOP_N = 15
DECADES = ("1980s", "1990s", "2000s", "2010s", "2020s")
ERA_TOP_N = 30
ERAS = {"since-1983": 1984, "since-2000": 2001}  # label: first season end year
SLUG = "2026-10-11-lakers-decade-game-scores"
DATA_DIR = _REPO / "docs" / "visuals" / SLUG / "data"
OUT = _REPO / "output" / "lakers-decade-game-scores"
FONTS = Path.home() / "Library" / "Fonts"
WIDTH = 1500  # CSS px; rendered at 2x, the 3000 px width of the published Game Score tables
FACE = 132  # portrait square, px; taller than the row so it overlaps the row above only
MIN_GAP = 22  # px between ordinary stat columns
SHOOTING_GAP_RATIO = 0.55
CARD_PADDING = 24  # px from the widest Game Score number to each card edge

base.BULLS_TEAM_ID = LAKERS_TEAM_ID
base.RAW_CACHE = _REPO / "cache" / "nba.com" / "lakers-top-game-performances"
_BULLS_DECADE = base.decade_for_end_year


def decade_for_end_year(end_year: int) -> str:
    """The Bulls post's end-year decades, with the 1980s starting at 1983-84."""
    if 1984 <= end_year <= 1990:
        return "1980s"
    return _BULLS_DECADE(end_year)


base.decade_for_end_year = decade_for_end_year

# NBA.com's old codes for teams that never moved; relocated franchises (SEA, NJN, NOH) keep theirs.
OPPONENT_LABELS = {"GOS": "GSW", "PHL": "PHI", "UTH": "UTA"}
_BULLS_OPPONENT = base._opponent


def _opponent(matchup: str) -> str:
    """Display label only; the saved data keeps NBA.com's code."""
    code = _BULLS_OPPONENT(matchup)
    return OPPONENT_LABELS.get(code, code)


base._opponent = _opponent


def top_with_ties(table: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    ranked = base.top_games_by_decade(table, top_n=len(table))
    keep = []
    for _, games in ranked.groupby("decade", sort=False):
        cutoff = games["game_score"].round(1).iloc[top_n - 1]
        keep.append(games[games["game_score"].round(1) >= cutoff])
    return pd.concat(keep, ignore_index=True)


def rank_labels(scores: pd.Series) -> list[str]:
    rounded = scores.round(1)
    rank = rounded.rank(method="min", ascending=False).astype(int)
    tied = rounded.duplicated(keep=False)
    return [f"T{r}" if t else str(r) for r, t in zip(rank, tied)]


def era_slides(table: pd.DataFrame, first_end_year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    pool = table[table["season_end_year"] >= first_end_year].assign(decade="era")
    ranked = top_with_ties(pool, ERA_TOP_N)
    ranked["rank_label"] = rank_labels(ranked["game_score"])
    if ranked["game_score"].round(1).iloc[TOP_N - 1] == ranked["game_score"].round(1).iloc[TOP_N]:
        raise ValueError("A tie straddles the 15/16 slide split.")
    return ranked.iloc[:TOP_N], ranked.iloc[TOP_N:]


def validate(table: pd.DataFrame) -> dict[str, object]:
    years = set(table["season_end_year"])
    if years != set(range(FIRST_SEASON_END_YEAR, base.LAST_SEASON_END_YEAR + 1)):
        raise ValueError("Coverage does not include every season since 1983-84.")
    if table.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Duplicate player-game rows.")
    inputs = ["points", "fgm", "fga", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf"]
    incomplete = set(table.loc[table[inputs].isna().any(axis=1), "game_id"])
    per_game = table.groupby("game_id").agg(players=("points", "sum"), team=("team_points", "first"))
    unreconciled = set(per_game.index[per_game["players"] != per_game["team"]])
    minutes = table.groupby("game_id")["minutes"].sum()
    off_budget = set(minutes.index[((minutes - 240) % 25).between(4, 21)])
    flagged = incomplete | unreconciled | off_budget
    ranked = top_with_ties(table[~table["game_id"].isin(incomplete)])
    counts = ranked.groupby("decade").size().to_dict()
    if set(counts) != set(DECADES) or min(counts.values()) < TOP_N:
        raise ValueError(f"Each decade needs at least {TOP_N} rows; got {counts}.")
    if flagged & set(ranked["game_id"]):
        raise ValueError(f"A flagged game reached a table: {sorted(flagged & set(ranked['game_id']))}.")
    return {
        "ranked": ranked,
        "table": table[~table["game_id"].isin(incomplete)],
        "counts": counts,
        "seasons": len(years),
        "games": table["game_id"].nunique(),
        "player_games": len(table),
        "flagged_games": sorted(flagged),
    }


COLUMNS = (  # header, value, made-attempted?
    ("PTS", lambda r: str(int(r["points"])), False),
    ("REB", lambda r: str(int(r["reb"])), False),
    ("AST", lambda r: str(int(r["ast"])), False),
    ("FG", lambda r: f"{int(r['fgm'])}-{int(r['fga'])}", True),
    ("3PT", lambda r: f"{int(r['fg3m'])}-{int(r['fg3a'])}", True),
    ("FT", lambda r: f"{int(r['ftm'])}-{int(r['fta'])}", True),
    ("TS%", lambda r: f"{float(r['ts_pct']):.1f}", False),
    ("STL", lambda r: str(int(r["stl"])), False),
    ("BLK", lambda r: str(int(r["blk"])), False),
    ("TOV", lambda r: str(int(r["tov"])), False),
)

CSS = f"""
@font-face{{font-family:House;font-weight:400;src:local('Geist-Regular'),url('file://{FONTS}/Geist-Regular.otf')}}
@font-face{{font-family:House;font-weight:600;src:local('Geist-SemiBold'),url('file://{FONTS}/Geist-SemiBold.otf')}}
*{{box-sizing:border-box;margin:0}}
:root{{--lead:0px;--row:108px;--g:{MIN_GAP}px;--s:calc(var(--g) * {SHOOTING_GAP_RATIO});--cp:{CARD_PADDING}px}}
body{{width:{WIDTH}px;background:transparent;font-family:House;color:#242424;
  font-variant-numeric:tabular-nums;padding:40px 0 14px}}
.t{{position:relative;display:grid;width:max-content;align-items:center;
  grid-template-columns:var(--lead) 144px max-content 24px max-content 18px repeat({len(COLUMNS)}, max-content)}}
.t > div{{height:var(--row);display:flex;align-items:center;justify-content:center;position:relative}}
.t > .h{{height:58px;font-weight:600;font-size:26px;border-bottom:2px solid #242424}}
.t > .r{{border-top:1px solid #B8B0A8}}
.t > .first{{border-top:0}}
.t > .id{{justify-content:center;flex-direction:column;align-items:flex-start}}
.id b{{font-weight:600;font-size:37px;line-height:1;white-space:nowrap}}
.id small{{font-size:25px;line-height:1;color:#5F5B57;margin-top:12px;white-space:nowrap}}
.id small i{{font-style:normal;font-weight:600}}
.rk{{font-weight:600;font-size:32px}}
.W{{color:#3FAE63}}.L{{color:#D64545}}
.face{{position:absolute;left:10px;bottom:0;width:{FACE}px;height:{FACE}px;overflow:hidden}}
.face img{{position:absolute;top:0}}
.gm{{font-weight:600;font-size:36px;color:#fff;z-index:3;padding:0 var(--cp)}}
.t > .r.gm{{border-top-color:transparent}}
.t > .h.gm{{border-bottom-color:transparent}}
.h.gm{{color:{LAKERS_PURPLE};font-size:26px}}
.v{{font-size:32px;padding:0 calc(var(--g) / 2)}}
.v.pts{{font-weight:600}}
.v.ma{{padding:0 calc(var(--s) / 2)}}
.h.v{{font-size:26px}}
.t > .card{{position:absolute;height:auto;background:{LAKERS_PURPLE};z-index:2;box-shadow:2px 2px 4px rgba(46,18,72,.25)}}
"""


def _face(player_id: int, z: int) -> str:
    """Square face crop (the top 74% of the portrait), its bottom on the row's lower rule."""
    path = HEADSHOT_CACHE / f"{player_id}.png"
    if not path.exists():
        return ""
    width, height = Image.open(path).size
    side = min(int(height * 0.74), width)
    scale = FACE / side
    left = (width - side) // 2
    return (
        f'<div class="face" style="z-index:{z}"><img src="{path.as_uri()}" '
        f'style="width:{width * scale:.1f}px;height:{height * scale:.1f}px;left:{-left * scale:.1f}px"></div>'
    )


def table_html(rows: pd.DataFrame, ranks: bool = False) -> str:
    # A tie can add a row; shorter rows keep every slide the height of a fifteen-row one.
    lead = f"--row:{108 * TOP_N / max(TOP_N, len(rows)):.2f}px;" + ("--lead:72px" if ranks else "")
    cells = ['<div class="h rk">#</div>' if ranks else '<div class="h"></div>', '<div class="h"></div>', '<div class="h id"><span>PLAYER</span></div>', '<div class="h"></div>',
             '<div class="h gm">GMSC</div>', '<div class="h"></div>']
    cells += [f'<div class="h v{" ma" if ma else ""}">{label}</div>' for label, _, ma in COLUMNS]
    for index, (_, row) in enumerate(rows.iterrows()):
        rule = "r first" if index == 0 else "r"
        date, matchup, result = base._game_context_parts(row)
        name = html.escape(base._display_name(str(row["player"])))
        cells += [
            f'<div class="{rule} rk">{row["rank_label"]}</div>' if ranks else f'<div class="{rule}"></div>',
            f'<div class="{rule}">{_face(int(row["player_id"]), 10 + index)}</div>',
            f'<div class="{rule} id"><b>{name}</b><small>{date} {html.escape(matchup)} '
            f'<i class="{result}">{result}</i></small></div>',
            f'<div class="{rule}"></div>',
            f'<div class="{rule} gm">{float(row["game_score"]):.1f}</div>',
            f'<div class="{rule}"></div>',
        ]
        for label, value, ma in COLUMNS:
            klass = " pts" if label == "PTS" else " ma" if ma else ""
            cells.append(f'<div class="{rule} v{klass}">{value(row)}</div>')
    return (f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>'
            f'<div class="t" style="{lead}">{"".join(cells)}<div class="card"></div></div>')


LAYOUT_JS = f"""() => {{
  const t = document.querySelector('.t'), root = document.documentElement.style;
  const fonts = [...document.fonts].filter(f => f.family === 'House');
  if (fonts.length < 2 || fonts.some(f => f.status !== 'loaded')) return {{error: 'Geist did not load'}};
  // Share the width left over between the stat columns: ordinary columns get one gap,
  // made-attempted columns a smaller one.
  root.setProperty('--g', '0px');
  const spare = {WIDTH} - 12 - t.getBoundingClientRect().width;
  const ordinary = document.querySelectorAll('.h.v:not(.ma)').length;
  const shooting = document.querySelectorAll('.h.v.ma').length;
  const gap = spare / (ordinary + {SHOOTING_GAP_RATIO} * shooting);
  root.setProperty('--g', gap + 'px');
  // One card spans the Game Score column from just above the header rule to below the last row.
  const nums = [...document.querySelectorAll('.r.gm')];
  const head = document.querySelector('.h.gm').getBoundingClientRect();
  const last = nums[nums.length - 1].getBoundingClientRect(), box = t.getBoundingClientRect();
  Object.assign(document.querySelector('.card').style, {{left: (head.left - box.left) + 'px',
    width: head.width + 'px', top: (head.bottom - box.top - 9) + 'px',
    height: (last.bottom - head.bottom + 9 + 9) + 'px'}});
  const below = Math.max(0, ...[...document.querySelectorAll('.face')].map(f =>
    f.getBoundingClientRect().bottom - f.parentElement.getBoundingClientRect().bottom));
  const overflow = [...t.children].some(c => c.scrollWidth > c.clientWidth + 1);
  return {{gap, width: t.getBoundingClientRect().width, below, overflow,
    height: Math.ceil(document.body.getBoundingClientRect().height)}};
}}"""


def render(page, rows: pd.DataFrame, decade: str, ranks: bool = False) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT / f"lakers-top-game-scores-{decade}.html"
    source.write_text(table_html(rows, ranks))
    page.goto(source.as_uri())
    page.evaluate("document.fonts.ready.then(() => true)")
    report = page.evaluate(LAYOUT_JS)
    if "error" in report:
        raise RuntimeError(f"{decade}: {report['error']}")
    if report["gap"] < MIN_GAP:
        raise ValueError(f"{decade}: stat columns too tight ({report['gap']:.1f}px gap).")
    if report["width"] > WIDTH or report["overflow"]:
        raise ValueError(f"{decade}: the table overflows its width.")
    if report["below"] > 0.5:
        raise ValueError(f"{decade}: a portrait reaches {report['below']:.1f}px below its row.")
    path = OUT / f"lakers-top-game-scores-{decade}.png"
    page.screenshot(path=str(path), clip={"x": 0, "y": 0, "width": WIDTH, "height": report["height"]},
                    omit_background=True)
    print(f"{path.name}: {len(rows)} rows, stat gap {report['gap']:.0f}px "
          f"(made-attempted {report['gap'] * SHOOTING_GAP_RATIO:.0f}px)")
    return path


def main() -> None:
    players, teams = base.fetch_bulls_history(first_end_year=FIRST_SEASON_END_YEAR)
    table = base.build_working_table(players, teams)
    table = table[table["minutes"] > 0]
    report = validate(table)
    ranked = report["ranked"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(DATA_DIR / "lakers_top15_by_decade.csv", index=False)
    eras = {label: era_slides(report["table"], first) for label, first in ERAS.items()}
    shown = {i for top, rest in eras.values() for i in pd.concat([top, rest])["game_id"]}
    if shown & set(report["flagged_games"]):
        raise ValueError(f"A flagged game reached an era list: {sorted(shown & set(report['flagged_games']))}.")
    for label, (top, rest) in eras.items():
        pd.concat([top, rest]).to_csv(DATA_DIR / f"lakers_top30_{label.replace('-', '_')}.csv", index=False)
        print(f"{label}: ranks {top['rank_label'].iloc[0]}-{rest['rank_label'].iloc[-1]}, {len(top) + len(rest)} rows")
    ensure_headshots(ranked["player_id"].tolist() + [
        int(i) for top, rest in eras.values() for i in pd.concat([top, rest])["player_id"]])
    print(
        f"{report['player_games']} player-games, {report['games']} games, {report['seasons']} seasons; "
        f"rows per decade {report['counts']}; flagged NBA.com games (none shown): {report['flagged_games']}"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 2400}, device_scale_factor=2)
        for decade in DECADES:
            render(page, ranked.loc[ranked["decade"].eq(decade)], decade)
        for label, (top, rest) in eras.items():
            render(page, top, f"top30-{label}-1-15", ranks=True)
            render(page, rest, f"top30-{label}-16-30", ranks=True)
        browser.close()


if __name__ == "__main__":
    main()
