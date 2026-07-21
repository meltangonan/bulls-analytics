"""Build the 2026 Bulls Summer League sticky shot-profile carousel.

Slide 1 asks what Summer League can tell us, slide 2 explains the published
research behind two repeatable shot-diet rates, and slide 3 applies those rates
to five Bulls within the 2026 Summer League player pool.

NBA.com does not currently return the league-wide Summer League player dashboard
through ``nba_api``, so the script caches one traditional box score and one shot
chart per completed game. Re-renders read those ignored cache files instead of
repeating roughly 150 network calls.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch
from nba_api.stats.endpoints import boxscoretraditionalv3, leaguegamefinder, shotchartdetail

from bulls.config import API_DELAY
from bulls.data.fetch import _NBA_HEADERS, get_player_headshot
from bulls.graphics.craft import headshot_label
from bulls.graphics.house import (
    CANVAS_WIDTH,
    DEFAULT_THEME,
    RED,
    WHITE,
    body_font,
    display_font,
    draw_footer,
    draw_header,
    draw_jersey_stripe,
    new_canvas,
    rendered_width,
    save_post,
)


SEASON = "2026"
SUMMER_LEAGUES = {
    "13": "California Classic",
    "16": "Salt Lake City",
    "15": "Las Vegas",
}
MIN_MINUTES = 50.0
REQUEST_RETRIES = 5
CACHE_DIR = _REPO / "cache" / "sl_sticky_stats_2026"
OUTPUT_DIR = _REPO / "output" / "feed"
OUTPUT_STEM = "2026-07-20-sl-shot-profile"

# Essengue dropped from the featured set 2026-07-21 (user edit); he remains in
# the plotted pool as an unlabeled context dot.
FEATURED_PLAYERS = (
    "Caleb Wilson",
    "Dailyn Swain",
    "Jaylin Sellers",
    "Donovan Atwell",
)


def parse_minutes(value: object) -> float:
    """Convert NBA clock or ISO duration text into decimal minutes."""
    raw = str(value or "").strip()
    if not raw or raw.lower() == "nan":
        return 0.0
    if raw.startswith("PT"):
        raw = raw[2:]
        minutes_text, _, seconds_text = raw.partition("M")
        seconds_text = seconds_text.rstrip("S")
        return float(minutes_text or 0) + float(seconds_text or 0) / 60
    if ":" in raw:
        minutes_text, seconds_text = raw.split(":", 1)
        whole_minutes = float(minutes_text or 0)
        # One 2026 California Classic box score prefixes some normal 10–39
        # minute values with an erroneous "1" (for example 129:53). A player
        # cannot log 100 minutes in one Summer League game, so remove it.
        if whole_minutes >= 100:
            whole_minutes -= 100
        return whole_minutes + float(seconds_text or 0) / 60
    return float(raw)


def is_dunk(action_type: object) -> bool:
    """NBA shot-detail labels every dunk variant with the word ``Dunk``."""
    return "dunk" in str(action_type or "").lower()


def prepare_shot_profiles(
    box_scores: pd.DataFrame,
    shots: pd.DataFrame,
    min_minutes: float = MIN_MINUTES,
) -> pd.DataFrame:
    """Aggregate volume and calculate shot-diet rates for each qualifier.

    The plotted metrics are ``3PA / total FGA`` and ``rim FGA / total FGA``
    (restricted-area attempts). Shot-detail FGA must reconcile to the finalized
    traditional box score before a shot-derived rate is assigned.
    """
    box = box_scores.copy()
    box["minutes_decimal"] = box["minutes"].map(parse_minutes)
    box["name"] = (
        box["firstName"].fillna("").str.strip()
        + " "
        + box["familyName"].fillna("").str.strip()
    ).str.strip()
    if "fieldGoalsAttempted" not in box:
        box["fieldGoalsAttempted"] = 0
    if "threePointersAttempted" not in box:
        box["threePointersAttempted"] = 0
    box["box_fga"] = pd.to_numeric(box["fieldGoalsAttempted"], errors="coerce").fillna(0)
    box["box_3pa"] = pd.to_numeric(box["threePointersAttempted"], errors="coerce").fillna(0)

    minutes = (
        box.groupby("personId", as_index=False)
        .agg(
            name=("name", "last"),
            team=("teamTricode", "last"),
            minutes=("minutes_decimal", "sum"),
            games=("minutes_decimal", lambda values: int((values > 0).sum())),
            box_fga=("box_fga", "sum"),
            box_3pa=("box_3pa", "sum"),
        )
        .rename(columns={"personId": "player_id"})
    )

    attempt_mask = shots["SHOT_ATTEMPTED_FLAG"].fillna(0).astype(int).eq(1)
    rim_mask = shots["SHOT_ZONE_BASIC"].eq("Restricted Area")
    dunk_mask = shots["ACTION_TYPE"].map(is_dunk)
    shot_rows = shots.loc[attempt_mask].copy()
    shot_rows["rim_fga"] = rim_mask.loc[shot_rows.index].astype(int)
    shot_rows["dunks"] = (rim_mask & dunk_mask).loc[shot_rows.index].astype(int)
    shot_counts = (
        shot_rows.groupby("PLAYER_ID", as_index=False)
        .agg(fga=("SHOT_ATTEMPTED_FLAG", "sum"), rim_fga=("rim_fga", "sum"), dunks=("dunks", "sum"))
        .rename(columns={"PLAYER_ID": "player_id"})
    )

    profiles = minutes.merge(shot_counts, on="player_id", how="left")
    for column in ("fga", "rim_fga", "dunks"):
        profiles[column] = profiles[column].fillna(0).astype(int)
    profiles["box_fga"] = profiles["box_fga"].astype(int)
    profiles["box_3pa"] = profiles["box_3pa"].astype(int)
    profiles["fga_gap"] = profiles["box_fga"] - profiles["fga"]
    profiles["shot_complete"] = profiles["fga_gap"].eq(0)
    profiles["qualified"] = profiles["minutes"] >= min_minutes
    profiles["dunk_rate"] = np.where(
        (profiles["box_fga"] > 0) & profiles["shot_complete"],
        100 * profiles["dunks"] / profiles["box_fga"],
        np.nan,
    )
    profiles["rim_rate"] = np.where(
        (profiles["box_fga"] > 0) & profiles["shot_complete"],
        100 * profiles["rim_fga"] / profiles["box_fga"],
        np.nan,
    )
    profiles["three_pt_attempt_rate"] = np.where(
        profiles["box_fga"] > 0,
        100 * profiles["box_3pa"] / profiles["box_fga"],
        np.nan,
    )

    rankable = profiles["qualified"] & profiles["dunk_rate"].notna()
    profiles["dunk_rank"] = np.nan
    profiles["dunk_percentile"] = np.nan
    profiles.loc[rankable, "dunk_rank"] = profiles.loc[rankable, "dunk_rate"].rank(
        method="min", ascending=False
    )
    profiles.loc[rankable, "dunk_percentile"] = 100 * profiles.loc[
        rankable, "dunk_rate"
    ].rank(method="average", pct=True)
    profiles["rim_rank"] = np.nan
    profiles["rim_percentile"] = np.nan
    profiles.loc[rankable, "rim_rank"] = profiles.loc[rankable, "rim_rate"].rank(
        method="min", ascending=False
    )
    profiles.loc[rankable, "rim_percentile"] = 100 * profiles.loc[
        rankable, "rim_rate"
    ].rank(method="average", pct=True)
    profiles["three_pt_rank"] = np.nan
    profiles["three_pt_percentile"] = np.nan
    profiles.loc[rankable, "three_pt_rank"] = profiles.loc[
        rankable, "three_pt_attempt_rate"
    ].rank(method="min", ascending=False)
    profiles.loc[rankable, "three_pt_percentile"] = 100 * profiles.loc[
        rankable, "three_pt_attempt_rate"
    ].rank(method="average", pct=True)
    return profiles.sort_values(["qualified", "dunk_rate", "minutes"], ascending=[False, False, False])


def _cache_file(kind: str, game_id: str) -> Path:
    return CACHE_DIR / kind / f"{game_id}.csv"


def _fetch_game_ids(refresh: bool = False) -> list[str]:
    all_game_ids: set[str] = set()
    for league_id, event_name in SUMMER_LEAGUES.items():
        cache_path = CACHE_DIR / f"games_{league_id}.csv"
        legacy_vegas_path = CACHE_DIR / "games.csv"
        if league_id == "15" and legacy_vegas_path.exists() and not cache_path.exists() and not refresh:
            games = pd.read_csv(legacy_vegas_path, dtype={"GAME_ID": str})
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            games.to_csv(cache_path, index=False)
        elif cache_path.exists() and not refresh:
            games = pd.read_csv(cache_path, dtype={"GAME_ID": str})
        else:
            games = leaguegamefinder.LeagueGameFinder(
                league_id_nullable=league_id,
                season_nullable=SEASON,
                timeout=60,
                headers=_NBA_HEADERS,
            ).get_data_frames()[0]
            if games.empty:
                raise RuntimeError(f"NBA.com returned no 2026 {event_name} games.")
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            games.to_csv(cache_path, index=False)
        event_ids = set(games["GAME_ID"].astype(str).unique())
        print(f"{event_name}: {len(event_ids)} games", flush=True)
        all_game_ids.update(event_ids)
    return sorted(all_game_ids)


def _fetch_box_score(game_id: str, refresh: bool) -> pd.DataFrame:
    path = _cache_file("box", game_id)
    if path.exists() and not refresh:
        cached = pd.read_csv(path, dtype={"personId": int})
        if "threePointersAttempted" in cached:
            return cached
        print(f"  backfilling 3PA for {game_id}", flush=True)
    frame = pd.DataFrame()
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            frame = boxscoretraditionalv3.BoxScoreTraditionalV3(
                game_id=game_id,
                timeout=60,
                headers=_NBA_HEADERS,
            ).player_stats.get_data_frame()
            break
        except Exception as error:
            if attempt == REQUEST_RETRIES:
                raise RuntimeError(f"Box score failed for {game_id} after {attempt} attempts") from error
            wait = attempt * 2
            print(f"  box retry {attempt}/{REQUEST_RETRIES - 1} for {game_id} in {wait}s", flush=True)
            time.sleep(wait)
    if frame.empty:
        raise RuntimeError(f"NBA.com returned no box score for {game_id}.")
    columns = [
        "personId",
        "firstName",
        "familyName",
        "teamId",
        "teamTricode",
        "minutes",
        "fieldGoalsAttempted",
        "threePointersAttempted",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    frame[columns].to_csv(path, index=False)
    time.sleep(API_DELAY)
    return frame[columns]


def _fetch_shots(game_id: str, refresh: bool) -> pd.DataFrame:
    path = _cache_file("shots", game_id)
    if path.exists() and not refresh:
        return pd.read_csv(path, dtype={"PLAYER_ID": int})
    frame = pd.DataFrame()
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            frame = shotchartdetail.ShotChartDetail(
                league_id=str(game_id)[:2],
                team_id=0,
                player_id=0,
                game_id_nullable=game_id,
                season_type_all_star="Regular Season",
                context_measure_simple="FGA",
                timeout=60,
                headers=_NBA_HEADERS,
            ).get_data_frames()[0]
            break
        except Exception as error:
            if attempt == REQUEST_RETRIES:
                raise RuntimeError(f"Shot chart failed for {game_id} after {attempt} attempts") from error
            wait = attempt * 2
            print(f"  shots retry {attempt}/{REQUEST_RETRIES - 1} for {game_id} in {wait}s", flush=True)
            time.sleep(wait)
    if frame.empty:
        raise RuntimeError(f"NBA.com returned no shot chart for {game_id}.")
    columns = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ID",
        "TEAM_NAME",
        "SHOT_ZONE_BASIC",
        "ACTION_TYPE",
        "SHOT_ATTEMPTED_FLAG",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    frame[columns].to_csv(path, index=False)
    time.sleep(API_DELAY)
    return frame[columns]


def fetch_league_data(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch or load every completed 2026 Summer League game."""
    game_ids = _fetch_game_ids(refresh=refresh)
    boxes: list[pd.DataFrame] = []
    shots: list[pd.DataFrame] = []
    total = len(game_ids)
    for index, game_id in enumerate(game_ids, 1):
        boxes.append(_fetch_box_score(game_id, refresh=refresh))
        shots.append(_fetch_shots(game_id, refresh=refresh))
        print(f"[{index:02d}/{total}] {game_id} cached", flush=True)
    return pd.concat(boxes, ignore_index=True), pd.concat(shots, ignore_index=True)


