"""The Shape of the Season — shipped debut post.

Cumulative games over/under .500 for 2025-26, fan-voice annotations, the Feb 5
trade-deadline line, and the payoff: Caleb Wilson (No. 4 pick) at the endpoint.
Grew out of build_record_timeline in three_options.py; promoted to its own file
because it's the post we're actually shipping.
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bulls.analysis import cumulative_record_delta
from bulls.graphics.feed import (
    _make_circular_headshot,
)
from bulls.graphics.house import (
    BULLS_BLACK,
    CANVAS_HEIGHT as H,
    CANVAS_WIDTH as W,
    GRIDLINE,
    INK,
    MUTED,
    RED,
    body_font,
    draw_footer,
    draw_header,
    export_dpi,
    new_canvas,
    save_post,
)

CACHE = _REPO / "cache"
OUT = _REPO / "output" / "feed"
CALEB_IMG = _REPO / "assets" / "img" / "caleb-wilson-draft.png"

games = pd.read_csv(CACHE / "games_2025-26.csv")


def canvas(title_segments, subtitle_parts, kicker):
    fig, ax = new_canvas()
    draw_header(ax, title_segments, subtitle_parts, kicker=kicker)
    draw_footer(ax)
    return fig, ax


def build():
    g = games.sort_values("GAME_DATE").reset_index(drop=True)
    g = cumulative_record_delta(g)
    wins, losses = int((g["WL"] == "W").sum()), int((g["WL"] == "L").sum())

    fig, ax = canvas(
        [("THE SHAPE OF THE ", INK), ("SEASON", RED)],
        ["Chicago Bulls", "2025-26 Season", f"{wins}-{losses}"],
        "Games over/under .500 through each game",
    )

    px0, px1, py0, py1 = 110, 1020, 260, 1000
    n = len(g)
    metric = "games_over_500"
    lo = float(np.floor(g[metric].min() / 5) * 5) - 5
    hi = float(np.ceil(g[metric].max() / 5) * 5) + 5

    def X(i):
        return px0 + i / n * (px1 - px0)

    def Y(v):
        return py0 + (v - lo) / (hi - lo) * (py1 - py0)

    # Month gridlines
    g["month"] = g["GAME_DATE"].str[:7]
    for m, idx in g.groupby("month").apply(lambda d: d.index.min()).items():
        lab = pd.Timestamp(m + "-01").strftime("%b").upper()
        ax.text(X(idx), py0 - 20, lab, ha="left", va="top", fontsize=10, color=MUTED,
                fontproperties=body_font("bold"))
        ax.plot([X(idx), X(idx)], [py0, py1], color=GRIDLINE, lw=1.0, zorder=1)

    # Horizontal ticks
    tick_start = int(np.ceil(lo / 5) * 5)
    tick_end = int(np.floor(hi / 5) * 5)
    for v in [v for v in range(tick_start, tick_end + 1, 5) if v != 0 and lo < v < hi]:
        ax.plot([px0, px1], [Y(v), Y(v)], color=GRIDLINE, lw=1.0, zorder=1)
        ax.text(px0 - 12, Y(v), f"{v:+d}", ha="right", va="center", fontsize=10,
                color=MUTED, fontproperties=body_font())
    ax.plot([px0, px1], [Y(0), Y(0)], color=MUTED, lw=1.3, zorder=2)
    ax.text(px0 - 12, Y(0), ".500", ha="right", va="center", fontsize=10, color=MUTED,
            fontproperties=body_font())

    # Area fill + line
    x_path = np.array([X(i) for i in range(n + 1)])
    y_path = np.concatenate(([0], g[metric].to_numpy()))
    ax.fill_between(x_path, Y(0), Y(np.clip(y_path, 0, None)), color=RED, alpha=0.92, zorder=3)
    ax.fill_between(x_path, Y(0), Y(np.clip(y_path, None, 0)), color=BULLS_BLACK, alpha=0.92, zorder=3)
    ax.plot(x_path, Y(y_path), color=INK, lw=1.8, zorder=4)

    def callout(text, i_game, xytext, ha="left"):
        v = g[metric].iloc[i_game]
        ax.annotate(text, xy=(X(i_game + 1), Y(v)), xytext=xytext, ha=ha, fontsize=11,
                    color=INK, fontproperties=body_font("bold"),
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=1.0), zorder=6)

    # --- Annotations (fan-in-the-stands voice) ---
    i_best = int(g[metric].idxmax())
    callout("5-0 start,\nwe were so back.", i_best, (X(i_best + 1) + 28, Y(g[metric].iloc[i_best]) + 96))

    dec_i = int(g[g["GAME_DATE"] == "2025-12-26"].index[0])
    callout("5-game Dec. run:\nBack to .500", dec_i, (X(dec_i + 1) - 20, Y(3.4)), ha="center")

    over = g[g[metric] > 0]
    i_last_over = int(over.index.max())
    ts = pd.Timestamp(g["GAME_DATE"].iloc[i_last_over])
    callout(f"Jan {ts.day} —\nlast night above .500.", i_last_over,
            (X(i_last_over + 1) + 84, Y(3) + 24))

    # --- Trade-deadline event line (Feb 5) ---
    i_dl = int(g[g["GAME_DATE"] >= "2026-02-05"].index.min())
    x_dl = X(i_dl + 1)
    ax.plot([x_dl, x_dl], [py0, py1], color=MUTED, lw=1.2, ls=(0, (4, 3)), zorder=2)
    ax.text(x_dl - 8, py1 - 2, "TRADE DEADLINE", ha="right", va="top", fontsize=9,
            color=MUTED, fontproperties=body_font("bold"), zorder=6)
    ax.text(x_dl - 8, py1 - 26, "Feb 5", ha="right", va="top", fontsize=9,
            color=MUTED, fontproperties=body_font("medium"), zorder=6)
    callout("Tank for Caleb begins.\n11 losses in a row.", i_dl,
            (x_dl - 30, Y(-16)), ha="right")

    # --- Endpoint + the payoff: Caleb Wilson ---
    i_final = n - 1
    final_v = g[metric].iloc[i_final]
    callout(f"Finished: {final_v:+.0f}", i_final, (X(i_final + 1) - 150, Y(final_v) + 42), ha="right")

    # The payoff — Caleb Wilson's face, unlabeled, tucked in the white space below
    # the crash (inside the plot so it no longer covers the month axis).
    circ = _make_circular_headshot(CALEB_IMG, border_color=(206, 17, 65), border_frac=0.045)
    r = 50
    cx, cy = X(i_final + 1) - r, 312  # right edge aligned to the final point; low enough to clear the line
    if circ is not None:
        ax.imshow(circ, extent=[cx - r, cx + r, cy - r, cy + r], zorder=7, interpolation="bilinear")

    return fig


if __name__ == "__main__":
    final = "--final" in sys.argv
    dpi = export_dpi(final)
    fig = build()
    name = "2026-07-09-season-shape.png"
    save_post(fig, OUT / name, final=final)
    plt.close(fig)
    print(f"Saved {name} at {dpi} DPI")
