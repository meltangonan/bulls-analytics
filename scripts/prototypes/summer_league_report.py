"""Render a player-led Bulls Summer League Report from a completed NBA game.

Game-night flow:
1. Run with no arguments to auto-resolve the latest completed Bulls Summer
   League game and review player box scores, role share, plus/minus, and
   shot-diet inputs.
2. In the clarification pass, choose one to three players and assign each the
   lens that tells the clearest story: ``shot_diet``, ``role``, or ``impact``.
3. Re-run with matching ``--player`` and ``--lens`` values to render the post.

The script refuses to render a game that is not yet final, so it is safe to run
while the game is still being played.

Example:
    venv/bin/python scripts/prototypes/summer_league_report.py \
      --player "Caleb Wilson" --lens shot_diet \
      --player "Dailyn Swain" --lens impact
"""
import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Arc, Circle, FancyBboxPatch
from nba_api.stats.endpoints import (
    boxscoresummaryv3,
    boxscoretraditionalv3,
    leaguegamefinder,
)

from bulls.config import BULLS_TEAM_ID, NBA_TEAMS
from bulls.data.fetch import _NBA_HEADERS, get_game_shots, get_player_headshot
from bulls.graphics.craft import headshot_label
from bulls.graphics.feed import (
    DEFAULT_DPI,
    INSTAGRAM_FEED_HEIGHT_PX as H,
    INSTAGRAM_FEED_WIDTH_PX as W,
    save_feed_post,
)

INK = "#1A1A1A"
MUTED = "#777777"
FAINT = "#AAAAAA"
RED = "#CE1141"
RULE = "#DDDDDD"
PALE_RED = "#F7E8ED"
PANEL_RED = "#FAF1F4"  # lighter wash for large court panels
CHIP_GRAY = "#F4F4F4"  # stat-chip containers (scaffolding, not meaning)
COURT_LINE = "#C9A8B5"  # warm court lines on the pale panels
DISPLAY_FONT = _REPO / "assets" / "fonts" / "AcademicM54.ttf"
BODY_FONTS = {
    "regular": _REPO / "assets" / "fonts" / "Archivo-400.ttf",
    "medium": _REPO / "assets" / "fonts" / "Archivo-500.ttf",
    "bold": _REPO / "assets" / "fonts" / "Archivo-600.ttf",
}
OUTPUT_DIR = _REPO / "output" / "feed"
LENSES = ("shot_diet", "role", "impact")
SUMMER_LEAGUE_LEAGUE_ID = "15"

# The NBA labels every shot with its own zone, the same ones a shot chart draws.
# Any zone not listed here -- both corner threes, above the break, backcourt --
# is a three.
SHOT_ZONE_BUCKETS = {
    "Restricted Area": "rim",
    "In The Paint (Non-RA)": "paint",
    "Mid-Range": "mid",
}

# Every other NBA nickname is the last word of the team name.
TWO_WORD_NICKNAMES = ("Trail Blazers",)

PLAYER_ROW_HEIGHT = 173
STORIES_TOP = 795


def _fp_display():
    return fm.FontProperties(fname=str(DISPLAY_FONT))


def _fp_body(weight="regular"):
    return fm.FontProperties(fname=str(BODY_FONTS[weight]))


def _number(value) -> float:
    """Return an NBA response value as a safe number for display math."""
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def _player_name(row: pd.Series) -> str:
    return f"{row['firstName']} {row['familyName']}"


def minutes_played(player: pd.Series) -> int:
    """Whole minutes from either clock format NBA.com uses ('22:34' or 'PT22M34.00S')."""
    raw = str(player.get("minutes") or "").strip()
    if raw.startswith("PT"):
        raw = raw[2:].split("M")[0]
    else:
        raw = raw.split(":")[0]
    try:
        return int(float(raw))
    except ValueError:
        return 0


def find_latest_bulls_game(season: str) -> tuple[str, str]:
    """Resolve the most recent completed Bulls Summer League game for a season."""
    games = leaguegamefinder.LeagueGameFinder(
        league_id_nullable=SUMMER_LEAGUE_LEAGUE_ID,
        season_nullable=season,
        team_id_nullable=BULLS_TEAM_ID,
        timeout=30,
        headers=_NBA_HEADERS,
    ).get_data_frames()[0]
    if games.empty:
        raise SystemExit(
            f"No completed Bulls Summer League games found for {season}. "
            "NBA.com lists a game only once it is final; pass --game-id to override."
        )
    latest = games.sort_values("GAME_DATE").iloc[-1]
    return str(latest["GAME_ID"]), f"{latest['MATCHUP']} on {latest['GAME_DATE']} ({latest['WL']})"


def fetch_game_summary(game_id: str) -> dict:
    """Fetch the game header, which carries the final/in-progress status."""
    return boxscoresummaryv3.BoxScoreSummaryV3(
        game_id=game_id,
        timeout=30,
        headers=_NBA_HEADERS,
    ).get_dict()["boxScoreSummary"]