# Helvetica for the Canva-assembled chart export only (user-directed
# 2026-07-21); the house Archivo faces still own every in-repo poster render.
HELVETICA_TTC = Path("/System/Library/Fonts/Helvetica.ttc")
HELVETICA_FACES = {"regular": 0, "bold": 1}
FONT_CACHE_DIR = _REPO / "cache" / "fonts"


def helvetica(weight: str = "regular") -> FontProperties:
    """Return a Helvetica face, extracting real Bold from the macOS collection.

    matplotlib registers only the Regular face of ``Helvetica.ttc``, so asking
    for ``weight="bold"`` by family name silently renders regular. Split the
    requested face out of the collection once into the ignored cache directory
    and load it by filename instead. Extraction stays in ``cache/`` so the
    licensed system font is never copied into the repository. Falls back to the
    house Archivo faces when Helvetica is unavailable (non-macOS).
    """
    fallback = "bold" if weight == "bold" else "medium"
    if not HELVETICA_TTC.exists():
        return body_font(fallback)
    extracted = FONT_CACHE_DIR / f"Helvetica-{weight}.ttf"
    if not extracted.exists():
        try:
            from fontTools.ttLib import TTCollection

            collection = TTCollection(str(HELVETICA_TTC))
            FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            collection.fonts[HELVETICA_FACES.get(weight, 0)].save(str(extracted))
        except Exception:
            return body_font(fallback)
    return FontProperties(fname=str(extracted))


