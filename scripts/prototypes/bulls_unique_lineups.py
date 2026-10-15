"""Unique five-man lineups the Bulls used each regular season, 2000-01 to 2025-26: bars, with each season's win % as a dashed line over them.

Run from the repo root:
    venv/bin/python scripts/prototypes/bulls_unique_lineups.py            # tables + chart from saved snapshots
    venv/bin/python scripts/prototypes/bulls_unique_lineups.py --fetch    # fetch missing snapshots first

NBA.com LeagueDashLineups has lineups only from 2007-08, so 2000-01 to 2006-07 come from pbpstats.
pbpstats /get-totals returns at most 500 rows, sorted by minutes, so a full-season request silently
drops a team's rarest lineups; it is requested per calendar month, split further at the cap. Every
season's lineup minutes must equal the team's minutes. League context (2024-25, 2025-26) is fetched
team by team into the untracked cache/ folder.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from nba_api.stats.endpoints import leaguedashlineups, leaguedashteamstats  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from bulls.data.fetch import _NBA_HEADERS  # noqa: E402

PROJECT = "bulls-unique-lineups"
DATA = _REPO / "docs" / "visuals" / f"2026-10-14-{PROJECT}" / "data"
PBPSTATS_SNAPSHOTS = DATA / "pbpstats-month-windows"
NBA_SNAPSHOTS = DATA / "nba-leaguedashlineups"
NBA_TEAM_MINUTES = DATA / "nba-bulls-team-minutes.csv"
LEAGUE_CACHE = _REPO / "cache" / "nba_league_lineups"
LEAGUE_SEASONS = ["2024-25", "2025-26"]
SEASON_RECORDS = DATA / "nba-bulls-season-records.csv"
OUT = _REPO / "output" / PROJECT
FONTS = Path.home() / "Library" / "Fonts"

API_ROOT = "https://api.pbpstats.com"
PBPSTATS_ROW_CAP = 500
BULLS_TEAM_ID = 1610612741
FIRST_SEASON = 2000
LAST_SEASON = 2025
NBA_FIRST_SEASON = 2007
MINUTE_FLOORS = [1, 2, 3, 4, 5, 10]
SELECTED_FLOOR = 3
CHART_WIDTH = 1030
BAR_HEIGHT = 28
ROW_GAP = 12
VALUE_SPACE = 70
RENDER_SCALE = 3
SEASON_COLUMN = 112
WIN_TICKS = (0.25, 0.5, 0.75)
WIN_GREEN = "#2E8540"
TEAM_MINUTE_TOLERANCE = 1.0


def season_label(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def get_json(path: str, params: dict, attempts: int = 8) -> dict:
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(f"{API_ROOT}{path}", params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            if attempt == attempts:
                raise
            time.sleep(3 * attempt)
    raise AssertionError("unreachable")


def month_windows(start_year: int) -> list[tuple[date, date]]:
    windows, first = [], date(start_year, 10, 1)
    while first < date(start_year + 1, 9, 1):
        next_first = date(first.year + first.month // 12, first.month % 12 + 1, 1)
        windows.append((first, next_first - timedelta(days=1)))
        first = next_first
    return windows


def fetch_window(season: str, start: date, end: date) -> list[dict]:
    params = {
        "Season": season, "SeasonType": "Regular Season", "Type": "Lineup", "TeamId": str(BULLS_TEAM_ID),
        "FromDate": start.isoformat(), "ToDate": end.isoformat(),
    }
    rows = get_json("/get-totals/nba", params).get("multi_row_table_data", [])
    time.sleep(0.5)
    if len(rows) < PBPSTATS_ROW_CAP:
        return [{"FromDate": params["FromDate"], "ToDate": params["ToDate"], "Rows": rows}]
    if start == end:
        raise ValueError(f"{season} {start}: a single day returned the {PBPSTATS_ROW_CAP}-row cap")
    middle = start + (end - start) // 2
    return fetch_window(season, start, middle) + fetch_window(season, middle + timedelta(days=1), end)


def fetch_team_seconds(season: str) -> float:
    params = {"Season": season, "SeasonType": "Regular Season", "Type": "Team"}
    rows = get_json("/get-totals/nba", params)["multi_row_table_data"]
    (bulls,) = [row for row in rows if str(row.get("TeamId")) == str(BULLS_TEAM_ID)]
    return float(bulls["SecondsPlayed"])


def fetch_pbpstats_season(start_year: int) -> None:
    season = season_label(start_year)
    path = PBPSTATS_SNAPSHOTS / f"{season}.json"
    if path.is_file():
        return
    windows = []
    for start, end in month_windows(start_year):
        windows += fetch_window(season, start, end)
    snapshot = {"source": f"{API_ROOT}/get-totals/nba", "season": season,
                "team_seconds": fetch_team_seconds(season), "windows": windows}
    path.write_text(json.dumps(snapshot, indent=1) + "\n")
    print(f"pbpstats {season}: {len(windows)} windows")


def fetch_nba_season(start_year: int) -> None:
    season = season_label(start_year)
    path = NBA_SNAPSHOTS / f"{season}.csv"
    if path.is_file():
        return
    frame = leaguedashlineups.LeagueDashLineups(
        group_quantity=5, team_id_nullable=BULLS_TEAM_ID, season=season,
        season_type_all_star="Regular Season", per_mode_detailed="Totals",
        measure_type_detailed_defense="Base", timeout=60, headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    frame[["GROUP_ID", "GROUP_NAME", "GP", "MIN"]].to_csv(path, index=False)
    print(f"NBA.com {season}: {len(frame)} lineups")
    time.sleep(1.0)


def pbpstats_lineups(season: str) -> tuple[pd.DataFrame, float]:
    snapshot = json.loads((PBPSTATS_SNAPSHOTS / f"{season}.json").read_text())
    rows = [
        {"EntityId": str(row["EntityId"]), "Name": row.get("Name"), "Seconds": float(row.get("SecondsPlayed") or 0)}
        for window in snapshot["windows"] for row in window["Rows"]
    ]
    lineups = (pd.DataFrame(rows).groupby("EntityId", as_index=False)
               .agg(Name=("Name", "first"), Seconds=("Seconds", "sum")))
    if (lineups["EntityId"].str.count("-") != 4).any():
        raise ValueError(f"{season}: a pbpstats lineup id is not five players")
    return lineups, snapshot["team_seconds"]


def season_lineup_minutes(start_year: int) -> tuple[pd.Series, str]:
    season = season_label(start_year)
    if start_year < NBA_FIRST_SEASON:
        lineups, team_seconds = pbpstats_lineups(season)
        minutes, team_minutes, source = lineups["Seconds"] / 60, team_seconds / 60, "pbpstats"
    else:
        minutes = pd.read_csv(NBA_SNAPSHOTS / f"{season}.csv")["MIN"]
        team_minutes = pd.read_csv(NBA_TEAM_MINUTES).set_index("Season").loc[season, "TeamMIN"]
        source = "NBA.com"
    if abs(minutes.sum() - team_minutes) > TEAM_MINUTE_TOLERANCE:
        raise ValueError(f"{season}: lineup minutes {minutes.sum():.1f} != team minutes {team_minutes:.1f}")
    return minutes, source


def lineup_counts(minutes: pd.Series) -> dict[str, int]:
    counts = {"Played": int((minutes > 0).sum())}
    counts.update({f"Min{floor}": int((minutes >= floor).sum()) for floor in MINUTE_FLOORS})
    return counts


def sensitivity_table() -> pd.DataFrame:
    records = []
    for start_year in range(FIRST_SEASON, LAST_SEASON + 1):
        minutes, source = season_lineup_minutes(start_year)
        records.append({"Season": season_label(start_year), "Source": source, **lineup_counts(minutes)})
    return pd.DataFrame(records)


def source_overlap_table() -> pd.DataFrame:
    """Seasons fetched from both sources; pbpstats omits NBA.com's zero-minute listings."""
    records = []
    for path in sorted(PBPSTATS_SNAPSHOTS.glob("*.json")):
        season = path.stem
        if not (NBA_SNAPSHOTS / f"{season}.csv").is_file():
            continue
        pbp, _ = pbpstats_lineups(season)
        nba = pd.read_csv(NBA_SNAPSHOTS / f"{season}.csv")
        pbp_ids = set(pbp["EntityId"].map(player_set))
        nba = nba.assign(Players=nba["GROUP_ID"].map(player_set))
        records.append({
            "Season": season, "pbpstats": len(pbp_ids), "NBA.com": len(nba),
            "Shared": len(pbp_ids & set(nba["Players"])),
            "NbaOnlyMaxMinutes": round(nba.loc[~nba["Players"].isin(pbp_ids), "MIN"].max(), 3) if len(nba) > len(pbp_ids) else 0,
            f"pbpstats{SELECTED_FLOOR}Min": int((pbp["Seconds"] >= SELECTED_FLOOR * 60).sum()),
            f"NBA.com{SELECTED_FLOOR}Min": int((nba["MIN"] >= SELECTED_FLOOR).sum()),
        })
    return pd.DataFrame(records)


