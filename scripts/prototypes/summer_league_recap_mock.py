"""Rough visual mock for a player-led Bulls Summer League game recap.

Uses the Bulls' 114-105 Summer League win over Indiana on July 14, 2025 so
every number in the draft is real. This is a layout probe, not yet tomorrow's
live-data workflow.
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from bulls.graphics.feed import (
    DEFAULT_DPI,
    INSTAGRAM_FEED_HEIGHT_PX as H,
    INSTAGRAM_FEED_WIDTH_PX as W,
    _fp_body,
    _fp_title,
    save_feed_post,
)

INK = "#1A1A1A"
MUTED = "#777777"
FAINT = "#AAAAAA"
RED = "#CE1141"
RULE = "#DDDDDD"
PALE_RED = "#F7E8ED"

OUT = _REPO / "output" / "feed"
DISPLAY_FONT = _REPO / "assets" / "fonts" / "AcademicM54.ttf"

GAME = {
    "bulls_score": 114,
    "opponent": "PACERS",
    "opponent_score": 105,
    "date": "JUL 14, 2025",
    "team_stats": [
        ("37-74", "FG"),
        ("10-26", "3PT"),
        ("32", "REB"),
        ("19", "TO"),
    ],
    "players": [
        {
            "name": "MATAS BUZELIS",
            "points": 28,
            "line": "8-14 FG   ·   2-4 3PT   ·   10-13 FT",
            "impact": "5 REB   ·   1 AST",
        },
        {
            "name": "NOA ESSENGUE",
            "points": 21,
            "line": "7-14 FG   ·   3-8 3PT   ·   4-4 FT",
            "impact": "3 REB   ·   1 AST",
        },
        {
            "name": "JAVON FREEMAN-LIBERTY",
            "points": 18,
            "line": "6-14 FG   ·   2-4 3PT   ·   4-4 FT",
            "impact": "8 REB   ·   5 AST",
        },
    ],
}


def _fp_display():
    return fm.FontProperties(fname=str(DISPLAY_FONT))


def _data_width(ax, text_obj):
    """Rendered width of a text artist in the canvas' pixel coordinates."""
    ax.figure.canvas.draw()
    bbox = text_obj.get_window_extent()
    inverse = ax.transData.inverted()
    x0, _ = inverse.transform((bbox.x0, bbox.y0))
    x1, _ = inverse.transform((bbox.x1, bbox.y0))
    return x1 - x0


def _draw_title(ax, segments):
    """Fit a two-color Academic M54 title inside the standard margins."""
    x, y, max_width, base_size = 60, H - 66, W - 120, 86
    full_text = "".join(text for text, _ in segments)
    probe = ax.text(
        x, y, full_text, ha="left", va="top", fontsize=base_size,
        fontproperties=_fp_display(), alpha=0,
    )
    size = base_size * max_width / _data_width(ax, probe)
    probe.remove()
    for text, color in segments:
        item = ax.text(
            x, y, text, ha="left", va="top", fontsize=size, color=color,
            fontproperties=_fp_display(),
        )
        x += _data_width(ax, item)


def _draw_subtitle(ax, parts, y):
    """Draw a muted subtitle separated by the design system's vertical ticks."""
    x = 60
    for index, part in enumerate(parts):
        label = ax.text(
            x,
            y,
            part,
            ha="left",
            va="top",
            fontsize=18,
            color=MUTED,
            fontproperties=_fp_body(weight="medium"),
        )
        x += _data_width(ax, label)
        if index < len(parts) - 1:
            x += 13
            ax.plot([x, x], [y - 21, y - 5], color="#CFCFCF", lw=1.3)
            x += 13


def _canvas():
    fig = plt.figure(
        figsize=(W / DEFAULT_DPI, H / DEFAULT_DPI), facecolor="#FFFFFF"
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax


def _team_snapshot(ax):
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
    ax.text(
        84,
        y_top - 27,
        "TEAM SNAPSHOT",
        ha="left",
        va="top",
        fontsize=11,
        color=RED,
        fontproperties=_fp_body(weight="bold"),
    )
    stat_width = (W - 168) / len(GAME["team_stats"])
    for index, (value, label) in enumerate(GAME["team_stats"]):
        x = 84 + stat_width * index
        if index:
            ax.plot([x - 18, x - 18], [y_bottom + 22, y_top - 56], color="#E6C4CF", lw=1)
        ax.text(
            x,
            y_top - 75,
            value,
            ha="left",
            va="top",
            fontsize=29,
            color=INK,
            fontproperties=_fp_body(weight="bold"),
        )
        ax.text(
            x,
            y_top - 125,
            label,
            ha="left",
            va="top",
            fontsize=11,
            color=MUTED,
            fontproperties=_fp_body(weight="bold"),
        )


def _player_row(ax, player, y_top, first=False):
    row_height = 173
    y_center = y_top - row_height / 2
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
    ax.text(
        126,
        y_center + 17,
        str(player["points"]),
        ha="center",
        va="center",
        fontsize=40,
        color="#FFFFFF",
        fontproperties=_fp_body(weight="bold"),
    )
    ax.text(
        126,
        y_center - 22,
        "PTS",
        ha="center",
        va="center",
        fontsize=10,
        color="#FFFFFF",
        fontproperties=_fp_body(weight="bold"),
    )
    ax.text(
        224,
        y_center + 32,
        player["name"],
        ha="left",
        va="center",
            fontsize=22,
            color=INK,
            fontproperties=_fp_body(weight="bold"),
    )
    ax.text(
        224,
        y_center - 6,
        player["line"],
        ha="left",
        va="center",
        fontsize=14,
        color=MUTED,
        fontproperties=_fp_body(weight="medium"),
    )
    ax.text(
        224,
        y_center - 35,
        player["impact"],
        ha="left",
        va="center",
        fontsize=13,
        color=INK,
        fontproperties=_fp_body(weight="bold"),
    )


def build():
    fig, ax = _canvas()
    _draw_title(ax, [("SUMMER LEAGUE ", INK), ("REPORT", RED)])
    _draw_subtitle(
        ax,
        [f"Bulls {GAME['bulls_score']}", f"{GAME['opponent'].title()} {GAME['opponent_score']}", GAME["date"]],
        H - 168,
    )
    ax.text(
        60,
        H - 206,
        "Three Bulls who drove the win in Las Vegas",
        ha="left",
        va="top",
        fontsize=14,
        color=RED,
        style="italic",
        fontproperties=_fp_body(weight="medium"),
    )

    _team_snapshot(ax)
    ax.text(
        60,
        843,
        "PLAYER SPOTLIGHT",
        ha="left",
        va="top",
        fontsize=12,
        color=MUTED,
        fontproperties=_fp_body(weight="bold"),
    )
    for index, player in enumerate(GAME["players"]):
        _player_row(ax, player, 795 - index * 173, first=index == 0)

    ax.text(
        60,
        40,
        "2025 Summer League game · Data via NBA.com/Stats",
        ha="left",
        va="bottom",
        fontsize=8.5,
        color=FAINT,
        fontproperties=_fp_body(),
    )
    ax.text(
        1020,
        40,
        "@chicagobullsdata",
        ha="right",
        va="bottom",
        fontsize=10.5,
        color=MUTED,
        fontproperties=_fp_body(weight="medium"),
    )
    return fig


if __name__ == "__main__":
    dpi = 300 if "--final" in sys.argv else DEFAULT_DPI
    fig = build()
    path = save_feed_post(fig, OUT / "2026-07-09-summer-league-recap-mock.png", dpi=dpi)
    plt.close(fig)
    print(path)