# User-saved ESPN headshots preferred over NBA CDN photos (2026-07-21). Keys are
# roster names; values are the exact saved filenames ("jailyn" spelling is in
# the file on disk). Essengue has no saved ESPN photo yet and falls through to
# the NBA-ID path.
ESPN_HEADSHOTS = {
    "Caleb Wilson": "caleb-wilson-headshot.png",
    "Dailyn Swain": "dailyn-swain-headshot.png",
    "Jaylin Sellers": "jailyn-sellers-headshot.png",
    "Donovan Atwell": "donovan-atwell-headshot.png",
}


def _headshot_path(player_id: int, name: str | None = None) -> Path | None:
    if name and name in ESPN_HEADSHOTS:
        espn = _REPO / "assets" / "img" / ESPN_HEADSHOTS[name]
        if espn.exists():
            return espn
    local = _REPO / "assets" / "img" / "players" / f"{int(player_id)}.png"
    if local.exists():
        return local
    return get_player_headshot(int(player_id))


def _featured_profiles(profiles: pd.DataFrame) -> pd.DataFrame:
    featured = profiles[profiles["name"].isin(FEATURED_PLAYERS)].copy()
    missing = [name for name in FEATURED_PLAYERS if name not in set(featured["name"])]
    if missing:
        raise RuntimeError(f"Featured Bulls missing from the 2026 data: {', '.join(missing)}")
    featured["order"] = featured["name"].map({name: index for index, name in enumerate(FEATURED_PLAYERS)})
    return featured.sort_values("order")


def _centered_display_lines(ax, lines, y_top: float, theme, max_width: float = 940.0,
                            gap: float = 1.12) -> float:
    """Draw centered Academic M54 title lines at one shared fitted size.

    ``lines`` is a sequence of segment lists ``[(text, color), ...]``. Every line
    is measured first and the smallest fitted size wins, so a two-line cover
    title keeps one consistent glyph height. Returns the y below the last line.
    """
    font = display_font()
    size = None
    for segments in lines:
        text = "".join(part for part, _ in segments)
        probe = ax.text(0, 0, text, fontsize=100, fontproperties=font, alpha=0)
        width = rendered_width(ax, probe)
        probe.remove()
        if width > 0:
            fitted = 100 * max_width / width
            size = fitted if size is None else min(size, fitted)
    size = size or 60
    y = y_top
    line_height = size * 2.08 * gap
    for segments in lines:
        text = "".join(part for part, _ in segments)
        probe = ax.text(0, 0, text, fontsize=size, fontproperties=font, alpha=0)
        width = rendered_width(ax, probe)
        probe.remove()
        cursor = (CANVAS_WIDTH - width) / 2
        for part, color in segments:
            artist = ax.text(cursor, y, part, ha="left", va="top", fontsize=size,
                             color=color, fontproperties=font)
            artist.set_path_effects([
                pe.withStroke(linewidth=7, foreground=RED),
                pe.withStroke(linewidth=3.5, foreground=WHITE),
                pe.Normal(),
            ])
            cursor += rendered_width(ax, artist)
        y -= line_height
    return y