def player_set(group_id: str) -> frozenset[str]:
    return frozenset(player for player in str(group_id).split("-") if player)


def fetch_league_season(season: str) -> None:
    folder = LEAGUE_CACHE / season
    folder.mkdir(parents=True, exist_ok=True)
    teams = leaguedashteamstats.LeagueDashTeamStats(
        season=season, season_type_all_star="Regular Season", per_mode_detailed="Totals",
        timeout=60, headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    teams[["TEAM_ID", "TEAM_NAME", "GP", "MIN"]].to_csv(folder / "teams.csv", index=False)
    for team_id in teams["TEAM_ID"]:
        path = folder / f"{team_id}.csv"
        if path.is_file():
            continue
        frame = leaguedashlineups.LeagueDashLineups(
            group_quantity=5, team_id_nullable=int(team_id), season=season,
            season_type_all_star="Regular Season", per_mode_detailed="Totals",
            measure_type_detailed_defense="Base", timeout=60, headers=_NBA_HEADERS,
        ).get_data_frames()[0]
        frame[["TEAM_ID", "GROUP_ID", "MIN"]].to_csv(path, index=False)
        time.sleep(0.8)


def league_table() -> pd.DataFrame:
    """Every team's counts; LeagueDashLineups caps a league-wide request at 2,000 rows, so teams are fetched one by one."""
    records = []
    for season in LEAGUE_SEASONS:
        teams = pd.read_csv(LEAGUE_CACHE / season / "teams.csv")
        for team in teams.itertuples():
            minutes = pd.read_csv(LEAGUE_CACHE / season / f"{team.TEAM_ID}.csv")["MIN"]
            if abs(minutes.sum() - team.MIN) > TEAM_MINUTE_TOLERANCE:
                raise ValueError(f"{season} {team.TEAM_NAME}: lineup minutes do not match team minutes")
            records.append({"Season": season, "Team": team.TEAM_NAME, **lineup_counts(minutes)})
    return pd.DataFrame(records)


def chart_html(table: pd.DataFrame) -> str:
    column = f"Min{SELECTED_FLOOR}"
    highlight = season_label(LAST_SEASON)
    top = table[column].max()
    pitch = BAR_HEIGHT + ROW_GAP
    rows_height = len(table) * pitch - ROW_GAP
    track_width = CHART_WIDTH - SEASON_COLUMN - VALUE_SPACE
    wx = lambda v: v * track_width
    wy = lambda i: i * pitch + BAR_HEIGHT / 2
    points = [(wx(row.WinPct), wy(i)) for i, (_, row) in enumerate(table.iterrows())]
    win_line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    ticks = "".join(
        f'<line x1="{wx(v):.1f}" x2="{wx(v):.1f}" y1="{rows_height + 6}" y2="{rows_height + 16}" class="tk"/>'
        f'<text x="{wx(v):.1f}" y="{rows_height + 42}" text-anchor="middle" class="wt">{v:.0%}</text>'
        for v in WIN_TICKS
    )
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="d"/>' for x, y in points)
    overlay = (f'<svg class="win" width="{track_width}" height="{rows_height + 48}">'
               f'<path d="{win_line}" class="halo"/><path d="{win_line}" class="wl"/>{dots}{ticks}</svg>')
    rows = "".join(
        f'<div class="s">{row.Season}</div><div class="track"><div class="bar{" hi" if row.Season == highlight else ""}" '
        f'style="width:{row[column] / top * 100:.3f}%"></div><span class="v">{row[column]}</span></div>'
        for _, row in table.iterrows()
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:House;font-weight:600;src:local('Geist-SemiBold'),url('file://{FONTS}/Geist-SemiBold.otf')}}
*{{box-sizing:border-box;margin:0}}
body{{width:{CHART_WIDTH}px;background:transparent;font-family:House;font-weight:600;color:#242424;
  font-variant-numeric:tabular-nums;padding:8px 0}}
