"""Render a player-led Bulls Summer League Report from a completed NBA game.

Game-night flow:
1. Run with no arguments to auto-resolve the latest completed Bulls Summer
   League game and review player box scores, role share, plus/minus, and
   shot-diet inputs.
2. In the clarification pass, choose one to four players and assign each the
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
import base64
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Arc, Circle, FancyBboxPatch
from nba_api.stats.endpoints import (
    boxscoreadvancedv3,
    boxscoresummaryv3,
    boxscoretraditionalv3,
    leaguegamefinder,
)

from bulls.config import BULLS_TEAM_ID, NBA_TEAMS
from bulls.data.fetch import _NBA_HEADERS, get_game_shots, get_player_headshot
from bulls.graphics.craft import headshot_label
from bulls.graphics.house import (
    CANVAS_HEIGHT as H,
    CANVAS_WIDTH as W,
    DEFAULT_THEME,
    INK,
    MUTED,
    RED,
    RULE,
    WHITE,
    body_font,
    display_font,
    draw_footer,
    draw_jersey_stripe,
    export_dpi,
    new_canvas,
    rendered_width,
    save_post,
)

PALE_RED = "#F7E8ED"
PANEL_RED = "#FAF1F4"  # lighter wash for large court panels
CHIP_GRAY = "#F1ECE8"  # warm neutral for cards outside a tinted panel
CHIP_BLUSH = "#F3E1E7"  # visible stat chips on the jersey canvas
COURT_LINE = "#C9A8B5"  # warm court lines on the pale panels
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


@dataclass(frozen=True)
class HeaderData:
    """Display-ready content shared by one report slide header."""

    title_segments: tuple[tuple[str, str], ...]
    subtitle_parts: tuple[tuple[str, str], ...]
    kicker: str | None = None


@dataclass(frozen=True)
class ShotMark:
    """One prepared shot-chart mark; no NBA/Pandas fields reach the renderer."""

    x: float
    y: float
    made: bool


@dataclass(frozen=True)
class StatItem:
    value: str
    label: str
    color: str = INK
    highlight: bool = False


@dataclass(frozen=True)
class ComparisonItem:
    """One Bulls/opponent row in the compact game comparison."""

    label: str
    bulls_value: float
    opponent_value: float
    bulls_display: str
    opponent_display: str


@dataclass(frozen=True)
class ZoneItem:
    """One Bulls shooting zone, including accuracy and shot-diet share."""

    key: str
    makes: int
    attempts: int
    percentage: float
    share: float


@dataclass(frozen=True)
class PlayerTableRow:
    headshot: Path | None
    player: str
    minutes: int
    points: int
    rebounds: int
    assists: int
    turnovers: int
    steals: int
    blocks: int
    field_goals: str
    threes: str
    free_throws: str
    usage: float
    true_shooting: float
    net_rating: float


@dataclass(frozen=True)
class TeamSlideData:
    header: HeaderData
    comparison_stats: tuple[ComparisonItem, ...]
    zones: tuple[ZoneItem, ...]
    shooting_splits: tuple[str, ...]
    players: tuple[PlayerTableRow, ...]


@dataclass(frozen=True)
class PlayerSlideData:
    header: HeaderData
    display_name: str
    headshot: Path | None
    identity_stats: tuple[StatItem, ...]
    attempts_label: str
    shots: tuple[ShotMark, ...]
    zone_stats: tuple[StatItem, ...]
    profile_stats: tuple[StatItem, ...]


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
    advanced_columns = ("usagePercentage", "netRating", "trueShootingPercentage")
    try:
        advanced = boxscoreadvancedv3.BoxScoreAdvancedV3(
            game_id=game_id,
            timeout=30,
            headers=_NBA_HEADERS,
        ).player_stats.get_data_frame()
        # Right after the buzzer the endpoint can respond with all-zero rows
        # before the real numbers post. A played game cannot have zero TS% for
        # every player, so an all-zero frame means "not populated yet".
        if advanced[list(advanced_columns)].abs().to_numpy().sum() == 0:
            raise ValueError("advanced box score not populated yet")
        players = players.merge(
            advanced[["personId", *advanced_columns]],
            on="personId",
            how="left",
        )
    except Exception as error:
        print(f"Warning: advanced box score unavailable ({error}); NETRTG, USG%, and TS% will show as missing.")
        for column in advanced_columns:
            players[column] = float("nan")
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


def ts_pct(player: pd.Series) -> float:
    """NBA-computed true shooting, as a percentage."""
    return 100 * _number(player.get("trueShootingPercentage"))


def usage_pct(player: pd.Series) -> float:
    return 100 * _number(player.get("usagePercentage"))


def net_rating(player: pd.Series) -> float:
    return _number(player.get("netRating"))


def one_ft_rule_applies(game_id: str) -> bool:
    """The one-free-throw experiment started with the 2026 Summer League.

    Game IDs encode {league:2}{season_type:1}{season:2}{game:5}, so characters
    3-4 are the two-digit season year. TS% printed for these games carries a
    footnote because the rule halves FTA and inflates the standard formula.
    """
    return game_id[:2] == SUMMER_LEAGUE_LEAGUE_ID and game_id[3:5] >= "26"


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
        [
            "name",
            "points",
            "FG",
            "3PT",
            "reboundsTotal",
            "assists",
            "steals",
            "blocks",
            "+/-",
            "FGA share",
            "eFG%",
        ]
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


def prepare_header(
    team: pd.Series,
    opponent: pd.Series,
    game_date: str,
    kicker: str | None,
    *,
    show_score: bool = True,
) -> HeaderData:
    """Turn raw box-score rows into the exact header copy the renderer needs."""
    title = (
        (str(team["teamTricode"]), RED),
        (" VS ", DEFAULT_THEME.ink),
        (str(opponent["teamTricode"]), DEFAULT_THEME.ink),
    )
    if show_score:
        parts = (
            (f"Bulls {int(_number(team['points']))}", RED),
            (f"{team_nickname(opponent['teamTricode'])} {int(_number(opponent['points']))}", DEFAULT_THEME.ink),
            (game_date, DEFAULT_THEME.muted),
        )
    else:
        parts = ((game_date, DEFAULT_THEME.muted),)
    return HeaderData(title, parts, kicker)


def _shooting_percentage(team: pd.Series, made_key: str, attempts_key: str) -> float:
    attempts = _number(team.get(attempts_key))
    return 100 * _number(team.get(made_key)) / attempts if attempts else 0.0


def prepare_comparison_stats(team: pd.Series, opponent: pd.Series) -> tuple[ComparisonItem, ...]:
    """Prepare the eight non-scoring rows shown in the game snapshot."""
    rows: list[ComparisonItem] = []
    for label, key in (
        ("REB", "reboundsTotal"),
        ("AST", "assists"),
        ("STL", "steals"),
        ("BLK", "blocks"),
        ("TO", "turnovers"),
    ):
        bulls_value = _number(team.get(key))
        opponent_value = _number(opponent.get(key))
        rows.append(
            ComparisonItem(
                label,
                bulls_value,
                opponent_value,
                str(int(bulls_value)),
                str(int(opponent_value)),
            )
        )
    for label, made_key, attempts_key in (
        ("FG%", "fieldGoalsMade", "fieldGoalsAttempted"),
        ("3P%", "threePointersMade", "threePointersAttempted"),
        ("FT%", "freeThrowsMade", "freeThrowsAttempted"),
    ):
        bulls_value = _shooting_percentage(team, made_key, attempts_key)
        opponent_value = _shooting_percentage(opponent, made_key, attempts_key)
        rows.append(
            ComparisonItem(
                label,
                bulls_value,
                opponent_value,
                f"{bulls_value:.1f}",
                f"{opponent_value:.1f}",
            )
        )
    return tuple(rows)


def prepare_team_zones(shots: pd.DataFrame) -> tuple[ZoneItem, ...]:
    """Summarize the Bulls' six useful half-court zones for the cover slide."""
    zone_keys = (
        ("restricted", "Restricted Area"),
        ("paint", "In The Paint (Non-RA)"),
        ("mid", "Mid-Range"),
        ("left_corner", "Left Corner 3"),
        ("right_corner", "Right Corner 3"),
        ("above_break", "Above the Break 3"),
    )
    total_attempts = len(shots)
    results = []
    for key, nba_label in zone_keys:
        if key == "above_break":
            rows = shots[~shots["shot_zone"].isin(label for _, label in zone_keys[:-1])]
        else:
            rows = shots[shots["shot_zone"] == nba_label]
        attempts = len(rows)
        makes = int(rows["shot_made"].sum()) if attempts else 0
        percentage = 100 * makes / attempts if attempts else 0.0
        share = 100 * attempts / total_attempts if total_attempts else 0.0
        results.append(ZoneItem(key, makes, attempts, percentage, share))
    return tuple(results)


def _shooting_split_line(team: pd.Series, label: str, made_key: str, attempts_key: str) -> str:
    made = int(_number(team.get(made_key)))
    attempts = int(_number(team.get(attempts_key)))
    percentage = 100 * made / attempts if attempts else 0.0
    return f"{label}  {made}-{attempts}  ({percentage:.1f}%)"


def prepare_shot_marks(shots: pd.DataFrame, player_id: int | None) -> tuple[ShotMark, ...]:
    """Remove dataframe/API vocabulary before shot attempts reach drawing code."""
    rows = shots if player_id is None else shots[shots["player_id"] == player_id]
    return tuple(
        ShotMark(float(shot["loc_x"]), float(shot["loc_y"]), bool(shot["shot_made"]))
        for _, shot in rows.iterrows()
    )


def _fitted_text(ax, x, y, text, fp, base_size, max_width, color, ha="left", va="top"):
    """Draw text at base_size, shrinking only if it would overflow max_width."""
    probe = ax.text(x, y, text, ha=ha, va=va, fontsize=base_size, fontproperties=fp, alpha=0)
    width = rendered_width(ax, probe)
    probe.remove()
    size = base_size if width <= max_width else base_size * max_width / width
    return ax.text(x, y, text, ha=ha, va=va, fontsize=size, color=color, fontproperties=fp)


