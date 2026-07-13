"""Mock post with fake data — a runnable preview of the full house style.

Renders every shared element of a real feed post (jersey stripe, fitted
title, tick subtitle, kicker, leaderboard rows with placeholder headshots,
gradient stat bars, threshold footer, watermark) using an invented roster,
so design changes can be judged on an actual 1080x1350 graphic instead of
only in design-system.html.

Outputs two drafts to output/feed/:
  mock-post-demo.png        house default (jersey canvas, outlined title)
  mock-post-demo-plain.png  plain-title comparison (outlined=False)

Pass --theme <name> (a house.THEMES key) to preview another canvas theme;
non-default outputs are suffixed with the theme name.
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")

from bulls.graphics.craft import gradient_bar, stacked_label
from bulls.graphics.house import (
    CANVAS_WIDTH as W,
    DEFAULT_THEME,
    body_font,
    draw_footer,
    draw_header,
    get_theme,
    new_canvas,
    save_post,
)
from bulls.graphics.craft import headshot_label

OUT = _REPO / "output" / "feed"

# Fictional roster — placeholder data only, never post.
PLAYERS = [
    ("Modest Boosalis", "G · 34 games", 24.6),
    ("Alice Windham", "F · 38 games", 21.9),
    ("Sam Okafor", "C · 31 games", 18.4),
    ("Lou Bricknell", "G · 40 games", 15.2),
    ("Dee Faultman", "F · 27 games", 12.8),
]


def build(outlined: bool, theme_name: str | None = None) -> Path:
    theme = get_theme(theme_name)
    fig, ax = new_canvas(theme)
    draw_header(
        ax,
        [("Who Carries the ", theme.ink), ("Offense", theme.accent)],
        ["Mock Bulls", "2025-26 Season", "Fake data"],
        kicker="Points per game, fictional roster — layout demo only",
        outlined=outlined,
        theme=theme,
    )

    # Leaderboard: headshot disc + stacked name label + gradient PPG bar.
    # Bar length leaves ~90 px for the value label inside the right margin.
    top_y, row_gap = 980, 185
    bar_x0 = 480
    bar_len = W - 60 - bar_x0 - 90
    vmax = max(ppg for _, _, ppg in PLAYERS)
    for i, (name, context, ppg) in enumerate(PLAYERS):
        y = top_y - i * row_gap
        ax.plot([60, W - 60], [y - row_gap / 2] * 2, color=theme.grid, lw=1, zorder=1)
        headshot_label(ax, None, 105, y, radius=44)
        stacked_label(
            ax, 175, y, name, context, gap=16, primary_size=17, secondary_size=12,
            primary_color=theme.ink, secondary_color=theme.muted,
        )
        gradient_bar(ax, y, ppg, vmin=0, vmax=vmax, x0=bar_x0, length=bar_len, height=34)
        ax.text(
            bar_x0 + (ppg / vmax) * bar_len + 14, y, f"{ppg:.1f}",
            ha="left", va="center", fontsize=16, color=theme.ink,
            fontproperties=body_font("bold"),
        )
    ax.text(
        bar_x0, top_y + 72, "PPG",
        ha="left", va="center", fontsize=11, color=theme.muted,
        fontproperties=body_font("medium"),
    )

    # Stat-board footer variant: one line joining threshold + coverage + source.
    draw_footer(
        ax, source="Min. 25 games | fictional demo data | not a real post", theme=theme
    )

    theme_suffix = "" if theme is DEFAULT_THEME else f"-{theme.name}"
    suffix = "" if outlined else "-plain"
    path = OUT / f"mock-post-demo{theme_suffix}{suffix}.png"
    save_post(fig, path, final="--final" in sys.argv)
    return path


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    theme_name = (
        sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else None
    )
    for outlined in (True, False):
        print("wrote", build(outlined, theme_name))