.key{{display:flex;gap:32px;align-items:center;font-size:22px;color:#645D57;height:44px;padding-left:{SEASON_COLUMN}px}}
.key span{{display:flex;align-items:center;gap:10px}}.key i{{display:inline-block;width:30px;height:16px;background:#242424}}
.key svg{{overflow:visible}}
.body{{position:relative}}
.grid{{display:grid;grid-template-columns:{SEASON_COLUMN}px 1fr;grid-auto-rows:{BAR_HEIGHT}px;align-items:center;row-gap:{ROW_GAP}px}}
.s{{font-size:24px;line-height:{BAR_HEIGHT}px}}
.track{{position:relative;height:{BAR_HEIGHT}px;margin-right:{VALUE_SPACE}px;display:flex;align-items:center}}
.bar{{height:100%;background:#242424}}.bar.hi{{background:#CE1141}}
.v{{font-size:24px;line-height:1;padding-left:10px;white-space:nowrap;position:relative;z-index:1;paint-order:stroke;-webkit-text-stroke:6px #E9E5E1}}
.track:has(.hi) .v{{color:#CE1141}}
svg.win{{position:absolute;top:0;left:{SEASON_COLUMN}px;overflow:visible}}
.halo{{fill:none;stroke:#E9E5E1;stroke-width:8;stroke-linejoin:round}}
.wl{{fill:none;stroke:{WIN_GREEN};stroke-width:3.5;stroke-dasharray:9 7;stroke-linejoin:round}}
.d,.kd{{fill:{WIN_GREEN};stroke:#E9E5E1;stroke-width:3}}.tk{{stroke:{WIN_GREEN};stroke-width:2}}
.wt{{font-size:22px;fill:{WIN_GREEN}}}
</style></head><body>
<div class="key"><span><i></i>Lineups with 3+ minutes</span><span><svg width="34" height="16"><line x1="0" x2="34" y1="8" y2="8" class="wl"/><circle cx="17" cy="8" r="7" class="kd"/></svg>Win %</span></div>
<div class="body"><div class="grid">{rows}</div>{overlay}</div><div style="height:48px"></div></body></html>"""


def fetch_season_records() -> None:
    records, team_minutes = [], []
    for start_year in range(FIRST_SEASON, LAST_SEASON + 1):
        season = season_label(start_year)
        teams = leaguedashteamstats.LeagueDashTeamStats(
            team_id_nullable=BULLS_TEAM_ID, season=season, season_type_all_star="Regular Season",
            per_mode_detailed="Totals", timeout=60, headers=_NBA_HEADERS,
        ).get_data_frames()[0]
        bulls = teams[teams["TEAM_ID"] == BULLS_TEAM_ID].iloc[0]
        records.append({"Season": season, "GP": int(bulls["GP"]), "W": int(bulls["W"]), "L": int(bulls["L"]),
                        "WinPct": round(bulls["W"] / bulls["GP"], 4)})
        if start_year >= NBA_FIRST_SEASON:
            team_minutes.append({"Season": season, "GP": int(bulls["GP"]), "TeamMIN": float(bulls["MIN"])})
        time.sleep(0.8)
    pd.DataFrame(records).to_csv(SEASON_RECORDS, index=False)
    pd.DataFrame(team_minutes).to_csv(NBA_TEAM_MINUTES, index=False)


def with_records(table: pd.DataFrame) -> pd.DataFrame:
    records = pd.read_csv(SEASON_RECORDS)
    if not (records["W"] + records["L"] == records["GP"]).all():
        raise ValueError("A season's wins and losses do not sum to games played")
    merged = table.merge(records, on="Season", how="left", validate="one_to_one")
    if merged["WinPct"].isna().any():
        raise ValueError("A lineup season has no win-loss record")
    return merged


def render_asset(html: str, name: str, overflow_selector: str | None = None) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    html_path = OUT / f"{name}.html"
    html_path.write_text(html)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": CHART_WIDTH, "height": 1600}, device_scale_factor=RENDER_SCALE)
        page.goto(html_path.as_uri())
        page.evaluate("document.fonts.ready")
        report = page.evaluate("""(selector) => {
            const width = document.body.clientWidth;
            const boxes = [...document.querySelectorAll('.lb')].map(e => [e.textContent, e.getBoundingClientRect()]);
            const dots = [...document.querySelectorAll('.d')].map(e => e.getBoundingClientRect());
            const hit = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
            return {
                height: Math.ceil(document.body.getBoundingClientRect().height),
                overflow: selector ? [...document.querySelectorAll(selector)].filter(v => v.getBoundingClientRect().right > width).map(v => v.textContent) : [],
                labelOverlaps: boxes.flatMap(([n, a], i) => boxes.slice(i + 1).filter(([, b]) => hit(a, b)).map(([m]) => n + '/' + m)),
                labelsOnDots: boxes.filter(([, a]) => dots.some(d => hit(a, d))).map(([n]) => n)
                    .concat([...document.querySelectorAll('.v')].filter(v => dots.some(d => hit(v.getBoundingClientRect(), d))).map(v => 'value ' + v.textContent)),
                labelsOut: boxes.filter(([, a]) => a.left < 0 || a.right > width).map(([n]) => n),
                rowDrift: (() => {
                    const bars = [...document.querySelectorAll('.track')].map(e => e.getBoundingClientRect());
                    const marks = [...document.querySelectorAll('.d')].map(e => e.getBoundingClientRect());
                    if (!marks.length) return [];
                    if (marks.length !== bars.length) return ['mark count ' + marks.length + ' != rows ' + bars.length];
                    return bars.map((b, i) => Math.abs((b.top + b.bottom) / 2 - (marks[i].top + marks[i].bottom) / 2))
                               .map((d, i) => [i, d]).filter(([, d]) => d > 1).map(([i, d]) => 'row ' + i + ' off by ' + d.toFixed(1));
                })(),
                geist: document.fonts.check('600 24px House') && [...document.fonts].some(f => f.status === 'loaded'),
            };
        }""", overflow_selector)
        problems = {k: report[k] for k in ("overflow", "labelOverlaps", "labelsOnDots", "labelsOut", "rowDrift") if report[k]}
        if problems:
            raise ValueError(f"{name}: layout problems {problems}")
        if not report["geist"]:
            raise ValueError("Geist did not load")
        path = OUT / f"{name}.png"
        page.screenshot(path=str(path), clip={"x": 0, "y": 0, "width": CHART_WIDTH, "height": report["height"]}, omit_background=True)
        browser.close()
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="Fetch any missing pbpstats, NBA.com and league snapshots.")
    args = parser.parse_args()
    if args.fetch:
        PBPSTATS_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        NBA_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        for start_year in range(FIRST_SEASON, NBA_FIRST_SEASON):
            fetch_pbpstats_season(start_year)
        for start_year in range(NBA_FIRST_SEASON, LAST_SEASON + 1):
            fetch_nba_season(start_year)
        for season in LEAGUE_SEASONS:
            fetch_league_season(season)
        fetch_season_records()
    table = sensitivity_table()
    table.to_csv(DATA / "bulls-unique-lineups-by-floor.csv", index=False)
    source_overlap_table().to_csv(DATA / "source-overlap-audit.csv", index=False)
    league = league_table()
    league.to_csv(DATA / "league-unique-lineups-by-team.csv", index=False)
    print(table.to_string(index=False))
    print(league.groupby("Season")[f"Min{SELECTED_FLOOR}"].describe().round(1).to_string())
    charted = with_records(table)
    charted[["Season", "Source", f"Min{SELECTED_FLOOR}", "GP", "W", "L", "WinPct"]].to_csv(DATA / "bulls-lineups-and-win-pct.csv", index=False)
    print(f"Correlation, win % vs lineups ({SELECTED_FLOOR}+ min): {charted[f'Min{SELECTED_FLOOR}'].corr(charted['WinPct']):.2f}")
    print(render_asset(chart_html(charted), "chart", overflow_selector=".v"))


if __name__ == "__main__":
    main()