def _stat_chip(
    ax,
    x,
    y_top,
    w,
    h,
    value,
    label,
    value_size=14.5,
    value_color=INK,
    facecolor=CHIP_GRAY,
):
    """One stat in its own small container: bold value over a muted label."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y_top - h),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=10",
            facecolor=facecolor,
            edgecolor="none",
        )
    )
    cx = x + w / 2
    ax.text(cx, y_top - h * 0.35, value, ha="center", va="center", fontsize=value_size, color=value_color, fontproperties=body_font("bold"))
    ax.text(cx, y_top - h * 0.72, label, ha="center", va="center", fontsize=8.5, color=MUTED, fontproperties=body_font("bold"))


def _chip_row(
    ax,
    chips: list[tuple[str, str, str]],
    x,
    y_top,
    w,
    h,
    gap,
    value_size=14.5,
    facecolor=CHIP_GRAY,
):
    """A row of stat chips; each entry is (value, label, value_color)."""
    for index, (value, label, color) in enumerate(chips):
        _stat_chip(
            ax,
            x + index * (w + gap),
            y_top,
            w,
            h,
            value,
            label,
            value_size,
            value_color=color,
            facecolor=facecolor,
        )


def _display_name(player: pd.Series) -> str:
    """Name for the Academic M54 face, which has no hyphen glyph."""
    return _player_name(player).upper().replace("-", " ")


def _headshot_path(player: pd.Series):
    """Committed local crop if one exists, else the cached NBA CDN headshot.

    Local overrides live in assets/img/players/<personId>.png — used when the
    CDN only has the gray rookie silhouette (DESIGN.md §8). Warns when falling
    back to a file that looks like the silhouette.
    """
    person_id = int(_number(player["personId"]))
    local = _REPO / "assets" / "img" / "players" / f"{person_id}.png"
    if local.exists():
        return local
    path = get_player_headshot(person_id)
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
    ax.text(84, y_top - 27, "TEAM SNAPSHOT", ha="left", va="top", fontsize=11, color=RED, fontproperties=body_font("bold"))
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
        ax.text(x, y_top - 75, value, ha="left", va="top", fontsize=29, color=INK, fontproperties=body_font("bold"))
        ax.text(x, y_top - 125, label, ha="left", va="top", fontsize=11, color=MUTED, fontproperties=body_font("bold"))


def _draw_shot_map(
    ax,
    attempts: tuple[ShotMark, ...],
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
    The caller prepares the team or player attempt set before drawing.
    """
    if not attempts:
        return
    t, x0, y0, top_y = _draw_half_court(ax, right, y_center, s, line_color)

    dot_r = max(5.0, 5 * s / 0.42 * 0.7)
    legend_size = 8 if s <= 0.6 else 12
    for shot in attempts:
        cx, cy = shot.x, min(shot.y, top_y)
        dot_x, dot_y = t(cx, cy)
        if shot.made:
            ax.add_patch(Circle((dot_x, dot_y), dot_r, facecolor=RED, edgecolor="#FFFFFF", lw=0.8, zorder=4))
        elif miss_as_x:
            ax.plot(dot_x, dot_y, marker="x", ms=dot_r * 0.72, color=INK, mew=1.2, zorder=4)
        else:
            ax.add_patch(Circle((dot_x, dot_y), dot_r, facecolor="#FFFFFF", edgecolor=MUTED, lw=1.2, zorder=4))
    if not draw_legend:
        return
    legend_y = y0 - (14 if s <= 0.6 else 26)
    ax.add_patch(Circle((x0 + 4, legend_y), legend_size / 2, facecolor=RED, edgecolor="none"))
    ax.text(x0 + 14 + legend_size / 2, legend_y, "MAKE", ha="left", va="center", fontsize=legend_size, color=MUTED, fontproperties=body_font("medium"))
    miss_x = x0 + (84 if s <= 0.6 else 120)
    if miss_as_x:
        ax.plot(miss_x, legend_y, marker="x", ms=legend_size * 0.65, color=INK, mew=1.2)
    else:
        ax.add_patch(Circle((miss_x, legend_y), legend_size / 2, facecolor="#FFFFFF", edgecolor=MUTED, lw=1.2))
    ax.text(miss_x + 10 + legend_size / 2, legend_y, "MISS", ha="left", va="center", fontsize=legend_size, color=MUTED, fontproperties=body_font("medium"))


