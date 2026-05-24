"""
Static Visualization Functions for FIFA Dashboard
Using Matplotlib and mplsoccer
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from mplsoccer import Pitch, VerticalPitch, Radar
from matplotlib.font_manager import FontProperties
import matplotlib.patheffects as path_effects
from typing import Optional, Tuple, List, Dict
from google.cloud import bigquery

# Import BigQuery helpers
from bigquery_helpers import execute_query
from fifa_metrics_bq import calculate_radar_boundaries, normalize_to_radar_scale

# Load custom fonts
try:
    font_path = "Play-Regular.ttf"
    font_bold_path = "Play-Bold.ttf"
    font_play = FontProperties(fname=font_path)
    font_play_bold = FontProperties(fname=font_bold_path)
except Exception:
    font_play = FontProperties()
    font_play_bold = FontProperties(weight='bold')

def create_shot_map(client: bigquery.Client, team: str,
                   player: Optional[str] = None,
                   competition: Optional[str] = None,
                   match_id: Optional[int] = None) -> Tuple[plt.Figure, plt.Axes]:
    """Create shot map visualization for a team or player using mplsoccer."""
    conditions = ["team = @team", "type = 'Shot'"]
    params = [bigquery.ScalarQueryParameter("team", "STRING", team)]

    if player:
        conditions.append("player = @player")
        params.append(bigquery.ScalarQueryParameter("player", "STRING", player))
    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        conditions.append("match_id = @match_id")
        params.append(bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)))

    where_clause = " AND ".join(conditions)

    query = f"""
    SELECT x, y, shot_outcome, SAFE_CAST(shot_statsbomb_xg AS FLOAT64) as shot_statsbomb_xg, shot_type
    FROM (
        SELECT x, y, shot_outcome, shot_statsbomb_xg, shot_type
        FROM {{{{TABLE}}}}
        WHERE {where_clause} AND x IS NOT NULL AND y IS NOT NULL
        LIMIT 10000
    )
    """
    shots_df = execute_query(client, query, params)

    if shots_df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f'No shot data available for {team}', ha='center', va='center', fontsize=14)
        return fig, ax

    fig, ax = plt.subplots(figsize=(10, 6))
    pitch = Pitch(pitch_type='statsbomb', pitch_color='grass', line_color='white')
    pitch.draw(ax=ax)

    goals = shots_df[shots_df['shot_outcome'] == 'Goal']
    other_shots = shots_df[shots_df['shot_outcome'] != 'Goal']

    if not other_shots.empty:
        pitch.scatter(other_shots.x, other_shots.y, s=other_shots.shot_statsbomb_xg * 600,
                     c='red', alpha=0.6, ax=ax, label='Shots')
    if not goals.empty:
        pitch.scatter(goals.x, goals.y, s=goals.shot_statsbomb_xg * 600,
                     marker='football', c='black', alpha=0.8, ax=ax, label='Goals')

    title = f'{player if player else team} - Shot Map (Size = xG)'
    ax.set_title(title, fontsize=22, pad=20, fontproperties=font_play_bold)
    ax.legend(loc='upper right')
    plt.tight_layout()
    return fig, ax

# ============================================================================
# RADAR CHARTS
# ============================================================================



def create_team_radar_chart(client: bigquery.Client, team_stats: list, font_properties: FontProperties,
                           team_name: str,
                           competition: Optional[str] = None,
                           team_color: str = '#aa65b2',
                           ring_color: str = '#66d8ba',
                           inner_ring_face: str = '#ffb2b2',
                           inner_ring_edge: str = '#fc5f5f') -> Tuple[plt.Figure, plt.Axes]:
    """
    Create radar chart for team performance metrics using mplsoccer.Radar.
    Now with dynamically calculated boundaries based on actual data.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team_stats : list
        List of team statistics in order:
        [Non-penalty xG, Shots on target %, Shots per game, Counter shots per game,
         Set piece xG, Shots under pressure per game, Through ball %, GK pass length, Cross %]
    font_properties : FontProperties
        Font properties for text
    team_name : str
        Name of the team
    competition : str, optional
        Filter boundaries by competition
    team_color : str
        Color for the team's polygon
    ring_color : str
        Color for outer rings
    inner_ring_face : str
        Face color for inner rings
    inner_ring_edge : str
        Edge color for inner rings

    Returns
    -------
    Tuple[plt.Figure, plt.Axes]
        Matplotlib figure and axes
    """
    # Define parameters
    params = [
        "Non-Penalty xG",
        "Shots on Target %",
        "Shots per Game",
        "Counter Attacking Shots per Game",
        "Set Piece xG",
        "Shots Under Pressure per Game",
        "Through ball %",
        "Goalkeeper Pass Length (avg)",
        "Cross %"
    ]

    # Calculate dynamic boundaries based on actual data
    low, high = calculate_radar_boundaries(client, competition=competition)

    # Initialize the Radar object
    radar = Radar(
        params,
        low,
        high,
        round_int=[False] * len(params),
        num_rings=4,
        ring_width=1,
        center_circle_radius=1
    )

    # Create the figure and axis
    fig, ax = radar.setup_axis()

    # Draw the circles
    rings_inner = radar.draw_circles(
        ax=ax,
        facecolor=inner_ring_face,
        edgecolor=inner_ring_edge
    )

    # Draw the radar
    radar_output = radar.draw_radar(
        team_stats,
        ax=ax,
        kwargs_radar={'facecolor': team_color},
        kwargs_rings={'facecolor': ring_color}
    )
    radar_poly, rings_outer, vertices = radar_output

    # Add the labels
    range_labels = radar.draw_range_labels(
        ax=ax,
        fontsize=14,
        zorder=2.5,
        fontproperties=font_properties
    )

    param_labels = radar.draw_param_labels(
        ax=ax,
        fontsize=14,
        fontproperties=font_properties
    )

    # Add title if team name is provided
    if team_name:
        ax.set_title(f"{team_name} Attacking Radar",
                    fontproperties=font_play_bold,
                    pad=15,
                    fontsize=24)

    return fig, ax


# ============================================================================
# PASS MAPS
# ============================================================================

def create_pass_network(client: bigquery.Client, team: str, match_id: int,
                       half: Optional[int] = None) -> Tuple[plt.Figure, plt.Axes]:
    """
    Create pass network visualization for a team in a match.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team : str
        Team name
    match_id : int
        Match ID
    half : int, optional
        Filter by half (1 or 2)

    Returns
    -------
    Tuple[plt.Figure, plt.Axes]
        Matplotlib figure and axes
    """
    # Build WHERE clause using parameterized query
    conditions = [
        "team = @team",
        "match_id = @match_id",
        "type = 'Pass'",
        "pass_outcome IS NULL"  # Only completed passes
    ]
    params = [
        bigquery.ScalarQueryParameter("team", "STRING", team),
        bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)),
    ]

    if half:
        conditions.append("period = @half")
        params.append(bigquery.ScalarQueryParameter("half", "INT64", int(half)))

    where_clause = " AND ".join(conditions)

    # Query pass data
    query = f"""
    SELECT
        player,
        pass_recipient,
        x, y,
        pass_end_x, pass_end_y
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
        AND x IS NOT NULL
        AND y IS NOT NULL
        AND pass_end_x IS NOT NULL
        AND pass_end_y IS NOT NULL
        AND pass_recipient IS NOT NULL
    """

    passes_df = execute_query(client, query, params)

    if passes_df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f'No pass data available',
                ha='center', va='center', fontsize=14)
        return fig, ax

    # Create pitch
    fig, ax = plt.subplots(figsize=(14, 10))
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#22312b', line_color='white')
    pitch.draw(ax=ax)

    # Calculate player average positions
    player_positions = passes_df.groupby('player').agg({
        'x': 'mean',
        'y': 'mean'
    }).reset_index()

    # Calculate pass connections
    pass_connections = passes_df.groupby(['player', 'pass_recipient']).size().reset_index(name='count')

    # Merge with positions
    pass_connections = pass_connections.merge(
        player_positions, left_on='player', right_on='player'
    ).rename(columns={'x': 'x_start', 'y': 'y_start'})

    pass_connections = pass_connections.merge(
        player_positions, left_on='pass_recipient', right_on='player',
        suffixes=('', '_end')
    ).rename(columns={'x': 'x_end', 'y': 'y_end'})

    # Plot top connections (minimum 3 passes)
    top_connections = pass_connections[pass_connections['count'] >= 3]

    if not top_connections.empty:
        for _, row in top_connections.iterrows():
            pitch.lines(row['x_start'], row['y_start'],
                       row['x_end'], row['y_end'],
                       lw=row['count'] / 3, color='white', alpha=0.5,
                       ax=ax, zorder=1)

    # Plot player positions
    pitch.scatter(player_positions.x, player_positions.y,
                 s=300, c='#FF4444', edgecolors='white',
                 linewidth=2, alpha=0.9, ax=ax, zorder=2)

    # Add player labels
    for _, row in player_positions.iterrows():
        # Get last name
        last_name = row['player'].split()[-1] if ' ' in row['player'] else row['player']
        ax.text(row['x'], row['y'], last_name[:8], fontsize=7,
               ha='center', va='center', color='white', weight='bold',
               zorder=3)

    # Add title
    half_text = f" - Half {half}" if half else ""
    ax.set_title(f'{team} Pass Network{half_text}', fontsize=16, pad=20,
                fontproperties=font_play_bold, color='white')

    plt.tight_layout()
    return fig, ax


# ============================================================================
# HEATMAPS
# ============================================================================

def create_touch_heatmap(client: bigquery.Client, team: str,
                        competition: Optional[str] = None,
                        player: Optional[str] = None) -> Tuple[plt.Figure, plt.Axes]:
    """
    Create touch/action heatmap for a team or player.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team : str
        Team name
    competition : str, optional
        Filter by competition
    player : str, optional
        Filter by player

    Returns
    -------
    Tuple[plt.Figure, plt.Axes]
        Matplotlib figure and axes
    """
    # Build WHERE clause using parameterized query
    conditions = ["team = @team", "x IS NOT NULL", "y IS NOT NULL"]
    params = [bigquery.ScalarQueryParameter("team", "STRING", team)]

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if player:
        conditions.append("player = @player")
        params.append(bigquery.ScalarQueryParameter("player", "STRING", player))

    where_clause = " AND ".join(conditions)

    # Query touch data using server-side binning for performance
    # StatsBomb pitch is 120x80. (12, 8) bins means each bin is 10x10.
    query = f"""
    SELECT 
        FLOOR(x / 10) * 10 as x_bin, 
        FLOOR(y / 10) * 10 as y_bin, 
        COUNT(*) as count
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    GROUP BY x_bin, y_bin
    """

    binned_df = execute_query(client, query, params)

    # Create pitch
    fig, ax = plt.subplots(figsize=(12, 8))
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#22312b', line_color='white',
                  line_zorder=2)
    pitch.draw(ax=ax)

    if binned_df.empty:
        ax.text(60, 40, f'No touch data available',
                ha='center', va='center', fontsize=14, color='white')
        return fig, ax

    # Prepare bin_statistic manual structure for mplsoccer
    # We need to map our BQ bins to the grid expected by mplsoccer
    import numpy as np
    
    # Create the statistic matrix (8 rows for y, 12 columns for x)
    # Note: StatsBomb y-axis is inverted in some contexts, but Pitch handles it.
    # We'll use the same binning as Pitch(bins=(12, 8)) would.
    statistic = np.zeros((8, 12))
    for _, row in binned_df.iterrows():
        xi = int(min(max(row['x_bin'] // 10, 0), 11))
        yi = int(min(max(row['y_bin'] // 10, 0), 7))
        statistic[yi, xi] = row['count']

    # Get the grid from pitch to ensure alignment
    # We use a dummy bin_statistic to get the correct structure
    dummy_stat = pitch.bin_statistic([0], [0], bins=(12, 8))
    dummy_stat['statistic'] = statistic

    # Create heatmap
    pitch.heatmap(dummy_stat, ax=ax, cmap='hot', edgecolors='#22312b', alpha=0.7)

    # Add title
    title = f'{player if player else team} Touch Heatmap'
    ax.set_title(title, fontsize=16, pad=20, fontproperties=font_play_bold, color='white')

    plt.tight_layout()
    return fig, ax

def plot_xg_distribution(client: bigquery.Client, team: str,
                        competition: Optional[str] = None,
                        color: str = '#1f77b4') -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot xG distribution for a team.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team : str
        Team name
    competition : str, optional
        Filter by competition
    color : str
        Color for the plot

    Returns
    -------
    Tuple[plt.Figure, plt.Axes]
        Matplotlib figure and axes
    """
    # Build WHERE clause using parameterized query
    conditions = ["team = @team", "type = 'Shot'", "shot_statsbomb_xg IS NOT NULL"]
    params = [bigquery.ScalarQueryParameter("team", "STRING", team)]

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))

    where_clause = " AND ".join(conditions)

    # Query xG data
    query = f"""
    SELECT SAFE_CAST(shot_statsbomb_xg AS FLOAT64) as shot_statsbomb_xg
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    """

    xg_df = execute_query(client, query, params)

    if xg_df.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, 'No xG data available', ha='center', va='center')
        return fig, ax

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Histogram
    ax.hist(xg_df['shot_statsbomb_xg'], bins=20, color=color, alpha=0.7, edgecolor='black')

    # Add mean line
    mean_xg = xg_df['shot_statsbomb_xg'].mean()
    ax.axvline(mean_xg, color='red', linestyle='--', linewidth=2,
              label=f'Mean: {mean_xg:.3f}')

    ax.set_xlabel('Expected Goals (xG)', fontsize=12, fontproperties=font_play)
    ax.set_ylabel('Frequency', fontsize=12, fontproperties=font_play)
    ax.set_title(f'{team} - xG Distribution', fontsize=14, fontproperties=font_play_bold)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig, ax


def plot_pressure_events(client: bigquery.Client, competition: str) -> plt.Figure:
    """
    Create pressure events heatmap comparison for all teams in a competition.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    competition : str
        Competition name

    Returns
    -------
    plt.Figure
        Matplotlib figure object
    """
    # Query pressure events for the competition using parameterized query
    params = [bigquery.ScalarQueryParameter("competition", "STRING", competition)]

    query = """
    SELECT team, x, y
    FROM {{TABLE}}
    WHERE competition_name = @competition
        AND type = 'Pressure'
        AND x IS NOT NULL
        AND y IS NOT NULL
    """

    pressure_df = execute_query(client, query, params)

    if pressure_df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No pressure data available',
                ha='center', va='center', fontsize=14)
        return fig

    # Setup pitch
    pitch = Pitch(line_zorder=2, line_color='black', pad_top=20)

    # Create bin statistic template
    bin_statistic = pitch.bin_statistic([0], [0], statistic='count', bins=(6, 1),
        normalize=True)

    GRID_HEIGHT = 0.8
    CBAR_WIDTH = 0.03

    teams = sorted(pressure_df['team'].unique())
    n_teams = len(teams)

    # Calculate grid dimensions
    ncols = min(5, n_teams)
    nrows = (n_teams + ncols - 1) // ncols  # Ceiling division

    fig, axs = pitch.grid(nrows=nrows, ncols=ncols, figheight=max(5, nrows * 2.5),
                          grid_width=0.88, left=0.025,
                          endnote_height=0.03, endnote_space=0,
                          axis=False,
                          title_space=0.02, title_height=0.06, grid_height=GRID_HEIGHT)
    fig.set_facecolor('white')

    for i, ax in enumerate(axs['pitch'].flat[:n_teams]):
        # Plot team name
        ax.text(60, -10, teams[i],
                ha='center', va='center', fontsize=25,
                fontproperties=font_play)

        # Calculate and plot heatmap
        bin_statistic['statistic'] = pitch.bin_statistic(
            pressure_df[pressure_df['team'] == teams[i]]['x'],
            pressure_df[pressure_df['team'] == teams[i]]['y'],
            statistic='count',
            bins=(6, 1),
            normalize=True
        )['statistic']

        heatmap = pitch.heatmap(bin_statistic, ax=ax, cmap='Reds', alpha=0.8)

    # Remove any unused axes
    for ax in axs['pitch'].flat[n_teams:]:
        ax.remove()

    # Add colorbar
    if n_teams > 0:
        cbar_bottom = axs['pitch'][-1, 0].get_position().y0
        cbar_left = axs['pitch'][0, -1].get_position().x1 + 0.01
        ax_cbar = fig.add_axes((cbar_left, cbar_bottom, CBAR_WIDTH,
                                GRID_HEIGHT - 0.036))
        cbar = plt.colorbar(heatmap, cax=ax_cbar)
        for label in cbar.ax.get_yticklabels():
            label.set_fontproperties(font_play)
            label.set_fontsize(20)

    # Add title
    title = axs['title'].text(0.5, 0.5, f'Pressure Events by Team - {competition}',
                              ha='center', va='center', fontsize=30, fontproperties=font_play_bold)

    return fig