def render_cover(profiles: pd.DataFrame, final: bool = False) -> Path:
    """Render slide 1: masthead, the five Bulls, and one plain question."""
    theme = DEFAULT_THEME
    fig, ax = new_canvas(theme)
    featured = _featured_profiles(profiles)
    draw_jersey_stripe(ax, theme)

    face_layout = {
        "Caleb Wilson": (540, 1015, 115),
        "Dailyn Swain": (205, 985, 78),
        "Noa Essengue": (368, 1050, 86),
        "Jaylin Sellers": (712, 1050, 86),
        "Donovan Atwell": (875, 985, 78),
    }
    for _, player in featured.iterrows():
        name = str(player["name"])
        x, y, radius = face_layout[name]
        is_caleb = name == "Caleb Wilson"
        headshot_label(ax, _headshot_path(int(player["player_id"]), name), x, y, radius=radius,
                       border_color=(206, 17, 65) if is_caleb else (95, 91, 87))
        # One shared baseline below the lowest circle keeps the staggered
        # cluster from reading as scattered labels.
        ax.text(x, 872, name.split()[-1].upper(), ha="center", va="top",
                fontsize=11 if is_caleb else 9.5, color=theme.ink,
                fontproperties=body_font("bold"))

    # Academic M54 has no "?" glyph, so the title reads as a topic statement.
    title_lines = (
        [("WHAT ", theme.ink), ("STICKS", theme.accent), (" FROM", theme.ink)],
        [("SUMMER LEAGUE", theme.ink)],
    )
    below = _centered_display_lines(ax, title_lines, 700, theme)
    ax.text(CANVAS_WIDTH / 2, below - 8,
            "a research-backed look at what Summer League can really tell us",
            ha="center", va="top", fontsize=13, color=theme.muted,
            fontproperties=body_font("medium"))

    ax.plot([415, 665], [180, 180], color=theme.rule, lw=1.4)
    ax.text(CANVAS_WIDTH / 2, 154, "1 / 3  ·  SWIPE FOR THE ANSWER  →",
            ha="center", va="center", fontsize=10.5, color=theme.muted,
            fontproperties=body_font("bold"))

    draw_footer(ax, source="", theme=theme)
    output = OUTPUT_DIR / f"{OUTPUT_STEM}-s1-cover.png"
    save_post(fig, output, final=final)
    plt.close(fig)
    return output


def render_definitions(final: bool = False) -> Path:
    """Render slide 2: how the research compares Summer League to rookie year."""
    theme = DEFAULT_THEME
    fig, ax = new_canvas(theme)
    draw_header(
        ax,
        [("HOW THE ", theme.ink), ("RESEARCH ", theme.accent), ("WORKS", theme.ink)],
        ["PHILLIPS ’08–24", "LEE ’17–25", "SAME PLAYERS"],
        kicker="Most box-score noise fades; shot selection is the repeatable signal",
        theme=theme,
    )

    process_y = 970
    process_cards = (
        (60, "FIRST SUMMER LEAGUE", "Measure a player's shot rate"),
        (650, "ROOKIE SEASON", "Measure that same rate again"),
    )
    for x, label, detail in process_cards:
        ax.add_patch(FancyBboxPatch(
            (x, process_y - 50), 370, 100,
            boxstyle="round,pad=0,rounding_size=14",
            facecolor="#F5F1EC", edgecolor=theme.rule, linewidth=1.0,
        ))
        ax.text(x + 22, process_y + 14, label, ha="left", va="center",
                fontsize=13, color=theme.ink, fontproperties=body_font("bold"))
        ax.text(x + 22, process_y - 18, detail, ha="left", va="center",
                fontsize=10.5, color=theme.muted, fontproperties=body_font("medium"))
    ax.annotate("", xy=(638, process_y), xytext=(442, process_y),
                arrowprops={"arrowstyle": "->", "color": theme.accent, "lw": 2.0})
    ax.text(540, process_y + 24, "COMPARE", ha="center", va="center",
            fontsize=9, color=theme.accent, fontproperties=body_font("bold"))
    ax.text(540, process_y - 24, "same player · same rate", ha="center", va="center",
            fontsize=8.5, color=theme.muted, fontproperties=body_font("medium"))

    signal_cards = (
        (
            60,
            "3PT ATTEMPT RATE",
            "R² .70",
            "Threes as a share of all field-goal attempts",
            "PHILLIPS · THE F5",
            "25 box-score stats · 485 rookies · 2008–24",
        ),
        (
            550,
            "RIM RATE",
            "R² .65",
            "Restricted-area attempts as a share of all FGA",
            "LEE · THE HARDWOOD COLLECTIVE",
            "Shot-location extension · 2017–25",
        ),
    )
    for x, metric, value, definition, source, context in signal_cards:
        ax.add_patch(FancyBboxPatch(
            (x, 555), 470, 300,
            boxstyle="round,pad=0,rounding_size=16",
            facecolor="#F3E1E7", edgecolor="none",
        ))
        ax.text(x + 28, 811, metric, ha="left", va="center", fontsize=13,
                color=theme.ink, fontproperties=body_font("bold"))
        ax.text(x + 28, 743, value, ha="left", va="center", fontsize=34,
                color=theme.accent, fontproperties=body_font("bold"))
        ax.plot([x + 28, x + 442], [700, 700], color=theme.rule, lw=1.0)
        ax.text(x + 28, 664, definition, ha="left", va="center", fontsize=10.5,
                color=theme.ink, fontproperties=body_font("medium"))
        ax.text(x + 28, 615, source, ha="left", va="center", fontsize=9.5,
                color=theme.muted, fontproperties=body_font("bold"))
        ax.text(x + 28, 585, context, ha="left", va="center", fontsize=8.5,
                color=theme.muted, fontproperties=body_font("medium"))

    ax.add_patch(FancyBboxPatch(
        (60, 365), 960, 126,
        boxstyle="round,pad=0,rounding_size=14",
        facecolor="#F5F1EC", edgecolor=theme.rule, linewidth=1.0,
    ))
    ax.text(84, 454, "WHAT R² MEANS", ha="left", va="center", fontsize=10,
            color=theme.accent, fontproperties=body_font("bold"))
    ax.text(84, 420,
            "How much the Summer League rate explains that same rookie-season rate,",
            ha="left", va="center", fontsize=12.5, color=theme.ink,
            fontproperties=body_font("medium"))
    ax.text(84, 390, "from 0 (none) to 1 (perfect).", ha="left", va="center", fontsize=12.5,
            color=theme.ink, fontproperties=body_font("medium"))

    ax.text(60, 292, "SHOT PROFILE, NOT PLAYER GRADE", ha="left", va="center",
            fontsize=10.5, color=theme.ink, fontproperties=body_font("bold"))
    ax.text(60, 260, "These measures describe a player's style — not how good they'll be.",
            ha="left", va="center", fontsize=12, color=theme.muted,
            fontproperties=body_font("regular"))

    ax.text(60, 68,
            "Research samples: 50+ Summer League minutes · 250+ rookie-season minutes",
            ha="left", va="bottom", fontsize=7.8, color=theme.faint, fontproperties=body_font())
    draw_footer(ax, source="Research via The F5 + The Hardwood Collective", theme=theme)
    output = OUTPUT_DIR / f"{OUTPUT_STEM}-s2-research.png"
    save_post(fig, output, final=final)
    plt.close(fig)
    return output


