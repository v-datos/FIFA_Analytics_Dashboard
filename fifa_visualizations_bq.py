"""
FIFA Dashboard Visualization Functions - Facade Module
This module delegates to static_viz_bq and interactive_viz_bq for better modularity.
Also provides highly-performant cached static PNG image bytes to speed up Streamlit rendering.
"""

from typing import Optional, Tuple, List, Dict
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from google.cloud import bigquery
import streamlit as st

# Import font logic (shared across modules)
try:
    font_path = "Play-Regular.ttf"
    font_bold_path = "Play-Bold.ttf"
    font_play = FontProperties(fname=font_path)
    font_play_bold = FontProperties(fname=font_bold_path)
except Exception as e:
    # st.warning(f"Failed to load custom fonts: {e}. Using defaults.")
    font_play = FontProperties()
    font_play_bold = FontProperties(weight='bold')

# Import metrics (for boundaries)
from fifa_metrics_bq import calculate_radar_boundaries

# Import static visualizations (Matplotlib/mplsoccer)
from static_viz_bq import (
    create_shot_map,
    create_team_radar_chart,
    create_pass_network,
    create_touch_heatmap,
    plot_xg_distribution,
    plot_pressure_events,
    plot_attacking_passes
)

# Import interactive visualizations (Plotly)
from interactive_viz_bq import (
    create_interactive_pressure_heatmap,
    create_interactive_pressure_passing_comparison,
    create_interactive_shot_map,
    create_interactive_radar_chart,
    create_interactive_touch_heatmap,
    create_interactive_xg_distribution,
    create_xg_distribution_comparison
)

# ============================================================================
# HIGH PERFORMANCE CACHED PNG VISUALIZATIONS
# ============================================================================

@st.cache_data(ttl=600)
def get_cached_shot_map(_client: bigquery.Client, team: str,
                       player: Optional[str] = None,
                       competition: Optional[str] = None,
                       match_id: Optional[int] = None) -> bytes:
    """Draw and serialize shot map to static PNG bytes."""
    fig, ax = create_shot_map(_client, team, player, competition, match_id)
    from bigquery_helpers import fig_to_png_bytes
    return fig_to_png_bytes(fig)


@st.cache_data(ttl=600)
def get_cached_radar_chart(_client: bigquery.Client, team_stats: list,
                           team_name: str,
                           competition: Optional[str] = None,
                           team_color: str = '#1f77b4') -> bytes:
    """Draw and serialize team radar chart to static PNG bytes."""
    fig, ax = create_team_radar_chart(
        _client, team_stats, font_play, team_name, competition, team_color
    )
    from bigquery_helpers import fig_to_png_bytes
    return fig_to_png_bytes(fig)


@st.cache_data(ttl=600)
def get_cached_pass_network(_client: bigquery.Client, team: str, match_id: int,
                            half: Optional[int] = None) -> bytes:
    """Draw and serialize pass network to static PNG bytes."""
    fig, ax = create_pass_network(_client, team, match_id, half)
    from bigquery_helpers import fig_to_png_bytes
    return fig_to_png_bytes(fig)


@st.cache_data(ttl=600)
def get_cached_touch_heatmap(_client: bigquery.Client, team: str,
                             competition: Optional[str] = None,
                             player: Optional[str] = None) -> bytes:
    """Draw and serialize touch heatmap to static PNG bytes."""
    fig, ax = create_touch_heatmap(_client, team, competition, player)
    from bigquery_helpers import fig_to_png_bytes
    return fig_to_png_bytes(fig)


@st.cache_data(ttl=600)
def get_cached_attacking_passes(_client: bigquery.Client, team: str,
                               competition: Optional[str] = None,
                               match_id: Optional[int] = None,
                               total_passes: Optional[int] = None,
                               completed_passes: Optional[int] = None) -> bytes:
    """Draw and serialize attacking passes map to static PNG bytes."""
    fig, axs = plot_attacking_passes(
        _client, team, competition, match_id, total_passes, completed_passes
    )
    from bigquery_helpers import fig_to_png_bytes
    return fig_to_png_bytes(fig)


@st.cache_data(ttl=600)
def get_cached_pressure_events(_client: bigquery.Client, competition: str) -> bytes:
    """Draw and serialize pressure events heatmap grid to static PNG bytes."""
    fig = plot_pressure_events(_client, competition)
    from bigquery_helpers import fig_to_png_bytes
    return fig_to_png_bytes(fig)
