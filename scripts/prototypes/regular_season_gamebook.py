"""Render four regular-season postgame concepts from one rehearsal game.

This is deliberately a deterministic visual prototype, not a live game-night
CLI. It uses the completed July 10, 2026 Bulls-Grizzlies Summer League box score
and shot chart to compare four analytical directions for a future regular-
season Gamebook:

1. Four Factors / game deciders
2. One-game fingerprint versus the Bulls' season baseline
3. Shot quality versus shot making
4. Player contribution shares

The regular-season benchmarks are frozen from official NBA.com 2025-26 data so
the concept can be reviewed without another API call. If the format is adopted,
wire the approved modules to live regular-season game and season data then.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

from bulls.graphics.house import (
    DEFAULT_THEME,
    RED,
    WHITE,
    body_font,
    draw_footer,
    draw_fitted_title,
    draw_jersey_stripe,
    draw_subtitle,
    export_dpi,
    new_canvas,
    save_post,
)

W, H = 1080, 1350
OUT = _REPO / "output" / "feed"
PALE_RED = "#F7E8ED"
SOFT_RED = "#F1D5DE"
TRACK = "#E8E2DC"


# Exact rehearsal-game totals from NBA.com game 1522600012.
CHI = {
    "points": 96,
    "fgm": 30,
    "fga": 69,
    "fg3m": 14,
    "fg3a": 32,
    "ftm": 13,
    "fta": 25,
    "oreb": 11,
    "dreb": 18,
    "ast": 14,
    "tov": 13,
}
MEM = {
    "points": 97,
    "fgm": 33,
    "fga": 70,
    "fg3m": 3,
    "fg3a": 21,
    "ftm": 17,
    "fta": 22,
    "oreb": 9,
    "dreb": 26,
    "ast": 18,
    "tov": 14,
}

PLAYERS = (
    {"name": "Caleb Wilson", "min": 32, "pts": 35, "fga": 21, "ast": 0, "reb": 5},
    {"name": "Dailyn Swain", "min": 30, "pts": 7, "fga": 10, "ast": 3, "reb": 4},
    {"name": "Jaylin Sellers", "min": 29, "pts": 15, "fga": 13, "ast": 4, "reb": 4},
    {"name": "Noa Essengue", "min": 28, "pts": 10, "fga": 5, "ast": 1, "reb": 5},
    {"name": "Malik Williams", "min": 21, "pts": 10, "fga": 6, "ast": 1, "reb": 7},
    {"name": "Kennedy Chandler", "min": 19, "pts": 11, "fga": 7, "ast": 5, "reb": 0},
    {"name": "Tobe Awaka", "min": 18, "pts": 0, "fga": 2, "ast": 0, "reb": 3},
    {"name": "Donovan Atwell", "min": 15, "pts": 6, "fga": 4, "ast": 0, "reb": 1},
    {"name": "Boo Buie", "min": 3, "pts": 2, "fga": 1, "ast": 0, "reb": 0},
)

# Aggregate 2025-26 Bulls regular-season averages, plus the rehearsal game's
# percentile among the 82 individual Bulls games. These are comparison inputs
# for the concept only; the rehearsal game itself was not a regular-season game.
REGULAR_SEASON_BENCHMARKS = {
    "efg": (54.75, 47.6),
    "three_rate": (44.32, 59.8),
    "ft_rate": (19.09, 53.7),
    "tov_rate": (12.74, 67.1),
    "assist_rate": (67.17, 0.0),
}

# NBA.com 2025-26 regular-season league shooting, aggregated to basic zones.
LEAGUE_ZONE_FG = {
    "rim": 0.670940,
    "paint": 0.445591,
    "mid": 0.416754,
    "corner_three": (0.387305 + 0.386092) / 2,
    "above_break_three": 0.350056,
}

# Rehearsal-game Bulls makes and attempts from the NBA's shot-zone labels.
SHOT_ZONES = {
    "rim": (12, 24),
    "paint": (1, 5),
    "mid": (3, 8),
    "corner_three": (5, 10),
    "above_break_three": (9, 22),
}


@dataclass(frozen=True)
class Factor:
    label: str
    definition: str
    bulls: float
    opponent: float
    lower_is_better: bool = False

    @property
    def bulls_wins(self) -> bool:
        return self.bulls < self.opponent if self.lower_is_better else self.bulls > self.opponent


@dataclass(frozen=True)
class FingerprintMetric:
    label: str
    value: float
    baseline: float
    percentile: float
    lower_is_better: bool = False


@dataclass(frozen=True)
class QualityZone:
    label: str
    attempts: int
    expected_points: float
    actual_points: float

    @property
    def delta(self) -> float:
        return self.actual_points - self.expected_points


@dataclass(frozen=True)
class Contribution:
    name: str
    minutes: int
    scoring: float
    shot_load: float
    creation: float
    rebounding: float


def _pct(numerator: float, denominator: float) -> float:
    return 100 * numerator / denominator if denominator else 0.0


def _efg(team: dict[str, float]) -> float:
    return _pct(team["fgm"] + 0.5 * team["fg3m"], team["fga"])


def _tov_rate(team: dict[str, float]) -> float:
    possessions = team["fga"] + 0.44 * team["fta"] + team["tov"]
    return _pct(team["tov"], possessions)


def prepare_factors(team: dict[str, float], opponent: dict[str, float]) -> tuple[Factor, ...]:
    """Four Factors, with ORB% using each opponent's defensive rebounds."""
    return (
        Factor("SHOT MAKING", "eFG%", _efg(team), _efg(opponent)),
        Factor("BALL SECURITY", "TOV% · LOWER IS BETTER", _tov_rate(team), _tov_rate(opponent), True),
        Factor(
            "SECOND CHANCES",
            "ORB%",
            _pct(team["oreb"], team["oreb"] + opponent["dreb"]),
            _pct(opponent["oreb"], opponent["oreb"] + team["dreb"]),
        ),
        Factor("FREE THROWS", "FTM / FGA", _pct(team["ftm"], team["fga"]), _pct(opponent["ftm"], opponent["fga"])),
    )


