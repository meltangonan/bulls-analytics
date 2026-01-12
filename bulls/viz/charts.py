"""Basic chart functions using matplotlib."""
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional, List
from pathlib import Path

from bulls.config import BULLS_RED, BULLS_BLACK, WHITE, OUTPUT_DIR


def bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    highlight_last: bool = True,
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a bar chart.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis (bar heights)
        title: Chart title
        color: Bar color (RGB tuple)
        highlight_last: Highlight the most recent bar
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=10)
        >>> bar_chart(coby, x='date', y='points', title="Coby's Scoring")
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Reverse data so oldest is first (left to right chronologically)
    plot_data = data.iloc[::-1].copy()
    
    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()
    
    # Color bars
    colors = [tuple(c/255 for c in color)] * len(y_vals)
    if highlight_last and len(colors) > 0:
        colors[-1] = tuple(c/255 for c in BULLS_RED)  # Highlight most recent
    
    ax.bar(x_vals, y_vals, color=colors, edgecolor='black', linewidth=0.5)
    
    # Styling
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_ylabel(y.capitalize())
    
    # X-axis labels
    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        # Shorten date labels if needed
        if 'date' in x.lower():
            labels = [str(l)[5:10] if len(str(l)) > 5 else l for l in labels]
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    # Add average line (only if we have data)
    if len(y_vals) > 0:
        avg = sum(y_vals) / len(y_vals)
        ax.axhline(y=avg, color='gray', linestyle='--', alpha=0.7, label=f'Avg: {avg:.1f}')
        ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig


def line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a line chart showing trend over time.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Line color (RGB tuple)
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Reverse for chronological order
    plot_data = data.iloc[::-1].copy()
    
    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()
    
    ax.plot(x_vals, y_vals, color=tuple(c/255 for c in color), linewidth=2, marker='o')
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_ylabel(y.capitalize())
    
    # X-axis labels
    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        if 'date' in x.lower():
            labels = [str(l)[5:10] if len(str(l)) > 5 else l for l in labels]
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig
