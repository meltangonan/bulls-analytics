"""Basic chart functions using matplotlib."""
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc, Patch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
import pandas as pd
from typing import Optional, List, Dict
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
    annotations: Optional[List[Dict]] = None,
    save_path: Optional[str] = None,
    figsize: tuple = (12, 11)
) -> plt.Figure:
    """
    Create a shot chart visualization on a basketball court.

    Args:
        shots_data: DataFrame with shot location data (loc_x, loc_y, shot_made)
        show_zones: If True, show hexbin heatmap; if False, show scatter plot
        title: Chart title
        annotations: List of annotation dicts to add callout text boxes.
                     Each dict should have:
                     - 'text': The callout text (e.g., "12/18 at the rim")
                     - 'position': Tuple (x, y) or preset string:
                       'top_left', 'top_right', 'bottom_left', 'bottom_right'
                     - 'fontsize': Optional font size (default: 14)
        save_path: Path to save image (optional)
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> shots = data.get_player_shots(1629632)  # Coby White
        >>> shot_chart(shots, title="Coby White Shot Chart")
        >>> # With annotations
        >>> annotations = [{'text': '12/18 at the rim', 'position': 'bottom_left'}]
        >>> shot_chart(shots, title="Shot Chart", annotations=annotations)
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

    # Add annotations (callout text boxes)
    if annotations:
        for ann in annotations:
            pos = ann.get('position', 'top_left')
            # Position presets
            if pos == 'top_left':
                x, y = -200, 380
            elif pos == 'top_right':
                x, y = 200, 380
            elif pos == 'bottom_left':
                x, y = -200, -30
            elif pos == 'bottom_right':
                x, y = 200, -30
            else:
                x, y = pos  # Custom coordinates as tuple

            ax.text(x, y, ann['text'],
                    fontsize=ann.get('fontsize', 14),
                    fontweight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.5',
                              facecolor='white',
                              edgecolor='black',
                              alpha=0.9))

    plt.tight_layout()

    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")

    return fig


def _draw_zone_boundaries(ax, color='gray', lw=1, alpha=0.3):
    """
    Draw approximate zone boundaries on the court.
    
    Args:
        ax: matplotlib axes
        color: Line color
        lw: Line width
        alpha: Transparency
    """
    # Restricted Area (already drawn as arc in _draw_court, but add circle for clarity)
    restricted_circle = Circle((0, 0), radius=48, linewidth=lw, 
                               color=color, fill=False, linestyle='--', alpha=alpha)
    ax.add_patch(restricted_circle)
    
    # Paint boundary (free throw line at y=142.5)
    # Draw lines to separate paint from mid-range
    paint_left = Rectangle((-80, -47.5), 0, 190, linewidth=lw, 
                           color=color, linestyle='--', alpha=alpha)
    paint_right = Rectangle((80, -47.5), 0, 190, linewidth=lw, 
                            color=color, linestyle='--', alpha=alpha)
    ax.add_patch(paint_left)
    ax.add_patch(paint_right)
    
    # Corner 3 boundaries (approximate at x = ±200)
    corner_left = Rectangle((-200, -47.5), 0, 140, linewidth=lw, 
                            color=color, linestyle='--', alpha=alpha)
    corner_right = Rectangle((200, -47.5), 0, 140, linewidth=lw, 
                             color=color, linestyle='--', alpha=alpha)
    ax.add_patch(corner_left)
    ax.add_patch(corner_right)
    
    return ax


def _get_zone_center(zone_name: str) -> tuple:
    """
    Get approximate center coordinates for a shot zone.
    
    Args:
        zone_name: Name of the shot zone
    
    Returns:
        Tuple of (x, y) coordinates for zone center
    """
    zone_centers = {
        'Restricted Area': (0, 0),
        'In The Paint (Non-RA)': (0, 70),
        'Mid-Range': (0, 200),
        'Left Corner 3': (-180, 50),
        'Right Corner 3': (180, 50),
        'Above the Break 3': (0, 300),
        'Backcourt': (0, 400),
    }
    
    # Try exact match first
    if zone_name in zone_centers:
        return zone_centers[zone_name]
    
    # Try partial matches
    zone_lower = zone_name.lower()
    if 'restricted' in zone_lower:
        return zone_centers['Restricted Area']
    elif 'paint' in zone_lower and 'non' in zone_lower:
        return zone_centers['In The Paint (Non-RA)']
    elif 'mid' in zone_lower or 'range' in zone_lower:
        return zone_centers['Mid-Range']
    elif 'left' in zone_lower and 'corner' in zone_lower:
        return zone_centers['Left Corner 3']
    elif 'right' in zone_lower and 'corner' in zone_lower:
        return zone_centers['Right Corner 3']
    elif 'above' in zone_lower or 'break' in zone_lower:
        return zone_centers['Above the Break 3']
    elif 'backcourt' in zone_lower:
        return zone_centers['Backcourt']
    
    # Default to center court
    return (0, 200)


def zone_leaders_chart(
    zone_leaders_dict: Dict,
    title: str = "Zone Leaders - Points Per Game",
    save_path: Optional[str] = None,
    figsize: tuple = (14, 12)
) -> plt.Figure:
    """
    Create a shot chart visualization showing which player leads in PPG for each zone.
    
    Args:
        zone_leaders_dict: Dict from zone_leaders() mapping zone names to leader info
        title: Chart title
        save_path: Path to save image (optional)
        figsize: Figure size
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> shots = data.get_team_shots()
        >>> leaders = analysis.zone_leaders(shots, min_shots=5)
        >>> zone_leaders_chart(leaders, title="Bulls Zone Leaders")
    """
    from bulls import data
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Draw court
    _draw_court(ax, color='black', lw=1.5)
    
    # Draw zone boundaries
    _draw_zone_boundaries(ax, color='gray', lw=1, alpha=0.3)
    
    if not zone_leaders_dict:
        ax.text(0, 200, 'No zone leaders data available', 
                ha='center', va='center', fontsize=14)
        ax.set_xlim(-250, 250)
        ax.set_ylim(-47.5, 422.5)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout()
        return fig
    
    # Place player headshots/names in each zone
    for zone_name, leader_info in zone_leaders_dict.items():
        zone_center = _get_zone_center(zone_name)
        x, y = zone_center
        
        player_id = leader_info.get('player_id')
        player_name = leader_info.get('player_name', 'Unknown')
        ppg = leader_info.get('ppg', 0)
        
        # Try to fetch headshot
        headshot_img = None
        if player_id:
            try:
                headshot_img = data.get_player_headshot(player_id, size=(80, 80))
            except Exception:
                pass
        
        # Place headshot or name
        if headshot_img:
            # Convert PIL image to numpy array for matplotlib
            img_array = np.array(headshot_img)
            im = OffsetImage(img_array, zoom=0.5)
            ab = AnnotationBbox(im, (x, y), frameon=True, 
                               bboxprops=dict(boxstyle='round,pad=2', 
                                            facecolor='white', 
                                            edgecolor=tuple(c/255 for c in BULLS_RED),
                                            linewidth=2))
            ax.add_artist(ab)
        else:
            # Use text if no headshot
            ax.text(x, y, player_name, ha='center', va='center',
                   fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=3', 
                           facecolor='white', 
                           edgecolor=tuple(c/255 for c in BULLS_RED),
                           linewidth=2))
        
        # Add PPG label below headshot/name
        label_y = y - 60
        ax.text(x, label_y, f"{ppg:.1f} PPG", ha='center', va='center',
               fontsize=9, fontweight='bold',
               bbox=dict(boxstyle='round,pad=2', 
                       facecolor=tuple(c/255 for c in BULLS_RED), 
                       edgecolor='black',
                       linewidth=1))
        
        # Add zone name label
        zone_label_y = y + 60 if y < 200 else y - 80
        ax.text(x, zone_label_y, zone_name, ha='center', va='center',
               fontsize=8, style='italic', alpha=0.7)
    
    # Set court dimensions
    ax.set_xlim(-250, 250)
    ax.set_ylim(-47.5, 422.5)
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=18, fontweight='bold', pad=20)
    
    # Remove axis labels for cleaner look
    ax.set_xticks([])
    ax.set_yticks([])
    
    plt.tight_layout()
    
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Saved to {save_path}")
    
    return fig