def prepare_fingerprint(team: dict[str, float]) -> tuple[FingerprintMetric, ...]:
    values = {
        "efg": _efg(team),
        "three_rate": _pct(team["fg3a"], team["fga"]),
        "ft_rate": _pct(team["ftm"], team["fga"]),
        "tov_rate": _tov_rate(team),
        "assist_rate": _pct(team["ast"], team["fgm"]),
    }
    metadata = (
        ("SHOT MAKING", "efg", False),
        ("THREE-POINT RATE", "three_rate", False),
        ("MADE-FT RATE", "ft_rate", False),
        ("TURNOVER RATE", "tov_rate", True),
        ("ASSISTED-FG RATE", "assist_rate", False),
    )
    return tuple(
        FingerprintMetric(label, values[key], *REGULAR_SEASON_BENCHMARKS[key], lower_is_better)
        for label, key, lower_is_better in metadata
    )


def prepare_quality_zones() -> tuple[QualityZone, ...]:
    labels = {
        "rim": "RIM",
        "paint": "PAINT (NON-RA)",
        "mid": "MID-RANGE",
        "corner_three": "CORNER THREES",
        "above_break_three": "ABOVE-BREAK THREES",
    }
    results = []
    for key, label in labels.items():
        makes, attempts = SHOT_ZONES[key]
        shot_value = 3 if "three" in key else 2
        results.append(
            QualityZone(
                label,
                attempts,
                attempts * LEAGUE_ZONE_FG[key] * shot_value,
                makes * shot_value,
            )
        )
    return tuple(results)


def prepare_contributions(
    players: tuple[dict[str, float], ...], team: dict[str, float], min_minutes: int = 10
) -> tuple[Contribution, ...]:
    qualified = [player for player in players if player["min"] >= min_minutes]
    return tuple(
        Contribution(
            player["name"],
            int(player["min"]),
            _pct(player["pts"], team["points"]),
            _pct(player["fga"], team["fga"]),
            _pct(player["ast"], team["ast"]),
            _pct(player["reb"], team["oreb"] + team["dreb"]),
        )
        for player in qualified
    )


def _base_slide(title_segments: list[tuple[str, str]], kicker: str):
    fig, ax = new_canvas()
    draw_jersey_stripe(ax)
    # Concept titles are intentionally narrower than the standard fitted
    # masthead so wide Academic M54 glyphs cannot collide with the subtitle.
    draw_fitted_title(ax, title_segments, max_width=850)
    draw_subtitle(
        ax,
        [("Bulls 96", RED), ("Grizzlies 97", DEFAULT_THEME.ink), ("Jul 10, 2026", DEFAULT_THEME.muted)],
        y=1160,
        weight="bold",
    )
    ax.text(60, 1120, kicker, ha="left", va="top", fontsize=14, color=RED, style="italic", fontproperties=body_font("medium"))
    return fig, ax