def _draw_half_court(ax, right: float, y_center: float, s: float, line_color: str):
    """Draw the reusable court geometry and return its coordinate transform."""
    top_y = 280
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
    return t, x0, y0, top_y


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
    ax.text(126, y_center + 17, str(int(_number(player["points"]))), ha="center", va="center", fontsize=40, color="#FFFFFF", fontproperties=body_font("bold"))
    ax.text(126, y_center - 22, "PTS", ha="center", va="center", fontsize=10, color="#FFFFFF", fontproperties=body_font("bold"))
    ax.text(224, y_center + 36, _player_name(player).upper(), ha="left", va="center", fontsize=22, color=INK, fontproperties=body_font("bold"))
    box_line = (
        f"{int(_number(player['fieldGoalsMade']))}-{int(_number(player['fieldGoalsAttempted']))} FG"
        f"   ·   {int(_number(player['threePointersMade']))}-{int(_number(player['threePointersAttempted']))} 3PT"
        f"   ·   {int(_number(player['reboundsTotal']))} REB"
        f"   ·   {int(_number(player['assists']))} AST"
    )
    ax.text(224, y_center + 4, box_line, ha="left", va="center", fontsize=13, color=MUTED, fontproperties=body_font("medium"))
    lens_label, lens_value = lens_copy(lens, player, team, shots)
    ax.text(224, y_center - 27, lens_label, ha="left", va="center", fontsize=10, color=RED, fontproperties=body_font("bold"))
    ax.text(224, y_center - 48, lens_value, ha="left", va="center", fontsize=13, color=INK, fontproperties=body_font("bold"))
    if lens == "shot_diet":
        attempts = prepare_shot_marks(shots, int(player["personId"]))
        _draw_shot_map(ax, attempts, right=1010, y_center=y_center)


def _draw_header(ax, header: HeaderData):
    draw_jersey_stripe(ax)
    team_code = header.title_segments[0][0]
    opponent_code = header.title_segments[-1][0]
    team_logo = _REPO / "assets" / "img" / "teams" / f"{team_code}.png"
    opponent_logo = _REPO / "assets" / "img" / "teams" / f"{opponent_code}.png"
    logo_bottom, logo_top = H - 157, H - 57
    if team_logo.exists():
        ax.imshow(mpimg.imread(team_logo), extent=[60, 160, logo_bottom, logo_top], zorder=6)
    cursor = 178 if team_logo.exists() else 60
    title_y = H - 55
    title_size = 54
    for text, color in header.title_segments:
        artist = ax.text(
            cursor,
            title_y,
            text,
            ha="left",
            va="top",
            fontsize=title_size,
            color=color,
            fontproperties=display_font(),
            path_effects=[
                pe.withStroke(linewidth=7, foreground=RED),
                pe.withStroke(linewidth=3.5, foreground=WHITE),
                pe.Normal(),
            ],
        )
        cursor += rendered_width(ax, artist)
    if opponent_logo.exists():
        ax.imshow(mpimg.imread(opponent_logo), extent=[cursor + 18, cursor + 118, logo_bottom, logo_top], zorder=6)
    # Keep every subtitle segment on one visual centerline; the date remains
    # secondary through weight and color rather than a mismatched size.
    subtitle_y = H - 194
    cursor = 60
    for index, (text, color) in enumerate(header.subtitle_parts):
        artist = ax.text(cursor, subtitle_y, text, ha="left", va="center", fontsize=18, color=color, fontproperties=body_font("bold" if index < 2 else "medium"))
        cursor += rendered_width(ax, artist)
        if index < len(header.subtitle_parts) - 1:
            cursor += 13
            ax.plot([cursor, cursor], [subtitle_y - 8, subtitle_y + 8], color=DEFAULT_THEME.tick, lw=1.3, zorder=6)
            cursor += 13
    if header.kicker:
        ax.text(60, H - 210, header.kicker, ha="left", va="top", fontsize=14, color=RED, style="italic", fontproperties=body_font("medium"))


def _draw_footer(ax):
    draw_footer(
        ax,
        source="Data via nba.com",
    )


def render_report(
    team: pd.Series,
    opponent: pd.Series,
    players: list[pd.Series],
    lenses: list[str],
    shots: pd.DataFrame,
    game_date: str,
    kicker: str,
):
    fig, ax = new_canvas()
    _draw_header(ax, prepare_header(team, opponent, game_date, kicker))
    _draw_team_snapshot(ax, team)
    ax.text(60, 843, "PLAYER STORIES", ha="left", va="top", fontsize=12, color=MUTED, fontproperties=body_font("bold"))
    for index, (player, lens) in enumerate(zip(players, lenses)):
        _draw_player_row(ax, player, lens, team, shots, STORIES_TOP - index * PLAYER_ROW_HEIGHT, index == 0)
    _draw_footer(ax)
    return fig


