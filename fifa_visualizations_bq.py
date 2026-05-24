"""
FIFA Dashboard Visualization Functions - Facade Module
This module delegates to static_viz_bq and interactive_viz_bq for better modularity.
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
