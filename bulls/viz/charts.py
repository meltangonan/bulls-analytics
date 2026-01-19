"""Basic chart functions using matplotlib."""
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc, Patch
import numpy as np
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


def rolling_efficiency_chart(
    data: pd.DataFrame,
    efficiency_col: str,
    result_col: str = 'result',
    title: str = "",
    league_avg: float = 57.0,
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6)
) -> plt.Figure:
    """
    Create a line chart of rolling efficiency with win/loss markers.

    Args:
        data: DataFrame with efficiency and result data
        efficiency_col: Column name for efficiency metric (e.g., 'ts_pct_roll_5')
        result_col: Column name containing 'W' or 'L' for win/loss
        title: Chart title
        league_avg: League average line (default: 57% for TS%)
        save_path: Path to save image (optional)
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> coby = get_player_games("Coby White", last_n=15)
        >>> coby_eff = game_efficiency(coby)
        >>> coby_roll = rolling_averages(coby_eff, metrics=['ts_pct'], windows=[5])
        >>> rolling_efficiency_chart(coby_roll, efficiency_col='ts_pct_roll_5')
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Reverse for chronological order
    plot_data = data.iloc[::-1].copy()

    x_vals = range(len(plot_data))
    y_vals = plot_data[efficiency_col].tolist()

    # Plot line
    ax.plot(x_vals, y_vals, color=tuple(c/255 for c in BULLS_RED), linewidth=2, zorder=2)

    # Add win/loss markers
    for i, (_, row) in enumerate(plot_data.iterrows()):
        if result_col in row:
            if str(row[result_col]).upper() == 'W':
                ax.scatter(i, y_vals[i], marker='^', s=100,
                           color=tuple(c/255 for c in GREEN), edgecolors='black',
                           linewidth=0.5, zorder=3)
            else:
                ax.scatter(i, y_vals[i], marker='v', s=100,
                           color=tuple(c/255 for c in RED_COLOR), edgecolors='black',
                           linewidth=0.5, zorder=3)

    # League average reference line
    ax.axhline(y=league_avg, color='gray', linestyle='--', alpha=0.7,
               label=f'League Avg: {league_avg}%', zorder=1)

    ax.set_title(title or f'Rolling {efficiency_col}', fontsize=16, fontweight='bold')
    ax.set_ylabel('Efficiency %')
    ax.set_xlabel('Game')

    # X-axis labels (dates if available)
    if 'date' in plot_data.columns:
        labels = [str(d)[5:10] if len(str(d)) > 5 else d for d in plot_data['date'].tolist()]
        ax.set_xticks(x_vals)
        ax.set_xticklabels(labels, rotation=45, ha='right')

    # Legend
    legend_elements = [
        plt.Line2D([0], [0], color=tuple(c/255 for c in BULLS_RED), linewidth=2, label='Efficiency'),
        plt.Line2D([0], [0], color='gray', linestyle='--', label=f'League Avg ({league_avg}%)'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor=tuple(c/255 for c in GREEN),
                   markersize=10, label='Win'),
        plt.Line2D([0], [0], marker='v', color='w', markerfacecolor=tuple(c/255 for c in RED_COLOR),
                   markersize=10, label='Loss'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")

    return fig


def radar_chart(
    players_data: List[dict],
    metrics: Optional[List[str]] = None,
    normalize: bool = True,
    title: str = "",
    save_path: Optional[str] = None,
    figsize: tuple = (8, 8)
) -> plt.Figure:
    """
    Create a radar/spider chart comparing players across metrics.

    Args:
        players_data: List of dicts, each with 'name' and metric values
        metrics: List of metrics to include (default: points, rebounds, assists, steals, fg_pct)
        normalize: Scale values to 0-100 for fair comparison
        title: Chart title
        save_path: Path to save image (optional)
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> coby = data.get_player_games("Coby White", last_n=10)
        >>> avgs = analysis.season_averages(coby)
        >>> avgs['name'] = 'Coby White'
        >>> radar_chart([avgs], title="Coby White Stats")
    """
    if metrics is None:
        metrics = ['points', 'rebounds', 'assists', 'steals', 'fg_pct']

    # Handle empty players list
    if not players_data:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No player data', ha='center', va='center')
        return fig

    # Filter to metrics that exist in data
    available_metrics = []
    for m in metrics:
        if all(m in p for p in players_data):
            available_metrics.append(m)

    if not available_metrics:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No metrics available', ha='center', va='center')
        return fig

    num_vars = len(available_metrics)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Complete the loop

    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))

    # Colors for multiple players
    colors = [BULLS_RED, BULLS_BLACK, GREEN, RED_COLOR]

    # Normalization: find max values for scaling
    if normalize:
        max_vals = {}
        for m in available_metrics:
            max_vals[m] = max(p.get(m, 0) for p in players_data) or 1

    for i, player in enumerate(players_data):
        values = []
        for m in available_metrics:
            val = player.get(m, 0)
            if normalize:
                val = (val / max_vals[m]) * 100 if max_vals[m] > 0 else 0
            values.append(val)
        values += values[:1]  # Complete the loop

        color = tuple(c/255 for c in colors[i % len(colors)])
        ax.plot(angles, values, 'o-', linewidth=2, label=player.get('name', f'Player {i+1}'),
                color=color)
        ax.fill(angles, values, alpha=0.25, color=color)

    # Labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([m.replace('_', ' ').title() for m in available_metrics])

    if normalize:
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])

    ax.set_title(title or 'Player Comparison', fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()

    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")

    return fig


def _draw_court(ax, color='black', lw=2):
    """
    Draw basketball half-court lines on the given axes.

    Args:
        ax: matplotlib axes
        color: Line color
        lw: Line width
    """
    # Hoop
    hoop = Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False)
    ax.add_patch(hoop)

    # Backboard
    backboard = Rectangle((-30, -7.5), 60, 0, linewidth=lw, color=color)
    ax.add_patch(backboard)

    # Paint (outer box)
    outer_box = Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color, fill=False)
    ax.add_patch(outer_box)

    # Paint (inner box)
    inner_box = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color, fill=False)
    ax.add_patch(inner_box)

    # Free throw top arc
    top_free_throw = Arc((0, 142.5), 120, 120, theta1=0, theta2=180,
                         linewidth=lw, color=color)
    ax.add_patch(top_free_throw)

    # Free throw bottom arc (dashed)
    bottom_free_throw = Arc((0, 142.5), 120, 120, theta1=180, theta2=0,
                            linewidth=lw, color=color, linestyle='dashed')
    ax.add_patch(bottom_free_throw)

    # Restricted zone arc
    restricted = Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color)
    ax.add_patch(restricted)

    # Three-point line
    corner_three_left = Rectangle((-220, -47.5), 0, 140, linewidth=lw, color=color)
    corner_three_right = Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color)
    ax.add_patch(corner_three_left)
    ax.add_patch(corner_three_right)

    three_arc = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color)
    ax.add_patch(three_arc)

    # Center court
    center_outer_arc = Arc((0, 422.5), 120, 120, theta1=180, theta2=0,
                           linewidth=lw, color=color)
    ax.add_patch(center_outer_arc)

    # Half court line
    ax.plot([-250, 250], [422.5, 422.5], linewidth=lw, color=color)

    return ax


def shot_chart(
    shots_data: pd.DataFrame,
    show_zones: bool = False,
    title: str = "",
    save_path: Optional[str] = None,
    figsize: tuple = (12, 11)
) -> plt.Figure:
    """
    Create a shot chart visualization on a basketball court.

    Args:
        shots_data: DataFrame with shot location data (loc_x, loc_y, shot_made)
        show_zones: If True, show hexbin heatmap; if False, show scatter plot
        title: Chart title
        save_path: Path to save image (optional)
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> shots = data.get_player_shots(1629632)  # Coby White
        >>> shot_chart(shots, title="Coby White Shot Chart")
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Draw court
    _draw_court(ax, color='black', lw=1)

    if not shots_data.empty:
        if show_zones:
            # Hexbin heatmap for shot efficiency
            makes = shots_data[shots_data['shot_made']]
            if len(makes) > 0:
                hb = ax.hexbin(shots_data['loc_x'], shots_data['loc_y'],
                               C=shots_data['shot_made'].astype(int),
                               reduce_C_function=np.mean,
                               gridsize=25, cmap='RdYlGn', mincnt=1)
                cb = fig.colorbar(hb, ax=ax)
                cb.set_label('FG%')
        else:
            # Scatter plot: green for makes, red for misses
            makes = shots_data[shots_data['shot_made']]
            misses = shots_data[~shots_data['shot_made']]

            if len(misses) > 0:
                ax.scatter(misses['loc_x'], misses['loc_y'], c='red', marker='x',
                           s=40, alpha=0.6, label='Miss')
            if len(makes) > 0:
                ax.scatter(makes['loc_x'], makes['loc_y'], c='green', marker='o',
                           s=40, alpha=0.6, label='Make')

            ax.legend(loc='upper right')

    # Set court dimensions
    ax.set_xlim(-250, 250)
    ax.set_ylim(-47.5, 422.5)
    ax.set_aspect('equal')
    ax.set_title(title or 'Shot Chart', fontsize=16, fontweight='bold')

    # Remove axis labels for cleaner look
    ax.set_xticks([])
    ax.set_yticks([])

    plt.tight_layout()

    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")

    return fig