def _player_table_image(players: tuple[PlayerTableRow, ...], out_path: Path) -> Path:
    """Render the featured-player comparison as a tightly cropped PNG.

    Uses Great Tables (environment-only dependency for now — see the anatomy
    study) so the table engine owns row rhythm, baselines, and image sizing.
    The slide composites the PNG below the team snapshot.
    """
    from great_tables import GT  # imported lazily; not in requirements.txt yet

    rows = pd.DataFrame(
        [
            {
                "headshot": str(player.headshot or ""),
                "player": player.player,
                "min": player.minutes,
                "pts": player.points,
                "reb": player.rebounds,
                "ast": player.assists,
                "tov": player.turnovers,
                "stl": player.steals,
                "blk": player.blocks,
                "fgma": player.field_goals,
                "pm3a": player.threes,
                "ftma": player.free_throws,
                "usg": player.usage,
                "ts": player.true_shooting,
                "netrtg": player.net_rating,
            }
            for player in players
        ]
    ).sort_values("pts", ascending=False)
    table = (
        GT(rows)
        .cols_label(
            headshot="",
            player="PLAYER",
            netrtg="NETRTG",
            min="MIN",
            pts="PTS",
            reb="REB",
            ast="AST",
            tov="TOV",
            stl="STL",
            blk="BLK",
            fgma="FGM/A",
            pm3a="3PM/A",
            ftma="FTM/A",
            usg="USG%",
            ts="TS%",
        )
        .fmt_image(columns="headshot", height=52)
        .fmt_number(columns="netrtg", decimals=1, force_sign=True)
        .fmt_number(columns=["usg", "ts"], decimals=1)
        .sub_missing(missing_text="—")
        .cols_align("left", columns="player")
        .cols_align("center", columns=["headshot", "netrtg", "min", "pts", "reb", "ast", "tov", "stl", "blk", "fgma", "pm3a", "ftma", "usg", "ts"])
        .opt_row_striping(row_striping=True)
        .tab_options(
            table_background_color=DEFAULT_THEME.canvas,
            table_font_names=["Archivo", "Helvetica Neue", "Helvetica", "Arial"],
            table_font_size="16px",
            table_font_color=DEFAULT_THEME.ink,
            column_labels_font_size="12px",
            column_labels_font_weight="bold",
            data_row_padding="11px",
            row_striping_background_color="#F3EFE9",
            table_body_hlines_color="transparent",
            column_labels_border_top_color=DEFAULT_THEME.ink,
            column_labels_border_top_width="2px",
            column_labels_border_bottom_color=DEFAULT_THEME.rule,
            table_body_border_bottom_color=DEFAULT_THEME.rule,
            table_border_top_style="none",
            table_border_bottom_style="none",
        )
    )
    # Great Tables renders inside a browser, which cannot see Matplotlib's font
    # registry. Embed the exact local Archivo files so the PNG cannot silently
    # fall back to Helvetica on another machine.
    font_css = []
    for weight, filename in ((400, "Archivo-400.ttf"), (500, "Archivo-500.ttf"), (600, "Archivo-600.ttf")):
        encoded = base64.b64encode((_REPO / "assets" / "fonts" / filename).read_bytes()).decode("ascii")
        font_css.append(
            f"@font-face{{font-family:'Archivo';font-style:normal;font-weight:{weight};"
            f"src:url(data:font/ttf;base64,{encoded}) format('truetype');}}"
        )
    html = table.as_raw_html().replace("<style>", f"<style>{''.join(font_css)}", 1)
    import nokap

    nokap.from_html(html=html, file=out_path, selector="table", expand=0, zoom=2, vwidth=992, vheight=744)
    return out_path


def _prepare_player_table_row(player: pd.Series) -> PlayerTableRow:
    return PlayerTableRow(
        headshot=_headshot_path(player),
        player=_player_name(player),
        minutes=minutes_played(player),
        points=int(_number(player["points"])),
        rebounds=int(_number(player["reboundsTotal"])),
        assists=int(_number(player["assists"])),
        turnovers=int(_number(player["turnovers"])),
        steals=int(_number(player["steals"])),
        blocks=int(_number(player["blocks"])),
        field_goals=f"{int(_number(player['fieldGoalsMade']))}/{int(_number(player['fieldGoalsAttempted']))}",
        threes=f"{int(_number(player['threePointersMade']))}/{int(_number(player['threePointersAttempted']))}",
        free_throws=f"{int(_number(player['freeThrowsMade']))}/{int(_number(player['freeThrowsAttempted']))}",
        usage=usage_pct(player),
        true_shooting=ts_pct(player),
        net_rating=net_rating(player),
    )


def prepare_team_slide(
    team: pd.Series,
    opponent: pd.Series,
    players: list[pd.Series],
    shots: pd.DataFrame,
    game_date: str,
    kicker: str | None,
) -> TeamSlideData:
    """Prepare the complete front-page content before any drawing occurs."""
    table_rows = tuple(
        sorted(
            (_prepare_player_table_row(player) for player in players),
            key=lambda row: row.points,
            reverse=True,
        )
    )
    return TeamSlideData(
        header=prepare_header(team, opponent, game_date, kicker),
        comparison_stats=prepare_comparison_stats(team, opponent),
        zones=prepare_team_zones(shots),
        shooting_splits=(
            _shooting_split_line(team, "FG", "fieldGoalsMade", "fieldGoalsAttempted"),
            _shooting_split_line(team, "3PT", "threePointersMade", "threePointersAttempted"),
            _shooting_split_line(team, "FT", "freeThrowsMade", "freeThrowsAttempted"),
        ),
        players=table_rows,
    )