def require_final(summary: dict, game_id: str) -> None:
    """Refuse to render a game still in progress, which would publish partial numbers."""
    if summary.get("gameStatus") != 3:
        status = str(summary.get("gameStatusText", "unknown")).strip()
        raise SystemExit(f"Game {game_id} is not final (status: {status}). Wait for the buzzer.")


def game_day(summary: dict) -> date:
    """The day the game was played, so a post rendered after midnight still dates it right."""
    stamp = str(summary.get("gameEt") or summary.get("gameTimeUTC") or "")
    if len(stamp) >= 10:
        return date.fromisoformat(stamp[:10])
    return date.today()


def fetch_game_data(game_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch player totals, team totals, and zoned Bulls shots for one completed game."""
    box = boxscoretraditionalv3.BoxScoreTraditionalV3(
        game_id=game_id,
        timeout=30,
        headers=_NBA_HEADERS,
    )
    players = box.player_stats.get_data_frame()
    teams = box.team_stats.get_data_frame()
    if players.empty or teams.empty:
        raise ValueError(f"NBA.com returned no completed box score for game {game_id}.")
    shots = get_game_shots(game_id)
    if shots.empty:
        # The shot chart can lag the box score right after the buzzer; only the
        # shot_diet lens needs it, so degrade instead of blocking the whole post.
        print("Warning: no shot chart yet for this game; the shot_diet lens is unavailable.")
    return players, teams, shots


def team_nickname(tricode: str) -> str:
    """Return 'Grizzlies' for 'MEM' so the subtitle reads 'Bulls 98 · Grizzlies 91'."""
    full_name = NBA_TEAMS.get(tricode, {}).get("name", tricode)
    for nickname in TWO_WORD_NICKNAMES:
        if full_name.endswith(nickname):
            return nickname
    return full_name.rsplit(" ", 1)[-1]


def shot_diet(shots: pd.DataFrame, player_id: int | None) -> Counter:
    """Group field-goal attempts by the NBA's own shot zones.

    These are the zones a shot chart draws, so a 14-ft baseline fadeaway lands in
    Mid-Range where the NBA puts it, not in the paint it never entered. Pass
    ``player_id=None`` for the whole team's attempts.
    """
    buckets = Counter({"rim": 0, "paint": 0, "mid": 0, "three": 0})
    zones = shots["shot_zone"] if player_id is None else shots.loc[shots["player_id"] == player_id, "shot_zone"]
    for zone in zones:
        buckets[SHOT_ZONE_BUCKETS.get(zone, "three")] += 1
    return buckets


def shot_diet_line(shots: pd.DataFrame, player_id: int | None) -> str:
    diet = shot_diet(shots, player_id)
    total = sum(diet.values())
    if not total:
        return "NO FIELD-GOAL ATTEMPTS"
    return f"{diet['rim'] + diet['paint']} RIM/PAINT · {diet['mid']} MID · {diet['three']} 3PT"


def zone_splits(shots: pd.DataFrame, player_id: int | None) -> dict[str, tuple[int, int]]:
    """Makes and attempts per shot-zone group, from the NBA's own zone labels."""
    rows = shots if player_id is None else shots[shots["player_id"] == player_id]
    splits = {"rim_paint": [0, 0], "mid": [0, 0], "three": [0, 0]}
    for _, shot in rows.iterrows():
        bucket = SHOT_ZONE_BUCKETS.get(shot["shot_zone"], "three")
        key = "rim_paint" if bucket in ("rim", "paint") else ("mid" if bucket == "mid" else "three")
        splits[key][1] += 1
        splits[key][0] += int(bool(shot["shot_made"]))
    return {key: tuple(pair) for key, pair in splits.items()}


def efg_pct(player: pd.Series) -> float:
    attempts = _number(player.get("fieldGoalsAttempted"))
    if not attempts:
        return 0.0
    return 100 * (
        _number(player.get("fieldGoalsMade"))
        + 0.5 * _number(player.get("threePointersMade"))
    ) / attempts


def role_share_pct(player: pd.Series, team: pd.Series) -> float:
    attempts = _number(team.get("fieldGoalsAttempted"))
    if not attempts:
        return 0.0
    return 100 * _number(player.get("fieldGoalsAttempted")) / attempts


def plus_minus(player: pd.Series) -> int:
    return int(round(_number(player.get("plusMinusPoints", player.get("plusMinus")))))


def lens_copy(lens: str, player: pd.Series, team: pd.Series, shots: pd.DataFrame) -> tuple[str, str]:
    if lens == "shot_diet":
        return "HOW HE SCORED", shot_diet_line(shots, int(player["personId"]))
    if lens == "role":
        return "THE ROLE", f"{role_share_pct(player, team):.0f}% OF BULLS FGA"
    if lens == "impact":
        return "THE IMPACT", f"BULLS {plus_minus(player):+d} IN HIS MINUTES"
    raise ValueError(f"Unknown lens: {lens}")


def player_candidates(players: pd.DataFrame, team: pd.Series) -> pd.DataFrame:
    """Create the game-night review table without choosing the editorial stories."""
    candidates = players.copy()
    candidates["name"] = candidates.apply(_player_name, axis=1)
    candidates["FG"] = candidates.apply(
        lambda p: f"{int(_number(p['fieldGoalsMade']))}-{int(_number(p['fieldGoalsAttempted']))}", axis=1
    )
    candidates["3PT"] = candidates.apply(
        lambda p: f"{int(_number(p['threePointersMade']))}-{int(_number(p['threePointersAttempted']))}", axis=1
    )
    candidates["+/-"] = candidates.apply(plus_minus, axis=1)
    candidates["FGA share"] = candidates.apply(lambda p: f"{role_share_pct(p, team):.0f}%", axis=1)
    candidates["eFG%"] = candidates.apply(lambda p: f"{efg_pct(p):.1f}%", axis=1)
    return candidates[
        ["name", "points", "FG", "3PT", "reboundsTotal", "assists", "+/-", "FGA share", "eFG%"]
    ].sort_values(["points", "reboundsTotal", "assists"], ascending=False)


def select_players(players: pd.DataFrame, names: list[str]) -> list[pd.Series]:
    selected = []
    for name in names:
        matches = players[players.apply(_player_name, axis=1).str.casefold() == name.casefold()]
        if matches.empty:
            available = ", ".join(players.apply(_player_name, axis=1).tolist())
            raise ValueError(f"Could not find '{name}'. Available Bulls: {available}")
        selected.append(matches.iloc[0])
    return selected


def _data_width(ax, text_obj) -> float:
    ax.figure.canvas.draw()
    bbox = text_obj.get_window_extent()
    inverse = ax.transData.inverted()
    x0, _ = inverse.transform((bbox.x0, bbox.y0))
    x1, _ = inverse.transform((bbox.x1, bbox.y0))
    return x1 - x0


def _draw_title(ax, segments):
    x, y, max_width, base_size = 60, H - 66, W - 120, 86
    probe = ax.text(
        x,
        y,
        "".join(text for text, _ in segments),
        ha="left",
        va="top",
        fontsize=base_size,
        fontproperties=_fp_display(),
        alpha=0,
    )
    size = base_size * max_width / _data_width(ax, probe)
    probe.remove()
    for text, color in segments:
        item = ax.text(
            x,
            y,
            text,
            ha="left",
            va="top",
            fontsize=size,
            color=color,
            fontproperties=_fp_display(),
        )
        x += _data_width(ax, item)


def _draw_subtitle(ax, parts: list[tuple[str, str]], y: float):
    x = 60
    for index, (text, color) in enumerate(parts):
        item = ax.text(
            x,
            y,
            text,
            ha="left",
            va="top",
            fontsize=18,
            color=color,
            fontproperties=_fp_body("bold"),
        )
        x += _data_width(ax, item)
        if index < len(parts) - 1:
            x += 13
            ax.plot([x, x], [y - 21, y - 5], color="#CFCFCF", lw=1.3)
            x += 13


def _fitted_text(ax, x, y, text, fp, base_size, max_width, color, ha="left", va="top"):
    """Draw text at base_size, shrinking only if it would overflow max_width."""
    probe = ax.text(x, y, text, ha=ha, va=va, fontsize=base_size, fontproperties=fp, alpha=0)
    width = _data_width(ax, probe)
    probe.remove()
    size = base_size if width <= max_width else base_size * max_width / width
    return ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=color, fontproperties=fp)