def render_shot_profile(profiles: pd.DataFrame, final: bool = False) -> Path:
    theme = DEFAULT_THEME
    fig, ax = new_canvas(theme)
    qualified = profiles[profiles["qualified"]].copy()
    rankable = qualified[
        qualified["rim_rate"].notna() & qualified["three_pt_attempt_rate"].notna()
    ].copy()
    featured = _featured_profiles(profiles)
    draw_header(
        ax,
        [("FIVE BULLS, FIVE ", theme.ink), ("SHOT DIETS", theme.accent)],
        ["ALL 3 CIRCUITS", "JUL 3–19", f"{len(rankable)} PROFILES"],
        kicker="Two rim-first · Atwell outside · Sellers both · Wilson near center",
        theme=theme,
    )

    x0, x1 = 145, 1005
    y0, y1 = 235, 1040
    x_min, x_max = 0.0, 100.0
    y_min, y_max = 0.0, 100.0

    def chart_x(value: float) -> float:
        return x0 + (value - x_min) / (x_max - x_min) * (x1 - x0)

    def chart_y(value: float) -> float:
        return y0 + (value - y_min) / (y_max - y_min) * (y1 - y0)

    panel_fill = "#F5F1EC"
    # Canvas-colored stroke behind in-chart text so pool dots never bleed
    # through a label (Atwell's caption sat on a dot in the first draft).
    halo = [pe.withStroke(linewidth=3.2, foreground=panel_fill)]
    ax.add_patch(FancyBboxPatch((x0 - 16, y0 - 14), x1 - x0 + 30, y1 - y0 + 26,
                                boxstyle="round,pad=0,rounding_size=12", facecolor=panel_fill,
                                edgecolor=theme.rule, linewidth=1.0, zorder=0))

    for value in range(0, 101, 25):
        x = chart_x(float(value))
        ax.plot([x, x], [y0, y1], color=theme.grid, lw=1.1, zorder=1)
        ax.text(x, y0 - 27, f"{value}%", ha="center", va="top", fontsize=9.5,
                color=theme.muted, fontproperties=body_font("medium"))
    for value in range(0, 101, 25):
        y = chart_y(float(value))
        ax.plot([x0, x1], [y, y], color=theme.grid, lw=1.1, zorder=1)
        ax.text(x0 - 18, y, f"{value}%", ha="right", va="center", fontsize=9.5,
                color=theme.muted, fontproperties=body_font("medium"))
    ax.plot([x0, x1], [y0, y0], color=theme.muted, lw=1.2, zorder=2)
    ax.plot([x0, x0], [y0, y1], color=theme.muted, lw=1.2, zorder=2)

    median_three_pt_rate = float(rankable["three_pt_attempt_rate"].median())
    median_rim_rate = float(rankable["rim_rate"].median())
    median_x = chart_x(median_three_pt_rate)
    median_y = chart_y(median_rim_rate)
    ax.plot([median_x, median_x], [y0, y1], color=theme.muted, lw=1.2,
            linestyle=(0, (4, 4)), alpha=0.8, zorder=2)
    ax.plot([x0, x1], [median_y, median_y], color=theme.muted, lw=1.2,
            linestyle=(0, (4, 4)), alpha=0.8, zorder=2)
    ax.text(median_x + 9, y1 - 17, f"MEDIAN {median_three_pt_rate:.1f}%", ha="left", va="top",
            fontsize=7.5,
            color=theme.muted, fontproperties=body_font("bold"), zorder=3, path_effects=halo)
    ax.text(x1 - 9, median_y + 12, f"MEDIAN {median_rim_rate:.1f}%", ha="right", va="bottom",
            fontsize=7.5, color=theme.muted, fontproperties=body_font("bold"), zorder=3,
            path_effects=halo)

    ax.text(x0 + 18, y1 - 22, "RIM-HEAVY", ha="left", va="top", fontsize=9,
            color=theme.muted, fontproperties=body_font("bold"), zorder=3, path_effects=halo)
    ax.text(x1 - 18, y1 - 22, "RIM + 3 HEAVY", ha="right", va="top", fontsize=9,
            color=theme.muted, fontproperties=body_font("bold"), zorder=3, path_effects=halo)
    ax.text(x1 - 18, y1 - 45, "FEWER OTHER 2S", ha="right", va="top", fontsize=7.2,
            color=theme.muted, fontproperties=body_font("medium"), zorder=3, path_effects=halo)
    featured_ids = set(featured["player_id"].astype(int))
    for _, player in rankable.iterrows():
        if int(player["player_id"]) in featured_ids:
            continue
        x = chart_x(float(player["three_pt_attempt_rate"]))
        y = chart_y(float(player["rim_rate"]))
        ax.add_patch(Circle((x, y), radius=4.6, facecolor=theme.muted, edgecolor=theme.canvas,
                            linewidth=0.7, alpha=0.32, zorder=3))

    face_offsets = {
        "Caleb Wilson": (28, -40),
        "Dailyn Swain": (-62, 82),
        "Noa Essengue": (6, 130),
        "Jaylin Sellers": (64, 78),
        "Donovan Atwell": (-28, 70),
    }
    for _, player in featured.iterrows():
        if not player["qualified"] or pd.isna(player["rim_rate"]):
            continue
        point_x = chart_x(float(player["three_pt_attempt_rate"]))
        point_y = chart_y(float(player["rim_rate"]))
        dx, dy = face_offsets[str(player["name"])]
        face_x, face_y = point_x + dx, point_y + dy
        is_caleb = player["name"] == "Caleb Wilson"
        radius = 47 if is_caleb else 34
        ax.plot([point_x, face_x], [point_y, face_y], color=theme.accent if is_caleb else theme.muted,
                lw=1.1, alpha=0.9, zorder=4)
        ax.add_patch(Circle((point_x, point_y), radius=7 if is_caleb else 5.5,
                            facecolor=theme.accent if is_caleb else theme.muted,
                            edgecolor=theme.canvas, linewidth=1.0, zorder=5))
        image = headshot_label(ax, _headshot_path(int(player["player_id"]), str(player["name"])), face_x, face_y,
                               radius=radius,
                               border_color=(206, 17, 65) if is_caleb else (95, 91, 87))
        image.set_zorder(7)
        label_y = face_y - radius - 8
        ax.text(face_x, label_y, str(player["name"]).split()[-1].upper(), ha="center", va="top",
                fontsize=10.5 if is_caleb else 8.8, color=theme.ink,
                fontproperties=body_font("bold"), zorder=8, path_effects=halo)
        ax.text(face_x, label_y - 21,
                f"{player['three_pt_attempt_rate']:.1f}% 3PT · {player['rim_rate']:.1f}% RIM",
                ha="center", va="top", fontsize=8.8 if is_caleb else 8.0,
                color=theme.accent if is_caleb else theme.muted,
                fontproperties=body_font("medium"), zorder=8, path_effects=halo)

    ax.text((x0 + x1) / 2, 160, "3PT ATTEMPT RATE  (% OF FGA)", ha="center", va="center",
            fontsize=15, color=theme.ink, fontproperties=body_font("bold"))
    ax.text(58, (y0 + y1) / 2, "RIM RATE  (% OF FGA)", ha="center", va="center", rotation=90,
            fontsize=15, color=theme.ink, fontproperties=body_font("bold"))

    ax.text(60, 90,
            "Each axis is a separate SL→rookie signal; this scatter is not a regression between the axes.",
            ha="left", va="bottom", fontsize=7.8, color=theme.muted, fontproperties=body_font("medium"))
    ax.text(60, 68,
            f"Min. {int(MIN_MINUTES)} SL minutes · {len(rankable)} of {len(qualified)} qualified players have fully reconciled shot detail",
            ha="left", va="bottom", fontsize=7.8, color=theme.faint, fontproperties=body_font())
    draw_footer(ax, source="Data via nba.com · Research via The F5 + The Hardwood Collective", theme=theme)
    output = OUTPUT_DIR / f"{OUTPUT_STEM}-s3-bulls.png"
    save_post(fig, output, final=final)
    plt.close(fig)
    return output


def render_chart_only(profiles: pd.DataFrame, final: bool = False) -> Path:
    """Render the slide-3 scatter alone for assembly in an external layout tool.

    The Canva template owns the title, subtitle, kicker, footer, and watermark,
    so this export draws only the chart panel, axis titles, and the
    stat-derived fine print (threshold and reconciliation counts), which must
    travel with the chart so the template cannot drift from the data. The
    figure background is transparent: the rounded panel sits directly on the
    destination canvas without a color-mismatch seam.
    """
    theme = DEFAULT_THEME
    width, height = 1080, 1030
    fig = plt.figure(figsize=(width / 150, height / 150))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_alpha(0)

    qualified = profiles[profiles["qualified"]].copy()
    rankable = qualified[
        qualified["rim_rate"].notna() & qualified["three_pt_attempt_rate"].notna()
    ].copy()
    featured = _featured_profiles(profiles)

    # Margins are deliberately generous: the axis titles and fine print sit
    # well inside the edge so a Canva frame that crops slightly cannot clip
    # them off the graphic.
    x0, x1 = 190, 1015
    y0, y1 = 175, 950
    # The plotted range runs past 0–100% so a portrait centered on an extreme
    # value (Atwell at 2.8% rim) still sits fully inside the panel instead of
    # being clipped by the axis.
    x_min, x_max = -6.0, 106.0
    y_min, y_max = -14.0, 104.0

    def chart_x(value: float) -> float:
        return x0 + (value - x_min) / (x_max - x_min) * (x1 - x0)

    def chart_y(value: float) -> float:
        return y0 + (value - y_min) / (y_max - y_min) * (y1 - y0)

    panel_fill = "#F5F1EC"
    halo = [pe.withStroke(linewidth=3.2, foreground=panel_fill)]
    # Borderless panel: the Canva page supplies any framing, so the export
    # carries fill only and never doubles up on an outline.
    panel = FancyBboxPatch((x0 - 16, y0 - 14), x1 - x0 + 30, y1 - y0 + 26,
                           boxstyle="round,pad=0,rounding_size=12", facecolor=panel_fill,
                           edgecolor="none", zorder=0)
    ax.add_patch(panel)

    # The panel stays one flat off-white. A tinted quadrant wash was tried and
    # removed: it made the dots and portraits harder to read, and any
    # corner-to-corner ramp risks implying that one shot diet is better than
    # another.
    #
    # Axes drawn in ink with outward tick marks so the frame of reference stays
    # legible once the chart is scaled down inside a Canva page.
    for value in range(0, 101, 25):
        x = chart_x(float(value))
        ax.plot([x, x], [y0, y1], color=theme.grid, lw=1.1, zorder=1)
        ax.plot([x, x], [y0, y0 - 10], color=theme.ink, lw=1.6, zorder=3)
        ax.text(x, y0 - 22, f"{value}%", ha="center", va="top", fontsize=13,
                color=theme.ink, fontproperties=helvetica())
    for value in range(0, 101, 25):
        y = chart_y(float(value))
        ax.plot([x0, x1], [y, y], color=theme.grid, lw=1.1, zorder=1)
        ax.plot([x0, x0 - 10], [y, y], color=theme.ink, lw=1.6, zorder=3)
        ax.text(x0 - 20, y, f"{value}%", ha="right", va="center", fontsize=13,
                color=theme.ink, fontproperties=helvetica())
    ax.plot([x0, x1], [y0, y0], color=theme.ink, lw=2.2, zorder=3)
    ax.plot([x0, x0], [y0, y1], color=theme.ink, lw=2.2, zorder=3)

    median_three_pt_rate = float(rankable["three_pt_attempt_rate"].median())
    median_rim_rate = float(rankable["rim_rate"].median())
    median_x = chart_x(median_three_pt_rate)
    median_y = chart_y(median_rim_rate)
    ax.plot([median_x, median_x], [y0, y1], color=theme.muted, lw=1.2,
            linestyle=(0, (4, 4)), alpha=0.8, zorder=2)
    ax.plot([x0, x1], [median_y, median_y], color=theme.muted, lw=1.2,
            linestyle=(0, (4, 4)), alpha=0.8, zorder=2)
    ax.text(median_x + 9, y1 - 17, f"MEDIAN {median_three_pt_rate:.1f}%", ha="left", va="top",
            fontsize=9,
            color=theme.muted, fontproperties=helvetica("bold"), zorder=3, path_effects=halo)
    ax.text(x1 - 9, median_y + 12, f"MEDIAN {median_rim_rate:.1f}%", ha="right", va="bottom",
            fontsize=9, color=theme.muted, fontproperties=helvetica("bold"), zorder=3,
            path_effects=halo)

    def quadrant_pill(anchor_x, anchor_y, ha, va, title, detail):
        """Draw one corner key: a style name and what it means, in plain words."""
        probe = ax.text(0, 0, title, fontsize=10.5, fontproperties=helvetica("bold"), alpha=0)
        title_width = rendered_width(ax, probe)
        probe.remove()
        probe = ax.text(0, 0, detail, fontsize=9.5, fontproperties=helvetica(), alpha=0)
        detail_width = rendered_width(ax, probe)
        probe.remove()
        box_w = max(title_width, detail_width) + 32
        box_h = 66
        left = anchor_x if ha == "left" else anchor_x - box_w
        bottom = anchor_y if va == "bottom" else anchor_y - box_h
        ax.add_patch(FancyBboxPatch((left, bottom), box_w, box_h,
                                    boxstyle="round,pad=0,rounding_size=11",
                                    facecolor=theme.canvas, edgecolor=theme.rule,
                                    linewidth=1.0, alpha=0.94, zorder=6))
        ax.text(left + 16, bottom + box_h - 21, title, ha="left", va="center", fontsize=10.5,
                color=theme.ink, fontproperties=helvetica("bold"), zorder=7)
        ax.text(left + 16, bottom + 20, detail, ha="left", va="center", fontsize=9.5,
                color=theme.muted, fontproperties=helvetica(), zorder=7)

    # Quadrant keys name the shot diet and then say plainly what it means.
    # Details stay short so the pills fit the corners without crowding the
    # portraits. The bottom-right key is anchored just right of the median
    # rather than in its corner, which Atwell's portrait occupies.
    # Keys are pinned to the 0–100% data area, not the padded panel edge, so
    # they sit inside the chart rather than floating in the margin.
    key_top = chart_y(100.0) - 12
    # The bottom keys tuck just under the 0% line: it keeps them clear of
    # Wilson's stat label without pushing them into the panel margin.
    key_bottom = chart_y(0.0) - 12
    # Each key's second line restates both axes in the same parallel form, so a
    # reader can decode any quadrant without re-reading the axis titles.
    quadrant_pill(chart_x(0.0) + 14, key_top, "left", "top",
                  "PAINT-FIRST", "higher rim, lower 3PT")
    quadrant_pill(chart_x(100.0) - 14, key_top, "right", "top",
                  "RIM + THREES", "higher rim, higher 3PT")
    quadrant_pill(chart_x(0.0) + 14, key_bottom, "left", "bottom",
                  "MID-RANGE LEAN", "lower rim, lower 3PT")
    quadrant_pill(median_x + 20, key_bottom, "left", "bottom",
                  "PERIMETER-FIRST", "lower rim, higher 3PT")
    featured_ids = set(featured["player_id"].astype(int))
    for _, player in rankable.iterrows():
        if int(player["player_id"]) in featured_ids:
            continue
        x = chart_x(float(player["three_pt_attempt_rate"]))
        y = chart_y(float(player["rim_rate"]))
        ax.add_patch(Circle((x, y), radius=4.6, facecolor=theme.muted, edgecolor=theme.canvas,
                            linewidth=0.7, alpha=0.32, zorder=3))

    # The portrait *is* the data point: each headshot is centered on the
    # player's exact coordinates with no connector line, so position alone
    # carries the reading. Portraits sit above the pool dots and may cover a
    # few of them.
    radius = 46
    for _, player in featured.iterrows():
        if not player["qualified"] or pd.isna(player["rim_rate"]):
            continue
        point_x = chart_x(float(player["three_pt_attempt_rate"]))
        point_y = chart_y(float(player["rim_rate"]))
        name = str(player["name"])
        image = headshot_label(ax, _headshot_path(int(player["player_id"]), name),
                               point_x, point_y, radius=radius, border_color=None)
        image.set_zorder(9)
        values = f"{player['three_pt_attempt_rate']:.1f}% 3PT  ×  {player['rim_rate']:.1f}% RIM"
        # Keep the centered label inside the panel even when the portrait sits
        # hard against an edge.
        label_x = min(max(point_x, x0 + 105), x1 - 105)
        # Flip the label above the portrait only when there is no room beneath
        # it, so edge players never print their stats outside the panel.
        if point_y - radius - 31 < y0 + 12:
            align, name_y, value_y = "bottom", point_y + radius + 34, point_y + radius + 11
        else:
            align, name_y, value_y = "top", point_y - radius - 8, point_y - radius - 31
        ax.text(label_x, name_y, name.split()[-1].upper(), ha="center", va=align,
                fontsize=9.5, color=theme.ink,
                fontproperties=helvetica("bold"), zorder=10)
        # Bulls red on every featured player's rates: the stat pair is the
        # payoff of the chart, and red is the one accent in the house palette.
        # Applied uniformly so it stays emphasis, not a ranking.
        ax.text(label_x, value_y, values,
                ha="center", va=align, fontsize=7.8,
                color=theme.accent,
                fontproperties=helvetica("bold"), zorder=10)

    ax.text((x0 + x1) / 2, 92, "3PT ATTEMPT RATE  (% OF FGA)", ha="center", va="center",
            fontsize=17, color=theme.ink, fontproperties=helvetica("bold"))
    ax.text(78, (y0 + y1) / 2, "RIM RATE  (% OF FGA)", ha="center", va="center", rotation=90,
            fontsize=17, color=theme.ink, fontproperties=helvetica("bold"))

    # The threshold/reconciliation fine print and the not-a-regression note are
    # deliberately NOT drawn here (user-directed 2026-07-21): they are typed
    # into the Canva template instead. Both are still required on the published
    # graphic — the current values are printed to stdout below so they can be
    # copied across, and they change whenever the data is refetched.

    print("Type into the Canva template (required on the published graphic):")
    print(f"  · Min. {int(MIN_MINUTES)} SL minutes · {len(rankable)} of {len(qualified)} "
          "qualified players have fully reconciled shot detail")
    print("  · Each axis is a separate Summer League-to-rookie signal; this scatter is not a "
          "regression between the axes.")
    print("  · Data via nba.com · R²: Phillips, The F5 · Lee, The Hardwood Collective")

    output = OUTPUT_DIR / f"{OUTPUT_STEM}-s3-chart-only.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300 if final else 150, transparent=True)
    plt.close(fig)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refetch all game-level NBA.com data")
    parser.add_argument("--final", action="store_true", help="Export at 300 DPI instead of draft 150 DPI")
    parser.add_argument("--fetch-only", action="store_true", help="Build/validate the cache without rendering")
    parser.add_argument(
        "--chart-only",
        action="store_true",
        help="Render only the frameless slide-3 scatter export for Canva assembly",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    box_scores, shots = fetch_league_data(refresh=args.refresh)
    profiles = prepare_shot_profiles(box_scores, shots)
    qualified = profiles[profiles["qualified"]]
    featured = _featured_profiles(profiles)

    box_fga = int(pd.to_numeric(box_scores["fieldGoalsAttempted"], errors="coerce").fillna(0).sum())
    shot_fga = int(pd.to_numeric(shots["SHOT_ATTEMPTED_FLAG"], errors="coerce").fillna(0).sum())
    print(f"Coverage: {len(box_scores):,} player-games; {len(shots):,} shots; box FGA {box_fga:,}; shot FGA {shot_fga:,}")
    print(
        f"Pool: {len(qualified)} players at {MIN_MINUTES:.0f}+ minutes; "
        f"{qualified['rim_rate'].notna().sum()} complete shot profiles"
    )
    print(
        featured[
            [
                "name",
                "games",
                "minutes",
                "rim_fga",
                "rim_rate",
                "rim_percentile",
                "box_3pa",
                "three_pt_attempt_rate",
                "three_pt_percentile",
            ]
        ].to_string(index=False)
    )
    if args.fetch_only:
        return

    if args.chart_only:
        print(render_chart_only(profiles, final=args.final))
        return

    print(render_cover(profiles, final=args.final))
    print(render_definitions(final=args.final))
    print(render_shot_profile(profiles, final=args.final))
    print(render_chart_only(profiles, final=args.final))


if __name__ == "__main__":
    main()
