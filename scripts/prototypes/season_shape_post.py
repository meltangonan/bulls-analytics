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
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bulls.analysis import cumulative_record_delta
from bulls.graphics.feed import (
    DEFAULT_DPI,
    INSTAGRAM_FEED_HEIGHT_PX as H,
    INSTAGRAM_FEED_WIDTH_PX as W,
    _make_circular_headshot,
    save_feed_post,
)

# Body/support face: Archivo (grotesque) — pairs with the collegiate slab title with
# more structure than DM Sans. matplotlib ignores the `weight` kwarg for a single font
# file, so we instanced static weights and select the file explicitly.
_BODY_FONTS = {
    "regular": _REPO / "assets" / "fonts" / "Archivo-400.ttf",
    "medium": _REPO / "assets" / "fonts" / "Archivo-500.ttf",
    "bold": _REPO / "assets" / "fonts" / "Archivo-600.ttf",
}


def _fp_body(weight="regular"):
    return fm.FontProperties(fname=str(_BODY_FONTS.get(weight, _BODY_FONTS["regular"])))

INK, MUTED, FAINT, RED = "#1A1A1A", "#777777", "#AAAAAA", "#CE1141"
BULLS_BLACK = "#141414"  # rich near-black for the under-.500 plunge (Bulls red + black)

_DISPLAY_FONT = _REPO / "assets" / "fonts" / "AcademicM54.ttf"


def _fp_display():
    """Academic M54 — collegiate/varsity slab display face for the headline.
    NOTE: free for NON-COMMERCIAL use only (by justme54s). If this account ever
    goes commercial, license it or swap back to Bevan.ttf (OFL, drop-in)."""
    return fm.FontProperties(fname=str(_DISPLAY_FONT))


def _data_width(ax, text_obj):
    """Rendered width of a text artist, in data (px) units."""
    ax.figure.canvas.draw()
    bb = text_obj.get_window_extent()
    inv = ax.transData.inverted()
    x0, _ = inv.transform((bb.x0, bb.y0))
    x1, _ = inv.transform((bb.x1, bb.y0))
    return x1 - x0

CACHE = _REPO / "cache"
OUT = _REPO / "output" / "feed"
CALEB_IMG = _REPO / "assets" / "img" / "caleb-wilson-draft.png"

games = pd.read_csv(CACHE / "games_2025-26.csv")


def _draw_fitted_title(ax, segments, x0, y, maxw, base=90):
    """Draw a multi-color headline in Anton, auto-scaled to fill `maxw` exactly
    (so left/right margins stay balanced regardless of the string)."""
    fp = _fp_display()
    probe = ax.text(x0, y, "".join(s for s, _ in segments), ha="left", va="top",
                    fontsize=base, fontproperties=fp, alpha=0)
    size = base * maxw / _data_width(ax, probe)
    probe.remove()
    x = x0
    for seg, color in segments:
        t = ax.text(x, y, seg, ha="left", va="top", fontsize=size, color=color,
                    fontproperties=fp)
        x += _data_width(ax, t)


def canvas(title_segments, subtitle_parts, kicker):
    fig = plt.figure(figsize=(W / DEFAULT_DPI, H / DEFAULT_DPI), facecolor="#FFFFFF")
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    _draw_fitted_title(ax, title_segments, 60, H - 66, maxw=W - 120)

    # Subtitle: quiet muted dek, tucked close under the title, thin light separators
    x = 60
    for i, text in enumerate(subtitle_parts):
        t = ax.text(x, H - 168, text, ha="left", va="top", fontsize=18, color=MUTED,
                    fontproperties=_fp_body(weight="medium"))
        x += _data_width(ax, t)
        if i < len(subtitle_parts) - 1:
            sep_x = x + 13
            ax.plot([sep_x, sep_x], [H - 189, H - 173], color="#CFCFCF", lw=1.3, zorder=6)
            x += 26

    ax.text(60, H - 206, kicker, ha="left", va="top", fontsize=14, color=RED,
            style="italic", fontproperties=_fp_body(weight="medium"))
    ax.text(60, 40, "Data via NBA.com/Stats", ha="left", va="bottom", fontsize=8.5,
            color=FAINT, fontproperties=_fp_body())
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
                fontproperties=_fp_body(weight="bold"))
        ax.plot([X(idx), X(idx)], [py0, py1], color="#F0F0F0", lw=1.0, zorder=1)

    # Horizontal ticks
    tick_start = int(np.ceil(lo / 5) * 5)
    tick_end = int(np.floor(hi / 5) * 5)
    for v in [v for v in range(tick_start, tick_end + 1, 5) if v != 0 and lo < v < hi]:
        ax.plot([px0, px1], [Y(v), Y(v)], color="#F0F0F0", lw=1.0, zorder=1)
        ax.text(px0 - 12, Y(v), f"{v:+d}", ha="right", va="center", fontsize=10,
                color=MUTED, fontproperties=_fp_body())
    ax.plot([px0, px1], [Y(0), Y(0)], color=MUTED, lw=1.3, zorder=2)
    ax.text(px0 - 12, Y(0), ".500", ha="right", va="center", fontsize=10, color=MUTED,
            fontproperties=_fp_body())

    # Area fill + line
    x_path = np.array([X(i) for i in range(n + 1)])
    y_path = np.concatenate(([0], g[metric].to_numpy()))
    ax.fill_between(x_path, Y(0), Y(np.clip(y_path, 0, None)), color=RED, alpha=0.92, zorder=3)
    ax.fill_between(x_path, Y(0), Y(np.clip(y_path, None, 0)), color=BULLS_BLACK, alpha=0.92, zorder=3)
    ax.plot(x_path, Y(y_path), color=INK, lw=1.8, zorder=4)

    def callout(text, i_game, xytext, ha="left"):
        v = g[metric].iloc[i_game]
        ax.annotate(text, xy=(X(i_game + 1), Y(v)), xytext=xytext, ha=ha, fontsize=11,
                    color=INK, fontproperties=_fp_body(weight="bold"),
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
            color=MUTED, fontproperties=_fp_body(weight="bold"), zorder=6)
    ax.text(x_dl - 8, py1 - 26, "Feb 5", ha="right", va="top", fontsize=9,
            color=MUTED, fontproperties=_fp_body(weight="medium"), zorder=6)
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

    # Watermark — bottom right, quiet, survives reposts/screenshots off-platform
    ax.text(1020, 40, "@chicagobullsdata", ha="right", va="bottom", fontsize=10.5,
            color=MUTED, fontproperties=_fp_body(weight="medium"), zorder=8)

    return fig


if __name__ == "__main__":
    dpi = 300 if "--final" in sys.argv else DEFAULT_DPI
    fig = build()
    name = "2026-07-09-season-shape.png"
    save_feed_post(fig, OUT / name, dpi=dpi)
    plt.close(fig)
    print(f"Saved {name} at {dpi} DPI")
