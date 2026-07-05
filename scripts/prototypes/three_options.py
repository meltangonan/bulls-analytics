"""Three candidate post directions to react to: quadrant, monthly grid, season timeline."""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(Path(__file__).parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bulls.data.fetch import get_player_headshot
from bulls.graphics.feed import (
    DEFAULT_DPI,
    INSTAGRAM_FEED_HEIGHT_PX as H,
    INSTAGRAM_FEED_WIDTH_PX as W,
    _fp_body,
    _fp_title,
    _make_circular_headshot,
    save_feed_post,
)
from impact_board import compute_board, parse_minutes, game_score

INK, MUTED, FAINT, RULE, RED = "#1A1A1A", "#777777", "#AAAAAA", "#DDDDDD", "#CE1141"

CACHE = _REPO / "cache"
OUT = _REPO / "output" / "feed"

for _f in ("box_scores_2025-26.csv", "games_2025-26.csv"):
    if not (CACHE / _f).exists():
        sys.exit(f"Missing cache/{_f} — see scripts/prototypes/README.md to rebuild the season cache.")

box = pd.read_csv(CACHE / "box_scores_2025-26.csv")
games = pd.read_csv(CACHE / "games_2025-26.csv")
board = compute_board(box)  # min 20 GP, sorted by avg Game Score


def canvas(title, subtitle, kicker, title_size=44):
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
    ax.text(60, H - 70, title, ha="left", va="top", fontsize=title_size, color=INK,
            fontproperties=_fp_title(weight="bold"))
    ax.text(60, H - 185, subtitle, ha="left", va="top", fontsize=18, color=MUTED,
            fontproperties=_fp_body(weight="medium"))
    ax.text(60, H - 235, kicker, ha="left", va="top", fontsize=14, color=RED,
            style="italic", fontproperties=_fp_body(weight="medium"))
    ax.text(60, 40, "Data via NBA.com/Stats", ha="left", va="bottom", fontsize=8.5,
            color=FAINT, fontproperties=_fp_body())
    return fig, ax


def headshot_at(ax, player_id, x, y, r):
    p = get_player_headshot(int(player_id))
    if p and Path(p).exists():
        circ = _make_circular_headshot(Path(p))
        if circ is not None:
            ax.imshow(circ, extent=[x - r, x + r, y - r, y + r], zorder=4,
                      interpolation="bilinear")
            return True
    return False


def short_name(name):
    parts = name.split(" ", 1)
    return parts[-1] if len(parts) > 1 else name


# ---------------------------------------------------------------- A. Quadrant
def build_quadrant():
    fig, ax = canvas(
        "Impact vs. Availability",
        "Chicago Bulls | 2025-26 Season",
        "Avg. Game Score vs. Games Played | Min. 20 Games",
    )

    # Plot region in canvas px
    px0, px1, py0, py1 = 130, 1000, 210, 990
    gp_lo, gp_hi = 12, 88
    gs_lo = float(board["gmsc_avg"].min()) - 1.8
    gs_hi = float(board["gmsc_avg"].max()) + 2.2
    x_thr, y_thr = 41, 10.0  # half the season / league-average game

    def X(gp):
        return px0 + (gp - gp_lo) / (gp_hi - gp_lo) * (px1 - px0)

    def Y(gs):
        return py0 + (gs - gs_lo) / (gs_hi - gs_lo) * (py1 - py0)

    ax.add_patch(plt.Rectangle((px0, py0), px1 - px0, py1 - py0,
                               facecolor="#FAFAFA", edgecolor=RULE, lw=1.0, zorder=1))
    ax.plot([X(x_thr), X(x_thr)], [py0, py1], color=FAINT, lw=1.2, ls=(0, (5, 4)), zorder=2)
    ax.plot([px0, px1], [Y(y_thr), Y(y_thr)], color=FAINT, lw=1.2, ls=(0, (5, 4)), zorder=2)

    corners = [
        ("GREAT WHEN AVAILABLE", px0 + 16, py1 - 18, "left"),
        ("CARRIED ALL SEASON", px1 - 16, py1 - 18, "right"),
        ("ON THE FRINGES", px0 + 16, py0 + 30, "left"),
        ("ALWAYS THERE, LIGHTER LIFT", px1 - 16, py0 + 30, "right"),
    ]
    for label, cx, cy, align in corners:
        ax.text(cx, cy, label, ha=align, va="center", fontsize=11.5, color=FAINT,
                fontproperties=_fp_body(weight="bold"), zorder=2)

    ax.text(X(x_thr) + 8, py1 - 46, "41 games = half the season", ha="left",
            va="center", fontsize=9.5, color=MUTED, style="italic",
            fontproperties=_fp_body(), zorder=3)
    ax.text(px1 - 16, Y(y_thr) - 16, "Game Score 10 = league-average game", ha="right",
            va="top", fontsize=9.5, color=MUTED, style="italic",
            fontproperties=_fp_body(), zorder=3)

    # Axis ticks
    for gp in (20, 40, 60, 80):
        ax.text(X(gp), py0 - 20, str(gp), ha="center", va="top", fontsize=10,
                color=MUTED, fontproperties=_fp_body())
    for gs in (5, 10, 15):
        ax.text(px0 - 14, Y(gs), str(gs), ha="right", va="center", fontsize=10,
                color=MUTED, fontproperties=_fp_body())
    ax.text((px0 + px1) / 2, py0 - 52, "GAMES PLAYED", ha="center", va="top",
            fontsize=11, color=MUTED, fontproperties=_fp_body(weight="bold"))
    ax.text(px0 - 58, (py0 + py1) / 2, "AVG. GAME SCORE", ha="center", va="center",
            fontsize=11, color=MUTED, rotation=90, fontproperties=_fp_body(weight="bold"))

    r = 27
    pts = [(X(row["games"]), Y(row["gmsc_avg"]), row) for _, row in board.iterrows()]
    for x, y, row in pts:
        if not headshot_at(ax, row["personId"], x, y, r):
            ax.add_patch(plt.Circle((x, y), r, facecolor=RED, zorder=4))

        cluster = [(ox, oy) for ox, oy, _ in pts
                   if (ox, oy) != (x, y) and abs(ox - x) < 60 and abs(oy - y) < 76]
        label = short_name(row["name"])
        kw = dict(fontsize=9.5, color=INK, zorder=5,
                  fontproperties=_fp_body(weight="bold"))
        if cluster and all(ox >= x for ox, _ in cluster):
            ax.text(x - r - 7, y, label, ha="right", va="center", **kw)
        elif cluster and all(ox <= x for ox, _ in cluster):
            ax.text(x + r + 7, y, label, ha="left", va="center", **kw)
        elif any(-8 < y - oy < 76 for _, oy in cluster):
            ax.text(x, y + r + 5, label, ha="center", va="bottom", **kw)
        else:
            ax.text(x, y - r - 5, label, ha="center", va="top", **kw)

    return fig


# ------------------------------------------------------- B. Month-by-month grid
def build_month_grid():
    fig, ax = canvas(
        "The Season, Month by Month",
        "Chicago Bulls | 2025-26 Season",
        "Avg. Game Score per month | Top 10 by season impact",
        title_size=36,
    )

    b = box.copy()
    b["min_played"] = b["minutes"].map(parse_minutes)
    b = b[b["min_played"] > 0].copy()
    b["gmsc"] = b.apply(game_score, axis=1)
    b["game_id"] = b["game_id"].astype(str).str.zfill(10)

    g = games.copy()
    g["GAME_ID"] = g["GAME_ID"].astype(str).str.zfill(10)
    b = b.merge(g[["GAME_ID", "GAME_DATE"]], left_on="game_id", right_on="GAME_ID")
    b["month"] = b["GAME_DATE"].str[:7]

    months = sorted(b["month"].unique())
    month_labels = [pd.Timestamp(m + "-01").strftime("%b").upper() for m in months]

    top = board.head(10)
    monthly = b.groupby(["personId", "month"])["gmsc"].mean().unstack()

    grid_x0, grid_x1 = 300, 1030
    grid_top, row_h = H - 330, 88
    cell_w = (grid_x1 - grid_x0) / len(months)
    vmax = float(np.nanmax(monthly.loc[top["personId"]].values))

    for j, lab in enumerate(month_labels):
        ax.text(grid_x0 + (j + 0.5) * cell_w, grid_top + 24, lab, ha="center",
                va="center", fontsize=11, color=MUTED,
                fontproperties=_fp_body(weight="bold"))

    red_rgb = np.array([206, 17, 65]) / 255

    for i, (_, row) in enumerate(top.iterrows()):
        cy = grid_top - i * row_h - row_h / 2
        headshot_at(ax, row["personId"], 95, cy, 28)
        name = short_name(row["name"])
        ax.text(140, cy, name, ha="left", va="center", fontsize=13, color=INK,
                fontproperties=_fp_body(weight="bold"))

        vals = monthly.loc[row["personId"]] if row["personId"] in monthly.index else None
        for j, m in enumerate(months):
            cx0 = grid_x0 + j * cell_w
            val = vals[m] if vals is not None and m in vals.index else np.nan
            if np.isnan(val):
                ax.add_patch(plt.Rectangle((cx0 + 3, cy - row_h / 2 + 3), cell_w - 6,
                                           row_h - 6, facecolor="#F2F2F2",
                                           edgecolor="none"))
                ax.text(cx0 + cell_w / 2, cy, "—", ha="center", va="center",
                        fontsize=11, color="#CCCCCC", fontproperties=_fp_body())
            else:
                t = max(0.0, min(1.0, val / vmax))
                color = tuple(1 - (1 - red_rgb) * t)
                ax.add_patch(plt.Rectangle((cx0 + 3, cy - row_h / 2 + 3), cell_w - 6,
                                           row_h - 6, facecolor=color, edgecolor="none"))
                txt_color = "#FFFFFF" if t > 0.55 else INK
                ax.text(cx0 + cell_w / 2, cy, f"{val:.1f}", ha="center", va="center",
                        fontsize=12.5, color=txt_color,
                        fontproperties=_fp_body(weight="bold"))

    ax.text(60, 62, "— = no games that month (trade, injury, or not yet a Bull). "
            "Darker red = better month.",
            ha="left", va="bottom", fontsize=8.5, color=FAINT, fontproperties=_fp_body())
    return fig


# ------------------------------------------------------------ C. Season timeline
def build_timeline():
    g = games.sort_values("GAME_DATE").reset_index(drop=True)
    g["roll"] = g["PLUS_MINUS"].rolling(10).mean()
    wins, losses = int((g["WL"] == "W").sum()), int((g["WL"] == "L").sum())

    fig, ax = canvas(
        "The Shape of the Season",
        f"Chicago Bulls | 2025-26 Season | Finished {wins}-{losses}",
        "Rolling 10-game average point differential",
    )

    px0, px1, py0, py1 = 110, 1020, 260, 1000
    n = len(g)
    lo = float(np.floor(g["roll"].min())) - 2
    hi = float(np.ceil(g["roll"].max())) + 4

    def X(i):
        return px0 + i / (n - 1) * (px1 - px0)

    def Y(v):
        return py0 + (v - lo) / (hi - lo) * (py1 - py0)

    # Month ticks at first game of each month
    g["month"] = g["GAME_DATE"].str[:7]
    for m, idx in g.groupby("month").apply(lambda d: d.index.min()).items():
        lab = pd.Timestamp(m + "-01").strftime("%b").upper()
        ax.text(X(idx), py0 - 20, lab, ha="left", va="top", fontsize=10, color=MUTED,
                fontproperties=_fp_body(weight="bold"))
        ax.plot([X(idx), X(idx)], [py0, py1], color="#F0F0F0", lw=1.0, zorder=1)

    for v in [v for v in range(-20, 15, 5) if v != 0 and lo < v < hi]:
        ax.plot([px0, px1], [Y(v), Y(v)], color="#F0F0F0", lw=1.0, zorder=1)
        ax.text(px0 - 12, Y(v), f"{v:+d}", ha="right", va="center", fontsize=10,
                color=MUTED, fontproperties=_fp_body())
    ax.plot([px0, px1], [Y(0), Y(0)], color=MUTED, lw=1.3, zorder=2)
    ax.text(px0 - 12, Y(0), "0", ha="right", va="center", fontsize=10, color=MUTED,
            fontproperties=_fp_body())

    xs = [X(i) for i in range(n)]
    ys = [Y(v) if not np.isnan(v) else np.nan for v in g["roll"]]
    valid = ~g["roll"].isna()
    xv = np.array(xs)[valid]
    yv = np.array(g["roll"][valid])

    ax.fill_between(xv, Y(0), [Y(v) for v in np.clip(yv, 0, None)],
                    color=RED, alpha=0.85, zorder=3)
    ax.fill_between(xv, Y(0), [Y(v) for v in np.clip(yv, None, 0)],
                    color="#2A2A2A", alpha=0.75, zorder=3)
    ax.plot(xv, [Y(v) for v in yv], color=INK, lw=1.6, zorder=4)

    # Data-derived annotations: best and worst 10-game stretch
    i_best = int(g["roll"].idxmax())
    i_worst = int(g["roll"].idxmin())
    best_v, worst_v = g["roll"].iloc[i_best], g["roll"].iloc[i_worst]

    ax.annotate(f"Best stretch: {best_v:+.1f}\nover 10 games",
                xy=(X(i_best), Y(best_v)), xytext=(X(i_best) - 40, Y(best_v) + 120),
                ha="center", fontsize=11, color=INK,
                fontproperties=_fp_body(weight="bold"),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1.0), zorder=6)
    ax.annotate(f"Worst stretch: {worst_v:+.1f}",
                xy=(X(i_worst), Y(worst_v)), xytext=(X(i_worst) - 150, Y(worst_v) - 4),
                ha="right", fontsize=11, color=INK,
                fontproperties=_fp_body(weight="bold"),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1.0), zorder=6)

    ax.text(60, 62, "Each point averages the previous 10 games. Red = outscoring "
            "opponents, black = outscored.",
            ha="left", va="bottom", fontsize=8.5, color=FAINT, fontproperties=_fp_body())
    return fig


for fn, name in ((build_quadrant, "2026-07-04-option-a-impact-availability-quadrant.png"),
                 (build_month_grid, "2026-07-04-option-b-month-by-month-grid.png"),
                 (build_timeline, "2026-07-04-option-c-season-shape-timeline.png")):
    fig = fn()
    save_feed_post(fig, OUT / name)
    plt.close(fig)
    print("Saved", name)