def prepare_player_slide(
    player: pd.Series,
    team: pd.Series,
    opponent: pd.Series,
    shots: pd.DataFrame,
    game_date: str,
    kicker: str | None,
    highlighted_identity_stats: frozenset[str] = frozenset(),
) -> PlayerSlideData:
    """Prepare one player's display copy, metrics, image, and shot marks."""
    person_id = int(_number(player["personId"]))
    splits = zone_splits(shots, person_id)
    return PlayerSlideData(
        header=prepare_header(team, opponent, game_date, kicker, show_score=False),
        display_name=_display_name(player),
        headshot=_headshot_path(player),
        identity_stats=(
            StatItem(str(int(_number(player["points"]))), "PTS", RED if "PTS" in highlighted_identity_stats else INK),
            StatItem(str(minutes_played(player)), "MIN", RED if "MIN" in highlighted_identity_stats else INK),
            StatItem(str(int(_number(player["reboundsTotal"]))), "REB", RED if "REB" in highlighted_identity_stats else INK),
            StatItem(str(int(_number(player["assists"]))), "AST", RED if "AST" in highlighted_identity_stats else INK),
            StatItem(str(int(_number(player["steals"]))), "STL", RED if "STL" in highlighted_identity_stats else INK),
            StatItem(str(int(_number(player["blocks"]))), "BLK", RED if "BLK" in highlighted_identity_stats else INK),
        ),
        attempts_label="SHOT CHART",
        shots=prepare_shot_marks(shots, person_id),
        zone_stats=(
            StatItem(f"{splits['rim_paint'][0]}-{splits['rim_paint'][1]}", "RIM / PAINT"),
            StatItem(f"{splits['mid'][0]}-{splits['mid'][1]}", "MID-RANGE"),
            StatItem(f"{splits['three'][0]}-{splits['three'][1]}", "THREES"),
        ),
        profile_stats=(
            StatItem(
                f"{int(_number(player['fieldGoalsMade']))}-{int(_number(player['fieldGoalsAttempted']))}",
                "FIELD GOALS",
            ),
            StatItem(
                f"{int(_number(player['threePointersMade']))}-{int(_number(player['threePointersAttempted']))}",
                "THREES",
            ),
            StatItem(
                f"{int(_number(player['freeThrowsMade']))}-{int(_number(player['freeThrowsAttempted']))}",
                "FREE THROWS",
            ),
            StatItem(f"{ts_pct(player):.1f}%", "TRUE SHOOTING"),
            StatItem(f"{role_share_pct(player, team):.0f}%", "OF BULLS FGA"),
            StatItem(f"{plus_minus(player):+d}", "PLUS/MINUS"),
        ),
    )


