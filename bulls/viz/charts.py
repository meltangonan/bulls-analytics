"""Notebook-first chart helpers for Bulls analytics."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle, Patch, Rectangle

from bulls.config import BULLS_BLACK, BULLS_RED, GREEN, RED as RED_COLOR


def _mpl_color(rgb: Sequence[int]) -> tuple:
    """Convert RGB values (0-255) to matplotlib color tuple (0-1)."""
    return tuple(channel / 255 for channel in rgb)


def _chronological(data: pd.DataFrame) -> pd.DataFrame:
    """Reverse rows so charts read oldest -> newest left to right."""
    if data.empty:
        return data.copy()
    return data.iloc[::-1].reset_index(drop=True)


def _short_date_labels(values: list) -> list:
    labels = []
    for value in values:
        raw = str(value)
        labels.append(raw[5:10] if len(raw) >= 10 else raw)
    return labels


def bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    highlight_last: bool = True,
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Create a bar chart for notebook exploration."""
    fig, ax = plt.subplots(figsize=figsize)
    plot_data = _chronological(data)

    if y not in plot_data.columns:
        ax.text(0.5, 0.5, f"Missing column: {y}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Bar Chart")
        return fig

    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()

    base_color = _mpl_color(color)
    colors = [base_color] * len(y_vals)
    if highlight_last and colors:
        colors[-1] = _mpl_color(BULLS_RED)

    ax.bar(x_vals, y_vals, color=colors, edgecolor="black", linewidth=0.5)

    ax.set_title(title or y.replace("_", " ").title(), fontsize=14, fontweight="bold")
    ax.set_ylabel(y.replace("_", " ").title())

    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        if "date" in x.lower():
            labels = _short_date_labels(labels)
        ax.set_xticks(list(x_vals))
        ax.set_xticklabels(labels, rotation=45, ha="right")

    if y_vals:
        avg = float(np.mean(y_vals))
        ax.axhline(avg, color="gray", linestyle="--", alpha=0.7, label=f"Avg: {avg:.1f}")
        ax.legend(loc="best")

    plt.tight_layout()
    return fig


def line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Create a line chart showing a stat over time."""
    fig, ax = plt.subplots(figsize=figsize)
    plot_data = _chronological(data)

    if y not in plot_data.columns:
        ax.text(0.5, 0.5, f"Missing column: {y}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Line Chart")
        return fig

    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()

    ax.plot(x_vals, y_vals, color=_mpl_color(color), linewidth=2, marker="o")
    ax.set_title(title or y.replace("_", " ").title(), fontsize=14, fontweight="bold")
    ax.set_ylabel(y.replace("_", " ").title())

    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        if "date" in x.lower():
            labels = _short_date_labels(labels)
        ax.set_xticks(list(x_vals))
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.grid(alpha=0.25)
    plt.tight_layout()
    return fig


def scatter_plot(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    size: Optional[int] = None,
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Create a scatter plot comparing two metrics."""
    fig, ax = plt.subplots(figsize=figsize)

    if x not in data.columns or y not in data.columns:
        missing = [col for col in (x, y) if col not in data.columns]
        ax.text(0.5, 0.5, f"Missing column(s): {', '.join(missing)}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Scatter Plot")
        return fig

    x_vals = data[x].tolist()
    y_vals = data[y].tolist()

    if size is None:
        sizes = 80
    elif isinstance(size, str) and size in data.columns:
        sizes = (data[size].clip(lower=1) * 10).tolist()
    else:
        sizes = size

    ax.scatter(
        x_vals,
        y_vals,
        c=[_mpl_color(color)],
        s=sizes,
        alpha=0.7,
        edgecolors="black",
        linewidth=0.5,
    )

    ax.set_title(title or f"{y} vs {x}", fontsize=14, fontweight="bold")
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(y.replace("_", " ").title())
    ax.grid(alpha=0.25)

    plt.tight_layout()
    return fig


def comparison_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    group_by: str,
    title: str = "",
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Create grouped bars for comparing multiple players or groups."""
    fig, ax = plt.subplots(figsize=figsize)

    required = [x, y, group_by]
    missing = [col for col in required if col not in data.columns]
    if missing:
        ax.text(0.5, 0.5, f"Missing column(s): {', '.join(missing)}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Comparison Chart")
        return fig

    groups = data[group_by].dropna().unique().tolist()
    if not groups:
        ax.text(0.5, 0.5, "No group data", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Comparison Chart")
        return fig

    categories = sorted(data[x].dropna().unique().tolist())
    x_positions = np.arange(len(categories))
    width = 0.8 / max(len(groups), 1)

    palette = [BULLS_RED, BULLS_BLACK, GREEN, RED_COLOR]

    for idx, group in enumerate(groups):
        group_rows = data[data[group_by] == group]
        values = []
        for category in categories:
            matching = group_rows[group_rows[x] == category]
            values.append(float(matching[y].iloc[0]) if not matching.empty else 0.0)

        offset = (idx - (len(groups) - 1) / 2) * width
        ax.bar(
            x_positions + offset,
            values,
            width=width,
            label=str(group),
            color=_mpl_color(palette[idx % len(palette)]),
            edgecolor="black",
            linewidth=0.5,
        )

    ax.set_title(title or f"{y.replace('_', ' ').title()} by {group_by}", fontsize=14, fontweight="bold")
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(y.replace("_", " ").title())
    ax.set_xticks(x_positions)
    ax.set_xticklabels(categories, rotation=45, ha="right")
    ax.legend(loc="best")
    ax.grid(alpha=0.25, axis="y")

    plt.tight_layout()
    return fig


def win_loss_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    result_col: str = "result",
    title: str = "",
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """Create a bar chart with win/loss color coding."""
    fig, ax = plt.subplots(figsize=figsize)
    plot_data = _chronological(data)

    if y not in plot_data.columns:
        ax.text(0.5, 0.5, f"Missing column: {y}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Win/Loss Chart")
        return fig

    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()

    colors = []
    for _, row in plot_data.iterrows():
        is_win = str(row.get(result_col, "")).upper() == "W"
        colors.append(_mpl_color(GREEN if is_win else RED_COLOR))

    ax.bar(x_vals, y_vals, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_title(title or y.replace("_", " ").title(), fontsize=14, fontweight="bold")
    ax.set_ylabel(y.replace("_", " ").title())

    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        if "date" in x.lower():
            labels = _short_date_labels(labels)
        ax.set_xticks(list(x_vals))
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.legend(
        handles=[
            Patch(facecolor=_mpl_color(GREEN), label="Win"),
            Patch(facecolor=_mpl_color(RED_COLOR), label="Loss"),
        ],
        loc="best",
    )

    plt.tight_layout()
    return fig


def rolling_efficiency_chart(
    data: pd.DataFrame,
    efficiency_col: str,
    result_col: str = "result",
    title: str = "",
    league_avg: float = 57.0,
    figsize: tuple = (12, 6),
) -> plt.Figure:
    """Plot rolling efficiency with win/loss markers."""
    fig, ax = plt.subplots(figsize=figsize)
    plot_data = _chronological(data)

    if plot_data.empty or efficiency_col not in plot_data.columns:
        ax.text(0.5, 0.5, f"Missing or empty data for {efficiency_col}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Rolling Efficiency")
        return fig

    x_vals = range(len(plot_data))
    y_vals = plot_data[efficiency_col].tolist()

    ax.plot(x_vals, y_vals, color=_mpl_color(BULLS_RED), linewidth=2, label="Efficiency")
    ax.axhline(league_avg, color="gray", linestyle="--", alpha=0.7, label=f"League Avg ({league_avg}%)")

    if result_col in plot_data.columns:
        for i, (_, row) in enumerate(plot_data.iterrows()):
            result = str(row.get(result_col, "")).upper()
            marker = "^" if result == "W" else "v"
            marker_color = GREEN if result == "W" else RED_COLOR
            ax.scatter(
                i,
                y_vals[i],
                marker=marker,
                s=80,
                color=_mpl_color(marker_color),
                edgecolors="black",
                linewidth=0.4,
                zorder=3,
            )

    if "date" in plot_data.columns:
        labels = _short_date_labels(plot_data["date"].tolist())
        ax.set_xticks(list(x_vals))
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(title or efficiency_col.replace("_", " ").title(), fontsize=14, fontweight="bold")
    ax.set_xlabel("Game")
    ax.set_ylabel("Efficiency %")
    ax.grid(alpha=0.25)

    legend = [
        Line2D([0], [0], color=_mpl_color(BULLS_RED), linewidth=2, label="Efficiency"),
        Line2D([0], [0], color="gray", linestyle="--", label=f"League Avg ({league_avg}%)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=_mpl_color(GREEN), markeredgecolor="black", label="Win"),
        Line2D([0], [0], marker="v", color="w", markerfacecolor=_mpl_color(RED_COLOR), markeredgecolor="black", label="Loss"),
    ]
    ax.legend(handles=legend, loc="best")

    plt.tight_layout()
    return fig


def radar_chart(
    players_data: List[dict],
    metrics: Optional[List[str]] = None,
    normalize: bool = True,
    title: str = "",
    figsize: tuple = (8, 8),
) -> plt.Figure:
    """Create a radar chart for one or more players."""
    if metrics is None:
        metrics = ["points", "rebounds", "assists", "steals", "fg_pct"]

    if not players_data:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No player data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    available = [metric for metric in metrics if any(metric in player for player in players_data)]
    if not available:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No metrics available", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    angles = np.linspace(0, 2 * np.pi, len(available), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"polar": True})
    palette = [BULLS_RED, BULLS_BLACK, GREEN, RED_COLOR]

    max_vals = {metric: max(player.get(metric, 0) for player in players_data) or 1 for metric in available}

    for idx, player in enumerate(players_data):
        values = []
        for metric in available:
            value = float(player.get(metric, 0))
            if normalize:
                value = value / max_vals[metric] * 100 if max_vals[metric] else 0
            values.append(value)
        values += values[:1]

        ax.plot(angles, values, linewidth=2, marker="o", color=_mpl_color(palette[idx % len(palette)]), label=player.get("name", f"Player {idx + 1}"))
        ax.fill(angles, values, alpha=0.2, color=_mpl_color(palette[idx % len(palette)]))

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([metric.replace("_", " ").title() for metric in available])

    if normalize:
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])

    ax.set_title(title or "Player Comparison", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15))

    plt.tight_layout()
    return fig


def _draw_court(ax, color: str = "black", lw: float = 1.5):
    """Draw a half-court for shot charts."""
    ax.add_patch(Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False))
    ax.add_patch(Rectangle((-30, -7.5), 60, 0, linewidth=lw, color=color))
    ax.add_patch(Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color, fill=False))
    ax.add_patch(Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color, fill=False))
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=lw, color=color))
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color, linestyle="dashed"))
    ax.add_patch(Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color))
    ax.add_patch(Rectangle((-220, -47.5), 0, 140, linewidth=lw, color=color))
    ax.add_patch(Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color))
    ax.add_patch(Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color))
    ax.add_patch(Arc((0, 422.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color))
    ax.plot([-250, 250], [422.5, 422.5], linewidth=lw, color=color)
    return ax


def shot_chart(
    shots_data: pd.DataFrame,
    show_zones: bool = False,
    title: str = "",
    annotations: Optional[List[Dict]] = None,
    figsize: tuple = (12, 11),
) -> plt.Figure:
    """Create a team or player shot chart on a half-court."""
    fig, ax = plt.subplots(figsize=figsize)
    _draw_court(ax, color="black", lw=1)

    if not shots_data.empty and {"loc_x", "loc_y", "shot_made"}.issubset(shots_data.columns):
        if show_zones:
            hb = ax.hexbin(
                shots_data["loc_x"],
                shots_data["loc_y"],
                C=shots_data["shot_made"].astype(int),
                reduce_C_function=np.mean,
                gridsize=24,
                cmap="RdYlGn",
                mincnt=1,
            )
            colorbar = fig.colorbar(hb, ax=ax)
            colorbar.set_label("FG%")
        else:
            makes = shots_data[shots_data["shot_made"]]
            misses = shots_data[~shots_data["shot_made"]]

            if not misses.empty:
                ax.scatter(misses["loc_x"], misses["loc_y"], c="red", marker="x", s=35, alpha=0.6, label="Miss")
            if not makes.empty:
                ax.scatter(makes["loc_x"], makes["loc_y"], c="green", marker="o", s=35, alpha=0.6, label="Make")
            if not makes.empty or not misses.empty:
                ax.legend(loc="upper right")

    if annotations:
        presets = {
            "top_left": (-195, 380),
            "top_right": (195, 380),
            "bottom_left": (-195, -30),
            "bottom_right": (195, -30),
        }
        for ann in annotations:
            position = ann.get("position", "top_left")
            x, y = presets.get(position, position)
            ax.text(
                x,
                y,
                ann.get("text", ""),
                fontsize=ann.get("fontsize", 12),
                ha="center",
                va="center",
                bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "black", "alpha": 0.9},
            )

    ax.set_xlim(-250, 250)
    ax.set_ylim(-47.5, 422.5)
    ax.set_aspect("equal")
    ax.set_title(title or "Shot Chart", fontsize=14, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    plt.tight_layout()
    return fig


def _get_zone_center(zone_name: str) -> tuple:
    """Approximate zone center coordinates for label placement."""
    centers = {
        "Restricted Area": (0, 5),
        "In The Paint (Non-RA)": (0, 80),
        "Mid-Range": (0, 200),
        "Left Corner 3": (-185, 55),
        "Right Corner 3": (185, 55),
        "Above the Break 3": (0, 300),
        "Backcourt": (0, 395),
    }

    if zone_name in centers:
        return centers[zone_name]

    zone = zone_name.lower()
    if "restricted" in zone:
        return centers["Restricted Area"]
    if "paint" in zone:
        return centers["In The Paint (Non-RA)"]
    if "corner" in zone and "left" in zone:
        return centers["Left Corner 3"]
    if "corner" in zone and "right" in zone:
        return centers["Right Corner 3"]
    if "break" in zone or "above" in zone:
        return centers["Above the Break 3"]
    if "backcourt" in zone:
        return centers["Backcourt"]
    return centers["Mid-Range"]


def zone_leaders_chart(
    zone_leaders_dict: Dict,
    title: str = "Zone Leaders - Points Per Game",
    figsize: tuple = (12, 10),
) -> plt.Figure:
    """Plot zone leaders as labeled callouts directly on the court."""
    fig, ax = plt.subplots(figsize=figsize)
    _draw_court(ax, color="black", lw=1.2)

    if not zone_leaders_dict:
        ax.text(0, 180, "No zone leaders data", ha="center", va="center", fontsize=13)
    else:
        for zone_name, leader in zone_leaders_dict.items():
            x, y = _get_zone_center(zone_name)
            player_name = leader.get("player_name", "Unknown")
            ppg = float(leader.get("ppg", 0))

            ax.text(
                x,
                y,
                f"{player_name}\n{ppg:.1f} PPG",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": "white",
                    "edgecolor": _mpl_color(BULLS_RED),
                    "linewidth": 1.3,
                },
            )
            ax.text(x, y + 48, zone_name, ha="center", va="center", fontsize=8, color="dimgray")

    ax.set_xlim(-250, 250)
    ax.set_ylim(-47.5, 422.5)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

    plt.tight_layout()
    return fig


def efficiency_matrix(
    players_data: List[dict],
    title: str = "Bulls Efficiency Matrix",
    league_avg_ts: float = 57.0,
    league_avg_fga: float = 12.0,
    show_gradient: bool = True,
    show_names: bool = True,
    figsize: tuple = (12, 8),
) -> plt.Figure:
    """Plot TS% vs volume (FGA/G) in a quadrant matrix."""
    fig, ax = plt.subplots(figsize=figsize)

    if not players_data:
        ax.text(0.5, 0.5, "No player data", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title, fontsize=14, fontweight="bold")
        return fig

    df = pd.DataFrame(players_data).copy()
    required = ["ts_pct", "fga_per_game"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        ax.text(0.5, 0.5, f"Missing column(s): {', '.join(missing)}", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title, fontsize=14, fontweight="bold")
        return fig

    x = df["fga_per_game"].astype(float)
    y = df["ts_pct"].astype(float)

    x_margin = max((x.max() - x.min()) * 0.15, 1.0)
    y_margin = max((y.max() - y.min()) * 0.15, 1.0)

    x_min = min(x.min() - x_margin, league_avg_fga - x_margin)
    x_max = max(x.max() + x_margin, league_avg_fga + x_margin)
    y_min = min(y.min() - y_margin, league_avg_ts - y_margin)
    y_max = max(y.max() + y_margin, league_avg_ts + y_margin)

    if show_gradient:
        gradient = np.linspace(0, 1, 256).reshape(-1, 1)
        ax.imshow(
            gradient,
            extent=[x_min, x_max, y_min, y_max],
            origin="lower",
            cmap="RdYlGn",
            alpha=0.12,
            aspect="auto",
            zorder=0,
        )

    ax.scatter(
        x,
        y,
        s=120,
        color=_mpl_color(BULLS_RED),
        edgecolors="black",
        linewidth=0.7,
        zorder=3,
    )

    if show_names and "name" in df.columns:
        for _, row in df.iterrows():
            ax.annotate(
                str(row.get("name", "")),
                (float(row["fga_per_game"]), float(row["ts_pct"])),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=9,
                zorder=4,
            )

    ax.axhline(league_avg_ts, color="gray", linestyle="--", linewidth=1.2)
    ax.axvline(league_avg_fga, color="gray", linestyle="--", linewidth=1.2)

    quadrant_style = {"fontsize": 9, "color": "dimgray", "ha": "center", "va": "center"}
    ax.text((x_min + league_avg_fga) / 2, (league_avg_ts + y_max) / 2, "Efficient\nLow Volume", **quadrant_style)
    ax.text((league_avg_fga + x_max) / 2, (league_avg_ts + y_max) / 2, "Efficient\nHigh Volume", **quadrant_style)
    ax.text((x_min + league_avg_fga) / 2, (y_min + league_avg_ts) / 2, "Inefficient\nLow Volume", **quadrant_style)
    ax.text((league_avg_fga + x_max) / 2, (y_min + league_avg_ts) / 2, "Inefficient\nHigh Volume", **quadrant_style)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel("Field Goal Attempts per Game")
    ax.set_ylabel("True Shooting %")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(alpha=0.2)

    ax.legend(
        handles=[
            Patch(facecolor=_mpl_color(BULLS_RED), edgecolor="black", label="Bulls Players"),
            Line2D([0], [0], color="gray", linestyle="--", label=f"League Avg TS% ({league_avg_ts})"),
            Line2D([0], [0], color="gray", linestyle="--", label=f"League Avg FGA/G ({league_avg_fga})"),
        ],
        loc="best",
    )

    plt.tight_layout()
    return fig
