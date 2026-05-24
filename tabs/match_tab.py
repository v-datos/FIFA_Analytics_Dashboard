import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from google.cloud import bigquery
from bigquery_helpers import execute_query
from data_loader import get_competitions, get_matches, get_match_comparison_stats, format_competition_name
from fifa_visualizations_bq import get_cached_shot_map, create_xg_distribution_comparison

def render_match_tab(client):
    st.header("Match Analysis")

    # Competition and match selectors
    col1, col2 = st.columns(2)

    with col1:
        competitions_df = get_competitions(client)
        match_competition = st.selectbox(
            "Select Competition",
            options=competitions_df['competition_name'].tolist(),
            format_func=format_competition_name,
            key="match_tab_competition"
        )

    if match_competition:
        # Get matches for selected competition
        matches_df = get_matches(client, competition=match_competition)

        if not matches_df.empty:
            with col2:
                # Create match display options using team names
                match_options = [
                    row['teams'].replace(',', ' vs ') if pd.notna(row.get('teams')) and row.get('teams') else f"Match {row['match_id']}"
                    for _, row in matches_df.iterrows()
                ]
                selected_match_idx = st.selectbox(
                    "Select Match",
                    options=range(len(match_options)),
                    format_func=lambda x: match_options[x],
                    key="match_tab_selector"
                )
                selected_match_row = matches_df.iloc[selected_match_idx]
                selected_match_id = selected_match_row['match_id']

            # Resolve team names directly from the pre-loaded matches_df to save raw BQ scans
            teams_str = selected_match_row.get('teams', '')
            team1, team2 = None, None
            if pd.notna(teams_str) and ',' in teams_str:
                teams_list = sorted(teams_str.split(','))
                if len(teams_list) >= 2:
                    team1 = teams_list[0]
                    team2 = teams_list[1]

            if team1 and team2:

                st.markdown(f"""

                    <div style="
                        display: flex; justify-content: center; align-items: center;
                        background: linear-gradient(135deg, #0d4a28, #1a6b3c);
                        border-radius: 12px; padding: 20px; margin: 16px 0;
                        border: 2px solid #f5c518;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    ">
                        <span style="font-size:1.8rem; font-weight:bold; color:white; font-family:'Play',sans-serif;">{team1}</span>
                        <span style="font-size:1.4rem; color:#f5c518; margin: 0 24px; font-family:'Play',sans-serif;">vs</span>
                        <span style="font-size:1.8rem; font-weight:bold; color:white; font-family:'Play',sans-serif;">{team2}</span>
                    </div>
                """, unsafe_allow_html=True)

                # Main match results and xG distribution (side-by-side layout)
                match_main_col1, match_main_col2 = st.columns([1, 1])

                with match_main_col1:
                    st.markdown("### Match Results")

                    # Side-by-side team stats
                    col_team1, col_team2 = st.columns(2)
                    
                    # Get comparison stats in a single call for better performance
                    team1_stats, team2_stats = get_match_comparison_stats(client, team1, team2, selected_match_id)

                    with col_team1:
                        st.markdown(f"**{team1}**")
                        if team1_stats is not None:
                            st.metric("Possession", f"{team1_stats['possession_pct']:.1f}%")
                            st.metric("Goals", int(team1_stats['goals']))
                            st.metric("Shots", int(team1_stats['shots']))
                            st.metric("Shots on Target", int(team1_stats['shots_on_target']))
                            st.metric("Pass Accuracy", f"{team1_stats['pass_accuracy']:.1f}%")
                            st.metric("Total Passes", int(team1_stats['passes']))

                    with col_team2:
                        st.markdown(f"**{team2}**")
                        if team2_stats is not None:
                            st.metric("Possession", f"{team2_stats['possession_pct']:.1f}%")
                            st.metric("Goals", int(team2_stats['goals']))
                            st.metric("Shots", int(team2_stats['shots']))
                            st.metric("Shots on Target", int(team2_stats['shots_on_target']))
                            st.metric("Pass Accuracy", f"{team2_stats['pass_accuracy']:.1f}%")
                            st.metric("Total Passes", int(team2_stats['passes']))

                with match_main_col2:
                    # xG Distribution comparison
                    st.markdown("### xG Distribution Comparison")
                    
                    @st.fragment
                    def render_xg_comp():
                        with st.spinner("Generating xG distribution comparison..."):
                            fig_xg_comp = create_xg_distribution_comparison(client, team1, team2, match_id=selected_match_id)
                            st.plotly_chart(fig_xg_comp, width="stretch", key="xg_comparison")
                    
                    render_xg_comp()

                # Shot maps comparison
                st.markdown("---")
                st.subheader("Shot Maps")

                shot_col1, shot_col2 = st.columns(2)

                with shot_col1:
                    st.markdown(f"**{team1} Shots**")
                    
                    @st.fragment
                    def render_shot_map_team1():
                        with st.spinner(f"Generating shot map for {team1}..."):
                            png_bytes = get_cached_shot_map(client, team1, match_id=selected_match_id)
                            st.image(png_bytes, use_column_width=True)
                    
                    render_shot_map_team1()

                with shot_col2:
                    st.markdown(f"**{team2} Shots**")
                    
                    @st.fragment
                    def render_shot_map_team2():
                        with st.spinner(f"Generating shot map for {team2}..."):
                            png_bytes = get_cached_shot_map(client, team2, match_id=selected_match_id)
                            st.image(png_bytes, use_column_width=True)
                    
                    render_shot_map_team2()
            else:
                st.warning("Could not find two teams for this match.")
        else:
            st.info("No matches found for the selected competition.")