def plot_attacking_passes(client: bigquery.Client, team: str,
                          competition: Optional[str] = None,
                          match_id: Optional[int] = None) -> Tuple[plt.Figure, object]:
    """
    Plots a map of attacking passes (crosses, cutbacks, switches, and through balls) for a given team.
    Same style as Copa America dashboard.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team : str
        The name of the team to analyze
    competition : str, optional
        Filter by competition
    match_id : int, optional
        Filter by match

    Returns
    -------
    Tuple[plt.Figure, object]
        Matplotlib figure and axes objects
    """
    # Build WHERE clause using parameterized query
    conditions = [
        "team = @team",
        "type = 'Pass'",
        "x IS NOT NULL",
        "y IS NOT NULL",
        "pass_end_x IS NOT NULL",
        "pass_end_y IS NOT NULL"
    ]
    params = [bigquery.ScalarQueryParameter("team", "STRING", team)]

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        conditions.append("match_id = @match_id")
        params.append(bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)))

    where_clause = " AND ".join(conditions)

    # Query pass data
    query = f"""
    SELECT
        x, y,
        pass_end_x, pass_end_y,
        pass_outcome,
        pass_cross,
        pass_cut_back,
        pass_switch,
        pass_through_ball
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    """

    pass_df = execute_query(client, query, params)

    if pass_df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f'No pass data available for {team}',
                ha='center', va='center', fontsize=14)
        return fig, ax

    # Filter different types of passes
    completed_passes = pass_df[pass_df['pass_outcome'].isna()]  # NULL means completed
    # Note: BigQuery BOOL columns are returned as Python bools. 
    # Use direct boolean check or convert to bool for robustness.
    cross_passes = pass_df[pass_df['pass_cross'].fillna(False).astype(bool)]
    cutback_passes = pass_df[pass_df['pass_cut_back'].fillna(False).astype(bool)]
    switch_passes = pass_df[pass_df['pass_switch'].fillna(False).astype(bool)]
    through_ball_passes = pass_df[pass_df['pass_through_ball'].fillna(False).astype(bool)]

    # Create the pitch
    pitch = VerticalPitch(
        pitch_type='statsbomb',
        line_color='black',
    )

    # Create the figure with subplots
    fig, axs = pitch.grid(ncols=4, endnote_height=0, axis=False)
    fig.set_facecolor("#f4f4f4")

    # Plot arrows for each pass type
    if not cross_passes.empty:
        pitch.arrows(
            cross_passes.x, cross_passes.y, cross_passes.pass_end_x, cross_passes.pass_end_y,
            width=1, headwidth=8, headlength=8, color='#d73728', ax=axs['pitch'][0],
            label=f'{team} Cross Passes'
        )

    if not cutback_passes.empty:
        pitch.arrows(
            cutback_passes.x, cutback_passes.y, cutback_passes.pass_end_x, cutback_passes.pass_end_y,
            width=1, headwidth=8, headlength=8, color='blue', ax=axs['pitch'][1],
            label=f'{team} Cut Back Passes'
        )

    if not switch_passes.empty:
        pitch.arrows(
            switch_passes.x, switch_passes.y, switch_passes.pass_end_x, switch_passes.pass_end_y,
            width=1, headwidth=10, headlength=8, color='green', ax=axs['pitch'][2],
            label=f'{team} Switch Passes'
        )

    if not through_ball_passes.empty:
        pitch.arrows(
            through_ball_passes.x, through_ball_passes.y, through_ball_passes.pass_end_x, through_ball_passes.pass_end_y,
            width=1, headwidth=8, headlength=8, color='orange', ax=axs['pitch'][3],
            label=f'{team} Through ball Passes'
        )

    # Add titles and text
    title_text = f'Attacking Passes for {team}'
    if match_id:
        title_text += f' - Match {match_id}'
    elif competition:
        title_text += f' - {competition}'

    axs['title'].text(
        0.55, 0.6, title_text, fontproperties=font_play_bold,
        color='#000009', va='center', ha='center', fontsize=36
    )

    axs['title'].text(
        0.06, 0.8, f"Total Passes: {len(pass_df)}",
        color='#000009', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    axs['title'].text(
        0.08, 0.6, f"Completed Passes: {len(completed_passes)}",
        color='#000009', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    completion_rate = (len(completed_passes) / len(pass_df) * 100) if len(pass_df) > 0 else 0
    axs['title'].text(
        0.08, 0.4, f"Completion Rate: {completion_rate:.2f}%",
        color='#000009', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    axs['title'].text(
        0.12, 0.1, f'Cross Passes: {len(cross_passes)}',
        color='#d73728', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    axs['title'].text(
        0.37, 0.1, f'Cut Back Passes: {len(cutback_passes)}',
        color='blue', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    axs['title'].text(
        0.63, 0.1, f'Switch Passes: {len(switch_passes)}',
        color='green', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    axs['title'].text(
        0.89, 0.1, f'Through Balls: {len(through_ball_passes)}',
        color='orange', va='center', ha='center', fontsize=18, fontproperties=font_play,
    )

    return fig, axs


# ============================================================================
# PLOTLY INTERACTIVE VISUALIZATIONS
# ============================================================================