def render_team_slide(
    data: TeamSlideData,
):
    """Slide 1: matchup, compact game comparison, shot diet, and player table."""
    fig, ax = new_canvas()
    _draw_header(ax, data.header)

    y_top, y_bottom = 1105, 620
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
    section_y = y_top - 25
    ax.text(84, section_y, "TEAM SNAPSHOT", ha="left", va="top", fontsize=11, color=RED, fontproperties=body_font("bold"))
    # The shot diet carries more visual information, so it owns roughly 65%
    # of the panel while the compact comparison uses the remaining 35%.
    divider_x = 420
    ax.plot([divider_x, divider_x], [y_bottom + 22, y_top - 58], color="#E6C4CF", lw=1)

    # Left: every row is normalized within itself, so bar length answers only
    # "which team had more of this stat?" Exact labels carry the actual values.
    left_end, right_start, max_bar = 210, 270, 64
    opponent_code = data.header.title_segments[-1][0]
    ax.text(left_end, 1028, "CHI", ha="right", va="center", fontsize=10, color=RED, fontproperties=body_font("bold"))
    ax.text(right_start, 1028, opponent_code, ha="left", va="center", fontsize=10, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))
    for index, stat in enumerate(data.comparison_stats):
        y = 990 - index * 43
        row_max = max(stat.bulls_value, stat.opponent_value, 1)
        bulls_w = max_bar * stat.bulls_value / row_max
        opponent_w = max_bar * stat.opponent_value / row_max
        ax.add_patch(FancyBboxPatch((left_end - bulls_w, y - 9), bulls_w, 18, boxstyle="round,pad=0,rounding_size=2", facecolor=RED, edgecolor="none"))
        ax.add_patch(FancyBboxPatch((right_start, y - 9), opponent_w, 18, boxstyle="round,pad=0,rounding_size=2", facecolor=DEFAULT_THEME.contrast, edgecolor="none"))
        ax.text(left_end - bulls_w - 7, y, stat.bulls_display, ha="right", va="center", fontsize=10, color=RED, fontproperties=body_font("bold"))
        ax.text(240, y, stat.label, ha="center", va="center", fontsize=9.5, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))
        ax.text(right_start + opponent_w + 7, y, stat.opponent_display, ha="left", va="center", fontsize=10, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))

    # Right: compact zone labels preserve the court geography while replacing
    # dozens of overlapping shot dots with makes/attempts, FG%, and diet share.
    ax.text(444, section_y, "BULLS SHOT DIET", ha="left", va="top", fontsize=11, color=RED, fontproperties=body_font("bold"))
    t, _, _, _ = _draw_half_court(ax, right=996, y_center=866, s=0.94, line_color=COURT_LINE)
    zone_positions = {
        "restricted": t(0, 4),
        "paint": t(0, 94),
        "mid": t(0, 184),
        "left_corner": t(-220, 80),
        "right_corner": t(220, 80),
        "above_break": t(0, 274),
    }
    max_share = max((zone.share for zone in data.zones), default=1) or 1
    for zone in data.zones:
        x, y = zone_positions[zone.key]
        strength = zone.share / max_share if zone.attempts else 0
        mix = 0.12 + 0.68 * strength if zone.attempts else 0.04
        fill_rgb = tuple((1 - mix) * a + mix * b for a, b in zip(mcolors.to_rgb(PANEL_RED), mcolors.to_rgb(RED)))
        text_color = WHITE if mix >= 0.5 else DEFAULT_THEME.ink
        w = 80 if "corner" in zone.key else 108
        h = 50
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=7", facecolor=fill_rgb, edgecolor="none", zorder=4))
        ax.text(x, y + 12, f"{zone.makes}/{zone.attempts}", ha="center", va="center", fontsize=10.5, color=text_color, fontproperties=body_font("bold"), zorder=5)
        ax.text(x, y - 2, f"{zone.percentage:.1f}%", ha="center", va="center", fontsize=7.2, color=text_color, fontproperties=body_font("medium"), zorder=5)
        ax.text(x, y - 16, f"{zone.share:.1f}% OF FGA", ha="center", va="center", fontsize=6.3, color=text_color, fontproperties=body_font("bold"), zorder=5)
    for index, line in enumerate(data.shooting_splits):
        ax.text(761, 680 - index * 23, line, ha="center", va="center", fontsize=10.5, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))

    # The featured players render as one Great Tables comparison so the table
    # engine, not per-card coordinates, owns row rhythm and alignment.
    table_png = _player_table_image(data.players, OUTPUT_DIR / "_player_table.png")
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
    data: PlayerSlideData,
):
    """One full slide per player, in the C2 anatomy-study structure: identity
    header, a large exact-location FGA chart on the left as the evidence
    layer, and a compact supporting stat rail on the right."""
    fig, ax = new_canvas()
    draw_jersey_stripe(ax)

    # The player is the slide title; the headshot and outlined name form one
    # identity block, while the date stays quiet underneath.
    headshot_label(ax, data.headshot, 118, 1218, radius=54)
    title = _fitted_text(ax, 196, 1274, data.display_name, display_font(), 48, 824, DEFAULT_THEME.ink)
    title.set_path_effects([
        pe.withStroke(linewidth=7, foreground=RED),
        pe.withStroke(linewidth=3.5, foreground=WHITE),
        pe.Normal(),
    ])
    ax.text(198, 1163, data.header.subtitle_parts[0][0], ha="left", va="top", fontsize=13, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))

    identity_chips = [(item.value, item.label, item.color) for item in data.identity_stats]
    _chip_row(ax, identity_chips, 60, 1098, w=145, h=62, gap=18, value_size=16, facecolor=CHIP_BLUSH)
    ax.plot([60, 1020], [1004, 1004], color=DEFAULT_THEME.rule, lw=1)

    # A translucent-looking Bulls-red wash groups the evidence and supporting
    # metrics into one story zone while the jersey canvas remains visible.
    ax.add_patch(
        FancyBboxPatch(
            (40, 146),
            W - 80,
            830,
            boxstyle="round,pad=0,rounding_size=18",
            facecolor=PALE_RED,
            edgecolor="none",
            alpha=0.72,
            zorder=0,
        )
    )

    ax.text(60, 952, data.attempts_label, ha="left", va="top", fontsize=11, color=RED, fontproperties=body_font("bold"))
    _draw_shot_map(
        ax,
        data.shots,
        right=660,
        y_center=582,
        s=1.2,
        line_color=COURT_LINE,
        miss_as_x=True,
    )
    ax.text(60, 314, "SHOT DISTRIBUTION", ha="left", va="top", fontsize=10, color=RED, fontproperties=body_font("bold"))
    distribution_chips = [(item.value, item.label, item.color) for item in data.zone_stats]
    _chip_row(
        ax,
        distribution_chips,
        60,
        282,
        w=190,
        h=68,
        gap=15,
        value_size=16,
        facecolor=DEFAULT_THEME.canvas,
    )

    rail_x, rail_w = 740, 280
    ax.text(rail_x, 952, "SHOT PROFILE", ha="left", va="top", fontsize=11, color=RED, fontproperties=body_font("bold"))
    card_h, gap = 80, 12
    for index, stat in enumerate(data.profile_stats):
        top = 910 - index * (card_h + gap)
        ax.add_patch(
            FancyBboxPatch(
                (rail_x, top - card_h),
                rail_w,
                card_h,
                boxstyle="round,pad=0,rounding_size=12",
                facecolor=RED if stat.highlight else DEFAULT_THEME.canvas,
                edgecolor="none",
            )
        )
        value_color = "#FFFFFF" if stat.highlight else INK
        label_color = "#F5C9D6" if stat.highlight else MUTED
        cx = rail_x + rail_w / 2
        ax.text(cx, top - card_h * 0.34, stat.value, ha="center", va="center", fontsize=23, color=value_color, fontproperties=body_font("bold"))
        ax.text(cx, top - card_h * 0.73, stat.label, ha="center", va="center", fontsize=9, color=label_color, fontproperties=body_font("bold"))
    _draw_footer(ax)
    return fig


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-id", help="NBA.com game ID; omit to auto-resolve the latest completed Bulls game")
    parser.add_argument("--season", default=str(date.today().year), help="Summer League year used to auto-resolve the game")
    parser.add_argument("--player", action="append", dest="players", help="Featured Bulls player; repeat one to four times")
    parser.add_argument(
        "--highlight-player-stat",
        action="append",
        default=[],
        metavar="PLAYER:STAT",
        help="Color one identity-stat value red, for example 'Caleb Wilson:BLK'; repeat as needed",
    )
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
        raise SystemExit("Carousel mode needs one to four --player names.")
    if args.players and not 1 <= len(args.players) <= 4:
        raise SystemExit("Choose one to four featured players.")

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
    print(
        "\nShot diet uses NBA.com shot zones. TS% can read high under the 2026"
        " one-free-throw rule; interpret it as Summer League context."
    )
    if not args.players:
        print("\nChoose one to four players and matching lenses, then re-run. See --help for an example.")
        return

    needs_shots = args.carousel or (args.lens and "shot_diet" in args.lens)
    if needs_shots and shots.empty:
        raise SystemExit("The shot chart for this game is not available yet; choose another lens or retry shortly.")
    selected = select_players(bulls, args.players)
    highlights: dict[str, set[str]] = {}
    valid_identity_stats = {"PTS", "MIN", "REB", "AST", "STL", "BLK"}
    for selection in args.highlight_player_stat:
        try:
            player_name, stat = (part.strip() for part in selection.rsplit(":", 1))
        except ValueError as exc:
            raise SystemExit("Each --highlight-player-stat must use PLAYER:STAT, such as 'Caleb Wilson:BLK'.") from exc
        stat = stat.upper()
        if not player_name or stat not in valid_identity_stats:
            allowed = ", ".join(sorted(valid_identity_stats))
            raise SystemExit(f"Invalid highlight '{selection}'. Stat must be one of: {allowed}.")
        if not any(_player_name(player).casefold() == player_name.casefold() for player in selected):
            raise SystemExit(f"Highlighted player '{player_name}' must also be passed with --player.")
        highlights.setdefault(player_name.casefold(), set()).add(stat)
    # Slide 1 carries no kicker by default; --kicker adds an approved editorial line.
    kicker = args.kicker
    played_on = game_day(summary)
    graphic_date = args.date or played_on.strftime("%b %d, %Y").upper()
    dpi = export_dpi(args.final)

    if args.carousel:
        team_slide = prepare_team_slide(
            team_row,
            opponent_row,
            selected,
            shots,
            graphic_date,
            kicker,
        )
        player_slides = [
            prepare_player_slide(
                player,
                team_row,
                opponent_row,
                shots,
                graphic_date,
                None,
                frozenset(highlights.get(_player_name(player).casefold(), set())),
            )
            for player in selected
        ]
        slides = [render_team_slide(team_slide)]
        slides += [
            render_player_slide(player_slide)
            for player_slide in player_slides
        ]
        for index, fig in enumerate(slides, start=1):
            output = OUTPUT_DIR / f"{played_on.isoformat()}-summer-league-report-s{index}.png"
            save_post(fig, output, final=args.final)
            plt.close(fig)
            print(f"Saved {output} at {dpi} DPI")
        return

    fig = render_report(team_row, opponent_row, selected, args.lens, shots, graphic_date, kicker)
    output = OUTPUT_DIR / f"{played_on.isoformat()}-summer-league-report.png"
    save_post(fig, output, final=args.final)
    plt.close(fig)
    print(f"\nSaved {output} at {dpi} DPI")


if __name__ == "__main__":
    main()
