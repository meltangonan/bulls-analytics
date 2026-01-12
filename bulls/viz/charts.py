"""Basic chart functions using matplotlib."""
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional, List
from pathlib import Path

from bulls.config import BULLS_RED, BULLS_BLACK, WHITE, GREEN, RED as RED_COLOR, OUTPUT_DIR


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


def scatter_plot(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: tuple = BULLS_RED,
    size: Optional[int] = None,
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a scatter plot comparing two metrics.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Point color (RGB tuple)
        size: Point size (optional, can use a column name for variable sizing)
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> coby = get_player_games("Coby White", last_n=15)
        >>> scatter_plot(coby, x='points', y='assists', title="Points vs Assists")
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    x_vals = data[x].tolist()
    y_vals = data[y].tolist()
    
    # Handle size parameter
    if size is None:
        sizes = 100
    elif isinstance(size, str) and size in data.columns:
        sizes = data[size].tolist()
        # Scale sizes for visibility
        sizes = [s * 10 for s in sizes]
    else:
        sizes = size
    
    ax.scatter(x_vals, y_vals, c=[tuple(c/255 for c in color)], s=sizes, alpha=0.6, edgecolors='black', linewidth=0.5)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel(x.capitalize())
    ax.set_ylabel(y.capitalize())
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig


def comparison_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    group_by: str,
    title: str = "",
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a comparison chart showing multiple groups side by side.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis (categories)
        y: Column name for y-axis (values)
        group_by: Column name to group by (creates multiple series)
        title: Chart title
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> # Compare multiple players' scoring
        >>> comparison_chart(data, x='date', y='points', group_by='player_name')
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    groups = data[group_by].unique()
    colors = [BULLS_RED, BULLS_BLACK, GREEN, RED_COLOR]
    
    x_categories = sorted(data[x].unique())
    x_pos = range(len(x_categories))
    
    width = 0.8 / len(groups)
    
    for i, group in enumerate(groups):
        group_data = data[data[group_by] == group]
        values = [group_data[group_data[x] == cat][y].values[0] if len(group_data[group_data[x] == cat]) > 0 else 0 
                 for cat in x_categories]
        
        offset = (i - len(groups)/2 + 0.5) * width
        ax.bar([p + offset for p in x_pos], values, width=width, 
               label=group, color=tuple(c/255 for c in colors[i % len(colors)]), 
               edgecolor='black', linewidth=0.5)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel(x.capitalize())
    ax.set_ylabel(y.capitalize())
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_categories, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig


def win_loss_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    result_col: str = 'result',
    title: str = "",
    save_path: Optional[str] = None,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Create a bar chart with different colors for wins and losses.
    
    Args:
        data: DataFrame with the data
        x: Column name for x-axis
        y: Column name for y-axis (bar heights)
        result_col: Column name containing 'W' or 'L' for win/loss
        title: Chart title
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> games = get_games(last_n=10)
        >>> win_loss_chart(games, x='GAME_DATE', y='PTS', result_col='WL')
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Reverse data so oldest is first
    plot_data = data.iloc[::-1].copy()
    
    x_vals = range(len(plot_data))
    y_vals = plot_data[y].tolist()
    
    # Color bars based on win/loss
    colors = []
    for _, row in plot_data.iterrows():
        if result_col in row and str(row[result_col]).upper() == 'W':
            colors.append(tuple(c/255 for c in GREEN))
        else:
            colors.append(tuple(c/255 for c in RED_COLOR))
    
    ax.bar(x_vals, y_vals, color=colors, edgecolor='black', linewidth=0.5)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_ylabel(y.capitalize())
    
    # X-axis labels
    if x in plot_data.columns:
        labels = plot_data[x].tolist()
        if 'date' in x.lower():
            labels = [str(l)[5:10] if len(str(l)) > 5 else l for l in labels]
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=tuple(c/255 for c in GREEN), label='Win'),
        Patch(facecolor=tuple(c/255 for c in RED_COLOR), label='Loss')
    ]
    ax.legend(handles=legend_elements)
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig
