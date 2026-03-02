"""Single-image feed post builders."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd

from bulls import analysis
from bulls.config import BULLS_BLACK, BULLS_RED


# Instagram portrait feed post (4:5)
INSTAGRAM_FEED_WIDTH_PX = 1080
INSTAGRAM_FEED_HEIGHT_PX = 1350
DEFAULT_DPI = 150


def _mpl_color(rgb: Sequence[int]) -> tuple:
    """Convert RGB values (0-255) to matplotlib color tuple (0-1)."""
    return tuple(channel / 255 for channel in rgb)


def build_zone_pps_post(
    team_shots: pd.DataFrame,
    title: str = "Bulls Shot Value by Zone",
    subtitle: str = "Points per shot (higher is better)",
    min_shots: int = 20,
) -> plt.Figure:
    """
    Build an Instagram-ready zone PPS post from team shot-level data.

    Args:
        team_shots: DataFrame from bulls.data.get_team_shots()
        title: Main post title
        subtitle: Post subtitle
        min_shots: Minimum shots required for zone inclusion

    Returns:
        Matplotlib Figure sized for Instagram portrait feed post.
    """
    figsize = (INSTAGRAM_FEED_WIDTH_PX / 100, INSTAGRAM_FEED_HEIGHT_PX / 100)
    fig, ax = plt.subplots(figsize=figsize, facecolor="white")

    if team_shots.empty:
        ax.text(0.5, 0.5, "No shot data available", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    pps_stats = analysis.points_per_shot(team_shots, by_zone=True)
    overall_pps = float(pps_stats.get("overall", {}).get("pps", 0.0))
    zone_data = pps_stats.get("by_zone", {})

    rows = []
    for zone, stats in zone_data.items():
        total_shots = int(stats.get("total_shots", 0))
        if total_shots < min_shots:
            continue
        rows.append(
            {
                "zone": zone,
                "pps": float(stats.get("pps", 0.0)),
                "shots": total_shots,
                "fg_pct": float(stats.get("fg_pct", 0.0)),
            }
        )

    if not rows:
        ax.text(
            0.5,
            0.5,
            f"No zones meet min_shots={min_shots}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        return fig

    frame = pd.DataFrame(rows).sort_values("pps", ascending=True).reset_index(drop=True)

    bar_colors = [
        _mpl_color(BULLS_RED) if pps >= overall_pps else _mpl_color(BULLS_BLACK)
        for pps in frame["pps"]
    ]
    bars = ax.barh(frame["zone"], frame["pps"], color=bar_colors, alpha=0.9)

    for bar, pps, shots in zip(bars, frame["pps"], frame["shots"]):
        label = f"{pps:.2f} PPS | {shots} shots"
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=11,
            color="black",
        )

    ax.axvline(overall_pps, color="dimgray", linestyle="--", linewidth=1.5)
    ax.text(
        overall_pps + 0.01,
        0.02,
        f"Overall: {overall_pps:.2f}",
        transform=ax.get_xaxis_transform(),
        fontsize=11,
        color="dimgray",
    )

    ax.set_xlim(0, max(frame["pps"].max() + 0.35, 1.2))
    ax.set_xlabel("Points Per Shot", fontsize=12, fontweight="bold")
    ax.set_ylabel("")
    ax.tick_params(axis="y", labelsize=11)
    ax.tick_params(axis="x", labelsize=10)
    ax.xaxis.grid(True, alpha=0.2)

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    fig.text(0.5, 0.965, title, ha="center", fontsize=28, fontweight="bold", color="black")
    fig.text(0.5, 0.935, subtitle, ha="center", fontsize=14, color="dimgray")
    fig.text(
        0.5,
        0.02,
        "Red bars are above team average PPS",
        ha="center",
        fontsize=11,
        color="dimgray",
    )

    fig.subplots_adjust(left=0.22, right=0.94, top=0.88, bottom=0.08)
    return fig


def save_feed_post(fig: plt.Figure, output_path: str, dpi: int = DEFAULT_DPI) -> Path:
    """
    Save a feed post figure to disk.

    Args:
        fig: Figure from a graphics builder
        output_path: Destination image path (e.g., output/feed/post.png)
        dpi: Export DPI

    Returns:
        Path to written image file.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, facecolor=fig.get_facecolor())
    return output