def _stat_chip(ax, x, y_top, w, h, value, label, value_size=14.5, value_color=INK):
    """One stat in its own small container: bold value over a muted label."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y_top - h),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=10",
            facecolor=CHIP_GRAY,
            edgecolor="none",
        )
    )
    cx = x + w / 2
    ax.text(cx, y_top - h * 0.35, value, ha="center", va="center", fontsize=value_size, color=value_color, fontproperties=_fp_body("bold"))
    ax.text(cx, y_top - h * 0.72, label, ha="center", va="center", fontsize=8.5, color=MUTED, fontproperties=_fp_body("bold"))


def _chip_row(ax, chips: list[tuple[str, str, str]], x, y_top, w, h, gap, value_size=14.5):
    """A row of stat chips; each entry is (value, label, value_color)."""
    for index, (value, label, color) in enumerate(chips):
        _stat_chip(ax, x + index * (w + gap), y_top, w, h, value, label, value_size, value_color=color)


def _display_name(player: pd.Series) -> str:
    """Name for the Academic M54 face, which has no hyphen glyph."""
    return _player_name(player).upper().replace("-", " ")


def _headshot_path(player: pd.Series):
    """Cached NBA CDN headshot; warn when the CDN only has the gray silhouette."""
    path = get_player_headshot(int(player["personId"]))
    if path is not None and path.stat().st_size < 20_000:
        print(
            f"Warning: headshot for {_player_name(player)} looks like the CDN silhouette "
            f"({path.stat().st_size // 1024} KB); consider a team-CDN crop."
        )
    return path


def _draw_team_snapshot(ax, team: pd.Series):
    y_top, y_bottom = 1030, 885
    ax.add_patch(
        FancyBboxPatch(
            (60, y_bottom),
            W - 120,
            y_top - y_bottom,
            boxstyle="round,pad=0,rounding_size=10",
            facecolor=PALE_RED,
            edgecolor="none",
        )
    )
    ax.text(84, y_top - 27, "TEAM SNAPSHOT", ha="left", va="top", fontsize=11, color=RED, fontproperties=_fp_body("bold"))
    stats = [
        (f"{int(_number(team['fieldGoalsMade']))}-{int(_number(team['fieldGoalsAttempted']))}", "FG"),
        (f"{int(_number(team['threePointersMade']))}-{int(_number(team['threePointersAttempted']))}", "3PT"),
        (str(int(_number(team["reboundsTotal"]))), "REB"),
        (str(int(_number(team["turnovers"]))), "TO"),
    ]
    stat_width = (W - 168) / len(stats)
    for index, (value, label) in enumerate(stats):
        x = 84 + stat_width * index
        if index:
            ax.plot([x - 18, x - 18], [y_bottom + 22, y_top - 56], color="#E6C4CF", lw=1)
        ax.text(x, y_top - 75, value, ha="left", va="top", fontsize=29, color=INK, fontproperties=_fp_body("bold"))
        ax.text(x, y_top - 125, label, ha="left", va="top", fontsize=11, color=MUTED, fontproperties=_fp_body("bold"))


def _draw_shot_map(
    ax,
    shots: pd.DataFrame,
    player_id: int | None,
    right: float,
    y_center: float,
    s: float = 0.42,
    line_color: str = "#CFCFCF",
    miss_as_x: bool = False,
    draw_legend: bool = True,
):
    """Draw a half-court with attempts, hoop at the bottom.

    Shot-chart coordinates are tenths of a foot with the hoop at the origin:
    court 500 wide, baseline at y=-47.5, paint |x|<=80 up to y=142.5, three-point
    arc radius 237.5 meeting the corner lines at x=+/-220. ``s`` scales the
    500-unit court width (0.42 -> 210 px card inset; 1.5 -> 750 px slide court).
    ``player_id=None`` plots the whole team's attempts.
    """
    player_shots = shots if player_id is None else shots[shots["player_id"] == player_id]
    if player_shots.empty:
        return
    top_y = 280  # court window shown; deeper heaves are clamped to the edge
    x0 = right - 500 * s
    y0 = y_center - (top_y + 47.5) * s / 2

    def t(cx, cy):
        return x0 + (cx + 250) * s, y0 + (cy + 47.5) * s

    court = dict(color=line_color, lw=1.1)
    ax.plot([t(-250, -47.5)[0], t(250, -47.5)[0]], [y0, y0], **court)
    for side in (-250, 250):
        ax.plot([t(side, -47.5)[0]] * 2, [t(side, -47.5)[1], t(side, 110)[1]], **court)
    paint_w, paint_h = 160 * s, 190 * s
    ax.add_patch(
        FancyBboxPatch((t(-80, -47.5)), paint_w, paint_h, boxstyle="square,pad=0", facecolor="none", edgecolor=line_color, lw=1.1)
    )
    hoop_x, hoop_y = t(0, 0)
    ax.add_patch(Circle((hoop_x, hoop_y), 7.5 * s * 2, facecolor="none", edgecolor=line_color, lw=1.1))
    corner_top = (237.5**2 - 220**2) ** 0.5
    for side in (-220, 220):
        ax.plot([t(side, -47.5)[0]] * 2, [t(side, -47.5)[1], t(side, corner_top)[1]], **court)
    theta = 22.1  # angle where the arc meets the corner lines
    ax.add_patch(
        Arc((hoop_x, hoop_y), 2 * 237.5 * s, 2 * 237.5 * s, theta1=theta, theta2=180 - theta, color=line_color, lw=1.1)
    )
    dot_r = max(5.0, 5 * s / 0.42 * 0.7)
    legend_size = 8 if s <= 0.6 else 12
    for _, shot in player_shots.iterrows():
        cx, cy = shot["loc_x"], min(shot["loc_y"], top_y)
        dot_x, dot_y = t(cx, cy)
        if shot["shot_made"]:
            ax.add_patch(Circle((dot_x, dot_y), dot_r, facecolor=RED, edgecolor="#FFFFFF", lw=0.8, zorder=4))
        elif miss_as_x:
            ax.plot(dot_x, dot_y, marker="x", ms=dot_r * 1.6, color=INK, mew=2.2, zorder=4)
        else:
            ax.add_patch(Circle((dot_x, dot_y), dot_r, facecolor="#FFFFFF", edgecolor=MUTED, lw=1.2, zorder=4))
    if not draw_legend:
        return
    legend_y = y0 - (14 if s <= 0.6 else 26)
    ax.add_patch(Circle((x0 + 4, legend_y), legend_size / 2, facecolor=RED, edgecolor="none"))
    ax.text(x0 + 14 + legend_size / 2, legend_y, "MAKE", ha="left", va="center", fontsize=legend_size, color=MUTED, fontproperties=_fp_body("medium"))
    miss_x = x0 + (84 if s <= 0.6 else 120)
    ax.add_patch(Circle((miss_x, legend_y), legend_size / 2, facecolor="#FFFFFF", edgecolor=MUTED, lw=1.2))
    ax.text(miss_x + 10 + legend_size / 2, legend_y, "MISS", ha="left", va="center", fontsize=legend_size, color=MUTED, fontproperties=_fp_body("medium"))


def _draw_player_row(ax, player: pd.Series, lens: str, team: pd.Series, shots: pd.DataFrame, y_top: float, first: bool):
    y_center = y_top - PLAYER_ROW_HEIGHT / 2
    if not first:
        ax.plot([60, 1020], [y_top, y_top], color=RULE, lw=1)
    ax.add_patch(
        FancyBboxPatch(
            (60, y_center - 45),
            132,
            90,
            boxstyle="round,pad=0,rounding_size=12",
            facecolor=RED,
            edgecolor="none",
        )
    )
    ax.text(126, y_center + 17, str(int(_number(player["points"]))), ha="center", va="center", fontsize=40, color="#FFFFFF", fontproperties=_fp_body("bold"))
    ax.text(126, y_center - 22, "PTS", ha="center", va="center", fontsize=10, color="#FFFFFF", fontproperties=_fp_body("bold"))
    ax.text(224, y_center + 36, _player_name(player).upper(), ha="left", va="center", fontsize=22, color=INK, fontproperties=_fp_body("bold"))
    box_line = (
        f"{int(_number(player['fieldGoalsMade']))}-{int(_number(player['fieldGoalsAttempted']))} FG"
        f"   ·   {int(_number(player['threePointersMade']))}-{int(_number(player['threePointersAttempted']))} 3PT"
        f"   ·   {int(_number(player['reboundsTotal']))} REB"
        f"   ·   {int(_number(player['assists']))} AST"
    )
    ax.text(224, y_center + 4, box_line, ha="left", va="center", fontsize=13, color=MUTED, fontproperties=_fp_body("medium"))
    lens_label, lens_value = lens_copy(lens, player, team, shots)
    ax.text(224, y_center - 27, lens_label, ha="left", va="center", fontsize=10, color=RED, fontproperties=_fp_body("bold"))
    ax.text(224, y_center - 48, lens_value, ha="left", va="center", fontsize=13, color=INK, fontproperties=_fp_body("bold"))
    if lens == "shot_diet":
        _draw_shot_map(ax, shots, int(player["personId"]), right=1010, y_center=y_center)


def _new_canvas():
    fig = plt.figure(figsize=(W / DEFAULT_DPI, H / DEFAULT_DPI), facecolor="#FFFFFF")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax


def _draw_header(ax, team: pd.Series, opponent: pd.Series, game_date: str, kicker: str | None, show_score: bool = True):
    _draw_title(ax, [("SUMMER LEAGUE ", INK), ("REPORT", RED)])
    if show_score:
        opponent_name = team_nickname(opponent["teamTricode"])
        parts = [
            (f"Bulls {int(_number(team['points']))}", RED),
            (f"{opponent_name} {int(_number(opponent['points']))}", INK),
            (game_date, MUTED),
        ]
    else:
        parts = [(game_date, MUTED)]
    _draw_subtitle(ax, parts, H - 168)
    if kicker:
        ax.text(60, H - 206, kicker, ha="left", va="top", fontsize=14, color=RED, style="italic", fontproperties=_fp_body("medium"))


def _draw_footer(ax):
    ax.text(60, 40, "Summer League game · Data via NBA.com/Stats", ha="left", va="bottom", fontsize=8.5, color=FAINT, fontproperties=_fp_body())
    ax.text(1020, 40, "@chicagobullsdata", ha="right", va="bottom", fontsize=10.5, color=MUTED, fontproperties=_fp_body("medium"))


def render_report(
    team: pd.Series,
    opponent: pd.Series,
    players: list[pd.Series],
    lenses: list[str],
    shots: pd.DataFrame,
    game_date: str,
    kicker: str,
):
    fig, ax = _new_canvas()
    _draw_header(ax, team, opponent, game_date, kicker)
    _draw_team_snapshot(ax, team)
    ax.text(60, 843, "PLAYER STORIES", ha="left", va="top", fontsize=12, color=MUTED, fontproperties=_fp_body("bold"))
    for index, (player, lens) in enumerate(zip(players, lenses)):
        _draw_player_row(ax, player, lens, team, shots, STORIES_TOP - index * PLAYER_ROW_HEIGHT, index == 0)
    _draw_footer(ax)
    return fig


def _player_table_image(players: list[pd.Series], out_path: Path) -> Path:
    """Render the featured-player comparison as a tightly cropped PNG.

    Uses Great Tables (environment-only dependency for now — see the anatomy
    study) so the table engine owns row rhythm, baselines, and image sizing.
    The slide composites the PNG below the team snapshot.
    """
    from great_tables import GT  # imported lazily; not in requirements.txt yet

    for player in players:
        _headshot_path(player)  # make sure the CDN image is cached for fmt_image
    rows = pd.DataFrame(
        [
            {
                "headshot": f"{int(_number(player['personId']))}.png",
                "player": _player_name(player),
                "min": minutes_played(player),
                "pts": int(_number(player["points"])),
                "fg": f"{int(_number(player['fieldGoalsMade']))}-{int(_number(player['fieldGoalsAttempted']))}",
                "three": f"{int(_number(player['threePointersMade']))}-{int(_number(player['threePointersAttempted']))}",
                "reb": int(_number(player["reboundsTotal"])),
                "ast": int(_number(player["assists"])),
                "efg": efg_pct(player),
                "plus_minus": plus_minus(player),
            }
            for player in players
        ]
    ).sort_values("pts", ascending=False)
    table = (
        GT(rows)
        .cols_label(
            headshot="",
            player="PLAYER",
            min="MIN",
            pts="PTS",
            fg="FG",
            three="3PT",
            reb="REB",
            ast="AST",
            efg="eFG%",
            plus_minus="+/-",
        )
        .fmt_image(columns="headshot", path=str(_REPO / "cache" / "headshots"), height=56)
        .fmt_number(columns="efg", decimals=1, pattern="{x}%")
        .fmt_number(columns="plus_minus", decimals=0, force_sign=True)
        .data_color(
            columns="pts",
            palette=["#F2EAE8", "#CE1141", "#7E0C2B"],
            autocolor_text=True,
        )
        .cols_align("left", columns="player")
        .cols_align("center", columns=["headshot", "min", "pts", "fg", "three", "reb", "ast", "efg", "plus_minus"])
        .opt_row_striping(row_striping=True)
        .tab_options(
            table_background_color="white",
            table_font_names=["Archivo", "Helvetica Neue", "Helvetica", "Arial"],
            table_font_size="18px",
            table_font_color=INK,
            column_labels_font_size="13px",
            column_labels_font_weight="bold",
            data_row_padding="11px",
            row_striping_background_color="#F7F7F7",
            table_body_hlines_color="transparent",
            column_labels_border_top_color=INK,
            column_labels_border_top_width="2px",
            column_labels_border_bottom_color=RULE,
            table_body_border_bottom_color=RULE,
            table_border_top_style="none",
            table_border_bottom_style="none",
        )
    )
    table.gtsave(str(out_path), zoom=2, expand=4)
    return out_path


def _shooting_split_line(team: pd.Series, prefix: str, made_key: str, att_key: str) -> str:
    made, att = int(_number(team[made_key])), int(_number(team[att_key]))
    pct = 100 * made / att if att else 0.0
    return f"{prefix}  {made}-{att}  ({pct:.1f}%)"


def render_team_slide(
    team: pd.Series,
    opponent: pd.Series,
    players: list[pd.Series],
    shots: pd.DataFrame,
    game_date: str,
    kicker: str | None,
):
    """Slide 1: the front page — score, Bulls-only snapshot with the team shot
    chart, and one card per featured player."""
    fig, ax = _new_canvas()
    _draw_header(ax, team, opponent, game_date, kicker)

    y_top, y_bottom = 1130, 700
    ax.add_patch(
        FancyBboxPatch(
            (60, y_bottom),
            W - 120,
            y_top - y_bottom,
            boxstyle="round,pad=0,rounding_size=12",
            facecolor=PALE_RED,
            edgecolor="none",
        )
    )
    ax.text(84, y_top - 27, "TEAM SNAPSHOT", ha="left", va="top", fontsize=11, color=RED, fontproperties=_fp_body("bold"))
    stats = [
        (str(int(_number(team["reboundsTotal"]))), "REBOUNDS"),
        (str(int(_number(team["assists"]))), "ASSISTS"),
        (str(int(_number(team["steals"]))), "STEALS"),
        (str(int(_number(team["turnovers"]))), "TURNOVERS"),
    ]
    card_w, card_h, gap = 185, 125, 14
    for index, (value, label) in enumerate(stats):
        x = 84 + (card_w + gap) * (index % 2)
        cy_top = 1030 - (card_h + gap) * (index // 2)
        ax.add_patch(
            FancyBboxPatch(
                (x, cy_top - card_h),
                card_w,
                card_h,
                boxstyle="round,pad=0,rounding_size=12",
                facecolor="#FFFFFF",
                edgecolor="none",
            )
        )
        ax.text(x + card_w / 2, cy_top - 47, value, ha="center", va="center", fontsize=28, color=INK, fontproperties=_fp_body("bold"))
        ax.text(x + card_w / 2, cy_top - 93, label, ha="center", va="center", fontsize=9.5, color=MUTED, fontproperties=_fp_body("bold"))
    if not shots.empty:
        _draw_shot_map(ax, shots, None, right=985, y_center=962, s=0.72)
    splits = [
        _shooting_split_line(team, "FG", "fieldGoalsMade", "fieldGoalsAttempted"),
        _shooting_split_line(team, "3PT", "threePointersMade", "threePointersAttempted"),
        _shooting_split_line(team, "FT", "freeThrowsMade", "freeThrowsAttempted"),
    ]
    for index, line in enumerate(splits):
        ax.text(805, 792 - index * 33, line, ha="center", va="top", fontsize=12.5, color=INK, fontproperties=_fp_body("bold"))

    # The featured players render as one Great Tables comparison so the table
    # engine, not per-card coordinates, owns row rhythm and alignment.
    table_png = _player_table_image(players, OUTPUT_DIR / "_player_table.png")
    table_img = mpimg.imread(table_png)
    img_h, img_w = table_img.shape[:2]
    disp_w = W - 120
    disp_h = disp_w * img_h / img_w
    # Keep the table close under the snapshot; extra space breathes at the bottom.
    table_top = y_bottom - min(70, max(40, (y_bottom - 90 - disp_h) / 2))
    ax.imshow(
        table_img,
        extent=[60, 60 + disp_w, table_top - disp_h, table_top],
        zorder=3,
        interpolation="bilinear",
    )
    _draw_footer(ax)
    return fig


def render_player_slide(
    player: pd.Series,
    team: pd.Series,
    opponent: pd.Series,
    shots: pd.DataFrame,
    game_date: str,
    kicker: str,
):
    """One full slide per player, in the C2 anatomy-study structure: identity
    header, a large exact-location FGA chart on the left as the evidence
    layer, and a compact supporting stat rail on the right."""
    fig, ax = _new_canvas()
    _draw_header(ax, team, opponent, game_date, kicker, show_score=False)

    headshot_label(ax, _headshot_path(player), 118, 1058, radius=58)
    _fitted_text(ax, 206, 1096, _display_name(player), _fp_display(), 30, 790, INK)
    identity_chips = [
        (str(int(_number(player["points"]))), "PTS", RED),
        (str(minutes_played(player)), "MIN", INK),
        (str(int(_number(player["reboundsTotal"]))), "REB", INK),
        (str(int(_number(player["assists"]))), "AST", INK),
    ]
    _chip_row(ax, identity_chips, 208, 1038, w=118, h=52, gap=10, value_size=14.5)
    ax.plot([60, 1020], [952, 952], color=RULE, lw=1)

    fga = int(_number(player["fieldGoalsAttempted"]))
    ax.text(60, 904, f"ALL {fga} FIELD-GOAL ATTEMPTS", ha="left", va="top", fontsize=11, color=RED, fontproperties=_fp_body("bold"))
    _draw_shot_map(
        ax,
        shots,
        int(player["personId"]),
        right=660,
        y_center=590,
        s=1.2,
        line_color="#C6C6C6",
    )
    splits = zone_splits(shots, int(player["personId"]))
    zone_caption = (
        f"{splits['rim_paint'][0]}-{splits['rim_paint'][1]} RIM/PAINT"
        f"   ·   {splits['mid'][0]}-{splits['mid'][1]} MID-RANGE"
        f"   ·   {splits['three'][0]}-{splits['three'][1]} THREES"
    )
    ax.text(60, 322, zone_caption, ha="left", va="top", fontsize=11.5, color=MUTED, fontproperties=_fp_body("medium"))

    rail_x, rail_w = 740, 280
    ax.text(rail_x, 904, "SHOT PROFILE", ha="left", va="top", fontsize=11, color=RED, fontproperties=_fp_body("bold"))
    rail = [
        (f"{int(_number(player['fieldGoalsMade']))}-{int(_number(player['fieldGoalsAttempted']))}", "FIELD GOALS", False),
        (f"{int(_number(player['threePointersMade']))}-{int(_number(player['threePointersAttempted']))}", "THREES", False),
        (f"{int(_number(player['freeThrowsMade']))}-{int(_number(player['freeThrowsAttempted']))}", "FREE THROWS", False),
        (f"{efg_pct(player):.1f}%", "EFFECTIVE FG", True),  # the payoff number
        (f"{role_share_pct(player, team):.0f}%", "OF BULLS FGA", False),
        (f"{plus_minus(player):+d}", "PLUS/MINUS", False),
    ]
    card_h, gap = 88, 14
    for index, (value, label, payoff) in enumerate(rail):
        top = 862 - index * (card_h + gap)
        ax.add_patch(
            FancyBboxPatch(
                (rail_x, top - card_h),
                rail_w,
                card_h,
                boxstyle="round,pad=0,rounding_size=12",
                facecolor=RED if payoff else CHIP_GRAY,
                edgecolor="none",
            )
        )
        value_color = "#FFFFFF" if payoff else INK
        label_color = "#F5C9D6" if payoff else MUTED
        cx = rail_x + rail_w / 2
        ax.text(cx, top - card_h * 0.34, value, ha="center", va="center", fontsize=23, color=value_color, fontproperties=_fp_body("bold"))
        ax.text(cx, top - card_h * 0.73, label, ha="center", va="center", fontsize=9, color=label_color, fontproperties=_fp_body("bold"))
    _draw_footer(ax)
    return fig


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-id", help="NBA.com game ID; omit to auto-resolve the latest completed Bulls game")
    parser.add_argument("--season", default=str(date.today().year), help="Summer League year used to auto-resolve the game")
    parser.add_argument("--player", action="append", dest="players", help="Featured Bulls player; repeat one to three times")
    parser.add_argument("--lens", action="append", choices=LENSES, help="Matching story lens for each --player")
    parser.add_argument("--date", help="Graphic date label; defaults to the game's own date")
    parser.add_argument("--kicker", help="Short editorial line below the score")
    parser.add_argument("--carousel", action="store_true", help="Render a team front-page slide plus one full slide per player; --lens is ignored (player slides show all three lenses)")
    parser.add_argument("--final", action="store_true", help="Export at 300 DPI")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.carousel:
        if bool(args.players) != bool(args.lens) or args.players and len(args.players) != len(args.lens):
            raise SystemExit("Pass one --lens for every --player.")
    elif not args.players:
        raise SystemExit("Carousel mode needs one to three --player names.")
    if args.players and not 1 <= len(args.players) <= 3:
        raise SystemExit("Choose one to three featured players.")

    game_id = args.game_id
    if not game_id:
        game_id, matchup = find_latest_bulls_game(args.season)
        print(f"Resolved game {game_id}: {matchup}")

    summary = fetch_game_summary(game_id)
    require_final(summary, game_id)

    players, teams, shots = fetch_game_data(game_id)
    bulls = players[players["teamId"] == BULLS_TEAM_ID].copy()
    bulls = bulls[bulls["minutes"].fillna("").astype(str).str.strip() != ""]
    team = teams[teams["teamId"] == BULLS_TEAM_ID]
    opponent = teams[teams["teamId"] != BULLS_TEAM_ID]
    if bulls.empty or team.empty or opponent.empty:
        raise SystemExit("This game does not contain a completed Bulls box score.")
    team_row, opponent_row = team.iloc[0], opponent.iloc[0]

    print("\nBULLS STORY REVIEW")
    print(player_candidates(bulls, team_row).to_string(index=False))
    print("\nShot diet uses NBA.com shot zones. eFG% is shown for review; true shooting is intentionally excluded during the 2026 Summer League free-throw experiment.")
    if not args.players:
        print("\nChoose one to three players and matching lenses, then re-run. See --help for an example.")
        return

    needs_shots = args.carousel or (args.lens and "shot_diet" in args.lens)
    if needs_shots and shots.empty:
        raise SystemExit("The shot chart for this game is not available yet; choose another lens or retry shortly.")
    selected = select_players(bulls, args.players)
    # Slide 1 carries no kicker by default; --kicker adds an approved editorial line.
    kicker = args.kicker
    played_on = game_day(summary)
    graphic_date = args.date or played_on.strftime("%b %d, %Y").upper()
    dpi = 300 if args.final else DEFAULT_DPI

    if args.carousel:
        slides = [render_team_slide(team_row, opponent_row, selected, shots, graphic_date, kicker)]
        slides += [
            render_player_slide(player, team_row, opponent_row, shots, graphic_date, None)
            for player in selected
        ]
        for index, fig in enumerate(slides, start=1):
            output = OUTPUT_DIR / f"{played_on.isoformat()}-summer-league-report-s{index}.png"
            save_feed_post(fig, output, dpi=dpi)
            plt.close(fig)
            print(f"Saved {output} at {dpi} DPI")
        return

    fig = render_report(team_row, opponent_row, selected, args.lens, shots, graphic_date, kicker)
    output = OUTPUT_DIR / f"{played_on.isoformat()}-summer-league-report.png"
    save_feed_post(fig, output, dpi=dpi)
    plt.close(fig)
    print(f"\nSaved {output} at {dpi} DPI")


if __name__ == "__main__":
    main()
