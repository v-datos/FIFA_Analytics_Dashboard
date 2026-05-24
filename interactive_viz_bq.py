"""
Interactive Visualization Functions for FIFA Dashboard
Using Plotly
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from typing import Optional, List, Dict
from google.cloud import bigquery

# Import BigQuery helpers
from bigquery_helpers import execute_query
from fifa_metrics_bq import calculate_radar_boundaries, normalize_to_radar_scale

def create_interactive_pressure_heatmap(client: bigquery.Client, competition: str) -> go.Figure:
    """
    Create interactive pressure heatmap comparison using Plotly.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    competition : str
        Competition name

    Returns
    -------
    go.Figure
        Plotly figure object
    """
    # Query pressure events for the competition with server-side 10x10 binning
    params = [bigquery.ScalarQueryParameter("competition", "STRING", competition)]

    query = """
    SELECT 
        team,
        FLOOR(x / 10) * 10 as x_bin, 
        FLOOR(y / 10) * 10 as y_bin, 
        COUNT(*) as count
    FROM {{TABLE}}
    WHERE competition_name = @competition
        AND type = 'Pressure'
        AND x IS NOT NULL
        AND y IS NOT NULL
    GROUP BY team, x_bin, y_bin
    """

    pressure_binned = execute_query(client, query, params)

    if pressure_binned.empty:
        fig = go.Figure()
        fig.add_annotation(text='No pressure data available',
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    teams = sorted(pressure_binned['team'].unique())
    n_teams = len(teams)

    # Calculate grid dimensions
    ncols = 3
    nrows = (n_teams + ncols - 1) // ncols

    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=teams,
        horizontal_spacing=0.02,
        vertical_spacing=0.05,
        specs=[[{"type": "xy"} for _ in range(ncols)] for _ in range(nrows)]
    )

    # Centers of the 10x10 bins
    x_centers = np.arange(5, 125, 10)
    y_centers = np.arange(5, 85, 10)

    for i, team in enumerate(teams):
        row = (i // ncols) + 1
        col = (i % ncols) + 1

        team_data = pressure_binned[pressure_binned['team'] == team]

        # Reconstruct 8x12 grid
        z = np.zeros((8, 12))
        for _, r in team_data.iterrows():
            xi = int(min(max(r['x_bin'] // 10, 0), 11))
            yi = int(min(max(r['y_bin'] // 10, 0), 7))
            z[yi, xi] = r['count']

        # Add pitch background for each subplot
        fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80,
                      fillcolor="#22312b", line=dict(width=0), layer='below',
                      row=row, col=col)

        # Add heatmap trace
        fig.add_trace(go.Heatmap(
            z=z,
            x=x_centers,
            y=y_centers,
            colorscale='Reds',
            showscale=False,
            opacity=0.7,
            hovertemplate=f'Team: {team}<br>X: %{{x}}<br>Y: %{{y}}<br>Count: %{{z}}<extra></extra>'
        ), row=row, col=col)

        # Update axes for each subplot
        fig.update_xaxes(range=[0, 120], showgrid=False, zeroline=False, visible=False, row=row, col=col)
        fig.update_yaxes(range=[0, 80], showgrid=False, zeroline=False, visible=False, row=row, col=col,
                        scaleanchor=f"x{i+1 if i>0 else ''}", scaleratio=1)

    fig.update_layout(
        title=f'Pressure Events Comparison - {competition}',
        height=300 * nrows,
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='#22312b',
        font=dict(family="Play, sans-serif", size=12)
    )

    return fig


def create_interactive_pressure_passing_comparison(client: bigquery.Client, competition: str) -> go.Figure:
    """
    Create interactive scatter plot comparing team passing accuracy vs accuracy under pressure.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    competition : str
        Competition name

    Returns
    -------
    go.Figure
        Plotly figure object
    """
    # Query aggregated pass metrics directly from BigQuery for performance
    params = [bigquery.ScalarQueryParameter("competition", "STRING", competition)]

    query = """
    SELECT
        team,
        COUNT(*) as total_passes,
        SAFE_DIVIDE(COUNTIF(pass_outcome IS NULL) * 100.0, COUNT(*)) as overall_completion,
        COUNTIF(under_pressure = TRUE) as pressure_total,
        SAFE_DIVIDE(
            COUNTIF(under_pressure = TRUE AND pass_outcome IS NULL) * 100.0,
            NULLIF(COUNTIF(under_pressure = TRUE), 0)
        ) as pressure_completion
    FROM (
        SELECT team, pass_outcome, under_pressure
        FROM {{TABLE}}
        WHERE competition_name = @competition
            AND type = 'Pass'
            AND team IS NOT NULL
        LIMIT 500000
    )
    GROUP BY team
    """

    metrics_df = execute_query(client, query, params)

    if metrics_df.empty:
        fig = go.Figure()
        fig.add_annotation(text='No pass data available',
                          x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    # Create scatter plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=metrics_df['overall_completion'],
        y=metrics_df['pressure_completion'],
        mode='markers+text',
        marker=dict(
            size=12,
            color='#667eea',
            opacity=0.7,
            line=dict(width=2, color='white')
        ),
        text=metrics_df['team'],
        textposition='top center',
        textfont=dict(
            family="Play, sans-serif",
            size=11,
            color='black'
        ),
        hovertemplate='<b>%{text}</b><br>' +
                     'Overall Completion: %{x:.1f}%<br>' +
                     'Under Pressure: %{y:.1f}%<br>' +
                     '<extra></extra>',
        customdata=np.column_stack((
            metrics_df['total_passes'],
            metrics_df['pressure_total']
        ))
    ))

    # Add diagonal reference line (where overall = under pressure)
    max_val = max(metrics_df['overall_completion'].max(), metrics_df['pressure_completion'].max())
    min_val = min(metrics_df['overall_completion'].min(), metrics_df['pressure_completion'].min())

    fig.add_trace(go.Scatter(
        x=[min_val - 5, max_val + 5],
        y=[min_val - 5, max_val + 5],
        mode='lines',
        line=dict(color='gray', width=1, dash='dash'),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Update layout
    fig.update_layout(
        title=f'{competition} - Team Passing Accuracy vs. Accuracy Under Pressure',
        xaxis_title='Overall Pass Completion %',
        yaxis_title='Pass Completion % Under Pressure',
        height=600,
        showlegend=False,
        font=dict(family="Play, sans-serif", size=12),
        hovermode='closest',
        plot_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False
        )
    )

    # Set axis ranges with some padding
    x_range = [metrics_df['overall_completion'].min() - 5, metrics_df['overall_completion'].max() + 5]
    y_range = [metrics_df['pressure_completion'].min() - 5, metrics_df['pressure_completion'].max() + 5]

    fig.update_xaxes(range=x_range)
    fig.update_yaxes(range=y_range)

    return fig


def create_interactive_shot_map(client: bigquery.Client, team: str,
                                competition: Optional[str] = None,
                                match_id: Optional[int] = None) -> go.Figure:
    """
    Create interactive shot map visualization using Plotly.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team : str
        Team name
    competition : str, optional
        Filter by competition
    match_id : int, optional
        Filter by match

    Returns
    -------
    go.Figure
        Plotly figure object
    """
    # Build WHERE clause using parameterized query
    conditions = ["team = @team", "type = 'Shot'"]
    params = [bigquery.ScalarQueryParameter("team", "STRING", team)]

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        conditions.append("match_id = @match_id")
        params.append(bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)))

    where_clause = " AND ".join(conditions)

    # Query shots data
    query = f"""
    SELECT
        x, y,
        shot_outcome,
        SAFE_CAST(shot_statsbomb_xg AS FLOAT64) as shot_statsbomb_xg,
        shot_type,
        player,
        minute
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
        AND x IS NOT NULL
        AND y IS NOT NULL
    """

    shots_df = execute_query(client, query, params)

    if shots_df.empty:
        fig = go.Figure()
        fig.add_annotation(text=f'No shot data available for {team}',
                          x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    # Create figure
    fig = go.Figure()

    # Add pitch background (green field)
    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80,
                  fillcolor="#22312b", line=dict(width=0))

    # Add pitch markings (white lines)
    # Outline
    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")

    # Halfway line
    fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80,
                  line=dict(color="white", width=2))

    # Center circle
    fig.add_shape(type="circle", x0=50, y0=30, x1=70, y1=50,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")

    # Penalty areas
    fig.add_shape(type="rect", x0=102, y0=18, x1=120, y1=62,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")
    fig.add_shape(type="rect", x0=0, y0=18, x1=18, y1=62,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")

    # Six-yard boxes
    fig.add_shape(type="rect", x0=114, y0=30, x1=120, y1=50,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")
    fig.add_shape(type="rect", x0=0, y0=30, x1=6, y1=50,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")

    # Separate goals from other shots
    goals = shots_df[shots_df['shot_outcome'] == 'Goal']
    other_shots = shots_df[shots_df['shot_outcome'] != 'Goal']

    # Plot non-goals
    if not other_shots.empty:
        fig.add_trace(go.Scatter(
            x=other_shots['x'],
            y=other_shots['y'],
            mode='markers',
            name='Shots',
            marker=dict(
                size=other_shots['shot_statsbomb_xg'] * 50 + 5,
                color='red',
                opacity=0.6,
                line=dict(width=1, color='white')
            ),
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                         'Shot Type: %{customdata[1]}<br>' +
                         'xG: %{customdata[2]:.3f}<br>' +
                         'Minute: %{customdata[3]}<br>' +
                         'Position: (%{x:.1f}, %{y:.1f})<extra></extra>',
            customdata=np.column_stack((
                other_shots['player'],
                other_shots['shot_type'],
                other_shots['shot_statsbomb_xg'],
                other_shots['minute']
            ))
        ))

    # Plot goals
    if not goals.empty:
        fig.add_trace(go.Scatter(
            x=goals['x'],
            y=goals['y'],
            mode='markers',
            name='Goals',
            marker=dict(
                size=goals['shot_statsbomb_xg'] * 50 + 10,
                color='#FFD700',
                symbol='star',
                opacity=0.95,
                line=dict(width=2, color='black')
            ),
            hovertemplate='<b>%{customdata[0]} ⚽ GOAL</b><br>' +
                         'Shot Type: %{customdata[1]}<br>' +
                         'xG: %{customdata[2]:.3f}<br>' +
                         'Minute: %{customdata[3]}<br>' +
                         'Position: (%{x:.1f}, %{y:.1f})<extra></extra>',
            customdata=np.column_stack((
                goals['player'],
                goals['shot_type'],
                goals['shot_statsbomb_xg'],
                goals['minute']
            ))
        ))

    # Update layout
    fig.update_layout(
        title=f'{team} - Interactive Shot Map (Size = xG)',
        xaxis=dict(range=[0, 120], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[0, 80], showgrid=False, zeroline=False, visible=False),
        plot_bgcolor='#22312b',
        paper_bgcolor='white',
        height=600,
        showlegend=True,
        legend=dict(x=0.02, y=0.98),
        font=dict(family="Play, sans-serif", size=12)
    )

    fig.update_xaxes(scaleanchor="y", scaleratio=1.5)

    return fig


def create_interactive_radar_chart(radar_stats: dict, team_name: str,
                                   team_color: str = '#667eea') -> go.Figure:
    """
    Create interactive radar chart for team performance metrics using Plotly.

    Parameters
    ----------
    radar_stats : dict
        Dictionary of metrics for radar
    team_name : str
        Name of the team
    team_color : str
        Color for the team's polygon

    Returns
    -------
    go.Figure
        Plotly figure object
    """
    # Extract metric names and values
    params_list = list(radar_stats.keys())
    values = [radar_stats[p] for p in params_list]

    # Calculate dynamic boundaries based on actual data
    # Pass client here if available, or use defaults
    # In a real app, we'd want to pass the competition context
    try:
        from bigquery_helpers import get_bigquery_client
        bq_client = get_bigquery_client()
        low, high = calculate_radar_boundaries(bq_client)
    except:
        low, high = [0.0]*9, [100.0]*9

    # Normalize values to 0-100 scale using centralized logic
    normalized_values = []
    for i, val in enumerate(values):
        normalized = normalize_to_radar_scale(val, i, low, high)
        normalized_values.append(normalized)

    # Create radar chart
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=normalized_values,
        theta=params_list,
        fill='toself',
        fillcolor=team_color,
        opacity=0.3,
        line=dict(color=team_color, width=2),
        name=team_name,
        hovertemplate='<b>%{theta}</b><br>' +
                     'Score: %{r:.1f}/100<br>' +
                     '<extra></extra>'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=True,
                ticks='',
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                showticklabels=True,
                gridcolor='lightgray'
            )
        ),
        showlegend=True,
        title=f'{team_name} Performance Radar',
        height=600,
        font=dict(family="Play, sans-serif", size=12)
    )

    return fig


def create_interactive_touch_heatmap(client: bigquery.Client, team: str,
                                     competition: Optional[str] = None,
                                     player: Optional[str] = None) -> go.Figure:
    """
    Create interactive touch/action heatmap using Plotly.

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
    go.Figure
        Plotly figure object
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

    if binned_df.empty:
        fig = go.Figure()
        fig.add_annotation(text='No touch data available',
                          x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    # Prepare data for heatmap
    import numpy as np
    z = np.zeros((8, 12))
    for _, row in binned_df.iterrows():
        xi = int(min(max(row['x_bin'] // 10, 0), 11))
        yi = int(min(max(row['y_bin'] // 10, 0), 7))
        z[yi, xi] = row['count']

    # Centers of the 10x10 bins
    x_centers = np.arange(5, 125, 10)
    y_centers = np.arange(5, 85, 10)

    # Create 2D histogram for heatmap
    fig = go.Figure()

    # Create heatmap using pre-calculated counts
    fig.add_trace(go.Heatmap(
        z=z,
        x=x_centers,
        y=y_centers,
        colorscale='Hot',
        opacity=0.7,
        hovertemplate='X: %{x}<br>Y: %{y}<br>Count: %{z}<extra></extra>'
    ))

    # Add pitch background
    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80,
                  fillcolor="#22312b", line=dict(width=0), layer='below')

    # Add pitch markings
    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80,
                  line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)")
    fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80,
                  line=dict(color="white", width=2))

    title = f'{player if player else team} Touch Heatmap'

    fig.update_layout(
        title=title,
        xaxis=dict(range=[0, 120], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[0, 80], showgrid=False, zeroline=False, visible=False),
        plot_bgcolor='#22312b',
        paper_bgcolor='white',
        height=600,
        font=dict(family="Play, sans-serif", size=12)
    )

    fig.update_xaxes(scaleanchor="y", scaleratio=1.5)

    return fig


def create_interactive_xg_distribution(client: bigquery.Client, team: str,
                                      competition: Optional[str] = None,
                                      color: str = '#667eea') -> go.Figure:
    """
    Create interactive xG distribution plot using Plotly.

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
    go.Figure
        Plotly figure object
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
    SELECT SAFE_CAST(shot_statsbomb_xg AS FLOAT64) as shot_statsbomb_xg, shot_outcome, player
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    """

    xg_df = execute_query(client, query, params)

    if xg_df.empty:
        fig = go.Figure()
        fig.add_annotation(text='No xG data available',
                          x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    # Create histogram
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=xg_df['shot_statsbomb_xg'],
        nbinsx=20,
        marker=dict(color=color, opacity=0.7, line=dict(color='black', width=1)),
        name='xG Distribution',
        hovertemplate='xG Range: %{x}<br>Count: %{y}<extra></extra>'
    ))

    # Add mean line
    mean_xg = xg_df['shot_statsbomb_xg'].mean()
    fig.add_vline(x=mean_xg, line_dash="dash", line_color="red",
                  annotation_text=f"Mean: {mean_xg:.3f}",
                  annotation_position="top right")

    fig.update_layout(
        title=f'{team} - Expected Goals (xG) Distribution',
        xaxis_title='Expected Goals (xG)',
        yaxis_title='Frequency',
        height=500,
        showlegend=False,
        hovermode='x',
        font=dict(family="Play, sans-serif", size=12)
    )

    return fig


def create_xg_distribution_comparison(client: bigquery.Client,
                                      team1: str, team2: str,
                                      match_id: Optional[int] = None,
                                      competition: Optional[str] = None) -> go.Figure:
    """
    Create interactive xG distribution comparison for two teams using Plotly.
    Based on Copa America dashboard style.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client
    team1 : str
        First team name
    team2 : str
        Second team name
    match_id : int, optional
        Filter by specific match
    competition : str, optional
        Filter by competition

    Returns
    -------
    go.Figure
        Plotly figure object
    """
    teams = [team1, team2]
    colors = ['#667eea', '#f5576c']  # Purple and pink

    fig = go.Figure()

    # Build WHERE clause using parameterized query
    conditions = [
        "team IN UNNEST(@teams)",
        "type = 'Shot'",
        "shot_type != 'Penalty'",
        "shot_statsbomb_xg IS NOT NULL"
    ]
    params = [bigquery.ArrayQueryParameter("teams", "STRING", teams)]

    if match_id:
        conditions.append("match_id = @match_id")
        params.append(bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)))
    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))

    where_clause = " AND ".join(conditions)

    # Single query to get xG data for both teams
    query = f"""
    SELECT team, SAFE_CAST(shot_statsbomb_xg AS FLOAT64) as shot_statsbomb_xg
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    """

    all_xg_df = execute_query(client, query, params)

    for team, color in zip(teams, colors):
        xg_df = all_xg_df[all_xg_df['team'] == team]
        
        if not xg_df.empty:
            # Create violin plot for density distribution
            fig.add_trace(go.Violin(
                x=xg_df['shot_statsbomb_xg'],
                name=team,
                fillcolor=color,
                opacity=0.2,  # More translucent
                line=dict(color=color, width=3),  # Thicker line for visibility
                meanline_visible=True,
                orientation='h',
                side='both',  # Show both sides for overlay effect
                width=1.5,
                scalemode='width'
            ))

    # Update layout
    fig.update_layout(
        title='Non-Penalty xG Distribution Comparison',
        xaxis_title='Expected Goals (xG)',
        yaxis_title='Density',
        height=500,
        showlegend=True,
        legend=dict(x=0.8, y=0.95),
        font=dict(family="Play, sans-serif", size=12),
        hovermode='x unified',
        violinmode='overlay',  # Overlay mode
        yaxis=dict(showticklabels=False)  # Hide y-axis labels for cleaner look
    )

    fig.update_xaxes(range=[0, max(0.5, all_xg_df['shot_statsbomb_xg'].max() if not all_xg_df.empty else 0.5)])
    fig.update_traces(orientation='h', side='positive', ) # width=3, points=False)

    return fig