def _concept_note(ax, text: str):
    ax.text(
        60,
        78,
        text,
        ha="left",
        va="center",
        fontsize=8.3,
        color=DEFAULT_THEME.faint,
        fontproperties=body_font("medium"),
    )
    draw_footer(ax)


def render_deciders(factors: tuple[Factor, ...]):
    fig, ax = _base_slide(
        [("GAME ", DEFAULT_THEME.ink), ("DECIDERS", RED)],
        "Four Factors · regular-season format rehearsal",
    )
    ax.text(90, 1080, "CHI", color=RED, fontsize=11, ha="left", fontproperties=body_font("bold"))
    ax.text(990, 1080, "MEM", color=DEFAULT_THEME.ink, fontsize=11, ha="right", fontproperties=body_font("bold"))

    row_tops = (1035, 835, 635, 435)
    for factor, top in zip(factors, row_tops):
        ax.add_patch(
            FancyBboxPatch(
                (60, top - 150), 960, 158,
                boxstyle="round,pad=0,rounding_size=14",
                facecolor=PALE_RED,
                edgecolor="none",
            )
        )
        ax.text(540, top - 23, factor.label, ha="center", va="center", fontsize=14, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        ax.text(540, top - 48, factor.definition, ha="center", va="center", fontsize=8.5, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))
        row_max = max(factor.bulls, factor.opponent, 1)
        bar_max = 275
        bulls_w = bar_max * factor.bulls / row_max
        opponent_w = bar_max * factor.opponent / row_max
        y = top - 102
        ax.add_patch(FancyBboxPatch((525 - bulls_w, y - 12), bulls_w, 24, boxstyle="round,pad=0,rounding_size=4", facecolor=RED, edgecolor="none"))
        ax.add_patch(FancyBboxPatch((555, y - 12), opponent_w, 24, boxstyle="round,pad=0,rounding_size=4", facecolor=DEFAULT_THEME.contrast, edgecolor="none"))
        ax.text(505 - bulls_w, y, f"{factor.bulls:.1f}%", ha="right", va="center", fontsize=13, color=RED, fontproperties=body_font("bold"))
        ax.text(575 + opponent_w, y, f"{factor.opponent:.1f}%", ha="left", va="center", fontsize=13, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        edge_x = 145 if factor.bulls_wins else 935
        edge_ha = "left" if factor.bulls_wins else "right"
        edge_color = RED if factor.bulls_wins else DEFAULT_THEME.ink
        ax.text(edge_x, top - 24, "EDGE", ha=edge_ha, va="center", fontsize=8, color=edge_color, fontproperties=body_font("bold"))

    ax.add_patch(FancyBboxPatch((60, 150), 960, 120, boxstyle="round,pad=0,rounding_size=14", facecolor=DEFAULT_THEME.contrast, edgecolor="none"))
    ax.text(540, 222, "THE MARGINS SPLIT 2–2", ha="center", va="center", fontsize=19, color=WHITE, fontproperties=body_font("bold"))
    ax.text(540, 184, "Chicago won shotmaking and ball security; Memphis won the glass and free-throw line.", ha="center", va="center", fontsize=10.5, color="#E8E2DC", fontproperties=body_font("medium"))
    _concept_note(ax, "CONCEPT MOCK · SUMMER LEAGUE GAME DATA USED TO REHEARSE A REGULAR-SEASON MODULE")
    return fig


def render_fingerprint(metrics: tuple[FingerprintMetric, ...]):
    fig, ax = _base_slide(
        [("GAME ", DEFAULT_THEME.ink), ("FINGERPRINT", RED)],
        "Where one game sits inside the Bulls' season",
    )
    ax.text(60, 1070, "SEASON PERCENTILE", ha="left", va="center", fontsize=9, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))
    ax.text(1015, 1070, "GAME  /  AVG", ha="right", va="center", fontsize=9, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))

    for index, metric in enumerate(metrics):
        y = 960 - index * 150
        highlight = metric.label == "ASSISTED-FG RATE"
        ax.add_patch(FancyBboxPatch((60, y - 55), 960, 112, boxstyle="round,pad=0,rounding_size=12", facecolor=PALE_RED if highlight else "none", edgecolor="none"))
        ax.text(84, y + 24, metric.label, ha="left", va="center", fontsize=11.5, color=RED if highlight else DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        if metric.lower_is_better:
            ax.text(84, y - 2, "LOWER IS BETTER", ha="left", va="center", fontsize=7.5, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))
        x0, x1 = 320, 825
        ax.plot([x0, x1], [y, y], color=TRACK, lw=9, solid_capstyle="round")
        marker_x = x0 + (x1 - x0) * metric.percentile / 100
        ax.plot([x0, marker_x], [y, y], color=SOFT_RED if not highlight else RED, lw=9, solid_capstyle="round")
        ax.add_patch(Circle((marker_x, y), 11, facecolor=RED if highlight else DEFAULT_THEME.ink, edgecolor=DEFAULT_THEME.canvas, lw=2, zorder=4))
        ax.text(x0, y - 28, "0", ha="center", va="center", fontsize=7.5, color=DEFAULT_THEME.faint, fontproperties=body_font("medium"))
        ax.text(x1, y - 28, "100", ha="center", va="center", fontsize=7.5, color=DEFAULT_THEME.faint, fontproperties=body_font("medium"))
        ax.text(1000, y + 13, f"{metric.value:.1f}%", ha="right", va="center", fontsize=17, color=RED if highlight else DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        ax.text(1000, y - 19, f"{metric.baseline:.1f}% AVG", ha="right", va="center", fontsize=8.5, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))

    ax.add_patch(FancyBboxPatch((60, 145), 960, 120, boxstyle="round,pad=0,rounding_size=14", facecolor=RED, edgecolor="none"))
    ax.text(540, 218, "14 ASSISTS ON 30 MAKES", ha="center", va="center", fontsize=22, color=WHITE, fontproperties=body_font("bold"))
    ax.text(540, 180, "Below every game in the 82-game regular-season baseline", ha="center", va="center", fontsize=10.5, color="#F8D7E1", fontproperties=body_font("medium"))
    _concept_note(ax, "CONCEPT MOCK · GAME VALUES ARE SUMMER LEAGUE; BASELINE IS THE 2025–26 BULLS REGULAR SEASON")
    return fig


def render_shot_quality(zones: tuple[QualityZone, ...]):
    fig, ax = _base_slide(
        [("SHOT QUALITY VS ", DEFAULT_THEME.ink), ("MAKING", RED)],
        "Expected field-goal points from shot location",
    )
    expected_total = sum(zone.expected_points for zone in zones)
    actual_total = sum(zone.actual_points for zone in zones)
    summary = (
        (f"{expected_total:.1f}", "EXPECTED POINTS", DEFAULT_THEME.canvas, DEFAULT_THEME.ink),
        (f"{actual_total:.0f}", "ACTUAL POINTS", DEFAULT_THEME.canvas, DEFAULT_THEME.ink),
        (f"{actual_total - expected_total:+.1f}", "VS EXPECTATION", RED, WHITE),
    )
    for index, (value, label, fill, text_color) in enumerate(summary):
        x = 60 + index * 325
        ax.add_patch(FancyBboxPatch((x, 985), 310, 115, boxstyle="round,pad=0,rounding_size=13", facecolor=fill, edgecolor=DEFAULT_THEME.rule if fill == DEFAULT_THEME.canvas else "none", lw=1))
        ax.text(x + 155, 1055, value, ha="center", va="center", fontsize=28, color=text_color, fontproperties=body_font("bold"))
        ax.text(x + 155, 1018, label, ha="center", va="center", fontsize=8.5, color="#F8D7E1" if fill == RED else DEFAULT_THEME.muted, fontproperties=body_font("bold"))

    max_points = max(max(zone.expected_points, zone.actual_points) for zone in zones)
    for index, zone in enumerate(zones):
        y = 875 - index * 138
        ax.text(60, y + 28, zone.label, ha="left", va="center", fontsize=12, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        ax.text(60, y - 2, f"{zone.attempts} FGA", ha="left", va="center", fontsize=8.5, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))
        x0, max_w = 285, 540
        expected_w = max_w * zone.expected_points / max_points
        actual_w = max_w * zone.actual_points / max_points
        ax.add_patch(FancyBboxPatch((x0, y - 17), max_w, 34, boxstyle="round,pad=0,rounding_size=6", facecolor=TRACK, edgecolor="none"))
        ax.add_patch(FancyBboxPatch((x0, y - 17), actual_w, 34, boxstyle="round,pad=0,rounding_size=6", facecolor=RED if zone.delta >= 0 else DEFAULT_THEME.contrast, edgecolor="none"))
        ax.plot([x0 + expected_w, x0 + expected_w], [y - 26, y + 26], color=RED, lw=2.2)
        ax.text(845, y + 15, f"{zone.actual_points:.0f} ACTUAL", ha="left", va="center", fontsize=10, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        ax.text(845, y - 15, f"{zone.expected_points:.1f} EXPECTED", ha="left", va="center", fontsize=8.2, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))
        ax.text(1010, y, f"{zone.delta:+.1f}", ha="right", va="center", fontsize=14, color=RED if zone.delta >= 0 else DEFAULT_THEME.ink, fontproperties=body_font("bold"))

    ax.text(285, 193, "BAR = ACTUAL POINTS", ha="left", va="center", fontsize=8, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))
    ax.plot([476, 476], [181, 205], color=RED, lw=2.2)
    ax.text(488, 193, "MARKER = EXPECTED POINTS", ha="left", va="center", fontsize=8, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))
    _concept_note(ax, "EXPECTED POINTS USE 2025–26 NBA LEAGUE-AVERAGE FG% BY BASIC SHOT ZONE")
    return fig


def render_contributions(rows: tuple[Contribution, ...]):
    fig, ax = _base_slide(
        [("WHO DROVE ", DEFAULT_THEME.ink), ("WHAT?", RED)],
        "Share of team production · minimum 10 minutes",
    )
    columns = (
        ("SCORING", "scoring"),
        ("SHOT LOAD", "shot_load"),
        ("CREATION", "creation"),
        ("REBOUNDING", "rebounding"),
    )
    name_w, cell_w = 250, 180
    x_starts = [60 + name_w + i * cell_w for i in range(4)]
    ax.text(60, 1055, "PLAYER", ha="left", va="center", fontsize=9, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))
    for (label, _), x in zip(columns, x_starts):
        ax.text(x + cell_w / 2, 1055, label, ha="center", va="center", fontsize=8.5, color=DEFAULT_THEME.muted, fontproperties=body_font("bold"))

    leaders = {
        key: max(getattr(row, key) for row in rows)
        for _, key in columns
    }
    row_h = 103
    for index, row in enumerate(rows):
        y = 985 - index * row_h
        if index % 2:
            ax.add_patch(FancyBboxPatch((60, y - 44), 960, 88, boxstyle="round,pad=0,rounding_size=8", facecolor=PALE_RED, edgecolor="none"))
        ax.text(76, y + 12, row.name, ha="left", va="center", fontsize=12, color=DEFAULT_THEME.ink, fontproperties=body_font("bold"))
        ax.text(76, y - 18, f"{row.minutes} MIN", ha="left", va="center", fontsize=8, color=DEFAULT_THEME.muted, fontproperties=body_font("medium"))
        for (_, key), x in zip(columns, x_starts):
            value = getattr(row, key)
            is_leader = abs(value - leaders[key]) < 0.01
            bar_x, bar_y, bar_w = x + 12, y - 9, 112
            ax.add_patch(FancyBboxPatch((bar_x, bar_y), bar_w, 18, boxstyle="round,pad=0,rounding_size=4", facecolor=TRACK, edgecolor="none"))
            if value > 0:
                ax.add_patch(FancyBboxPatch((bar_x, bar_y), bar_w * min(value, 50) / 50, 18, boxstyle="round,pad=0,rounding_size=4", facecolor=RED if is_leader else DEFAULT_THEME.contrast, edgecolor="none"))
            ax.text(x + cell_w - 10, y, f"{value:.0f}%", ha="right", va="center", fontsize=10.5, color=RED if is_leader else DEFAULT_THEME.ink, fontproperties=body_font("bold"))

    ax.add_patch(FancyBboxPatch((60, 130), 960, 95, boxstyle="round,pad=0,rounding_size=12", facecolor=DEFAULT_THEME.contrast, edgecolor="none"))
    ax.text(540, 185, "SCORING LOAD ≠ CREATION LOAD", ha="center", va="center", fontsize=17, color=WHITE, fontproperties=body_font("bold"))
    ax.text(540, 153, "Caleb carried the shots; Kennedy created the assists; Malik led the glass.", ha="center", va="center", fontsize=9.5, color="#E8E2DC", fontproperties=body_font("medium"))
    _concept_note(ax, "SHARES USE TEAM TOTALS · QUALIFICATION: 10+ MINUTES · CONCEPT MOCK")
    return fig


def main():
    final = "--final" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    figures = (
        render_deciders(prepare_factors(CHI, MEM)),
        render_fingerprint(prepare_fingerprint(CHI)),
        render_shot_quality(prepare_quality_zones()),
        render_contributions(prepare_contributions(PLAYERS, CHI)),
    )
    for index, fig in enumerate(figures, start=1):
        path = OUT / f"2026-07-13-regular-season-gamebook-concept-s{index}.png"
        save_post(fig, path, final=final)
        plt.close(fig)
        print(f"Saved {path} at {export_dpi(final)} DPI")


if __name__ == "__main__":
    main()
