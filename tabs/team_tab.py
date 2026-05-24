import streamlit as st
import matplotlib.pyplot as plt
from data_loader import get_competitions, get_teams, format_competition_name
from fifa_metrics_bq import analyze_team_metrics, get_team_radar_stats
from fifa_visualizations_bq import (
    get_cached_shot_map,
    get_cached_radar_chart,
    get_cached_attacking_passes,
    create_interactive_xg_distribution,
    font_play
)


def render_team_tab(client):
    st.header("Team Analysis")

    # Team and competition selectors
    col1, col2 = st.columns(2)

    with col1:
        teams_df = get_teams(client)
        selected_team = st.selectbox(
            "Select Team",
            options=sorted(teams_df['team'].tolist()),
            key="team_tab_selector"
        )

    with col2:
        competitions_df = get_competitions(client, team=selected_team)
        team_competition = st.selectbox(
            "Filter by Competition (Optional)",
            options=["All Competitions"] + competitions_df['competition_name'].tolist(),
            format_func=format_competition_name,
            key="team_tab_competition_filter"
        )

    if selected_team:
        # Set competition filter
        comp_filter = None if team_competition == "All Competitions" else team_competition

        st.subheader(f"🛡️ {selected_team} Performance Analysis")

        # Get comprehensive team metrics
        team_metrics = analyze_team_metrics(client, selected_team, competition=comp_filter, return_dict=True)

        if team_metrics:
            # Safely extract sub-dictionaries
            shooting = team_metrics.get('shooting', {})
            passing = team_metrics.get('passing', {})
            defensive = team_metrics.get('defensive', {})

            # Main KPIs and xG Distribution
            st.markdown("### 📊 Main KPIs")

            # Create 2-column layout: KPIs on left, xG chart on right
            main_kpi_col1, main_kpi_col2 = st.columns([1, 1])

            with main_kpi_col1:
                # First row of metrics (2 columns)
                kpi_row1_col1, kpi_row1_col2 = st.columns(2)

                with kpi_row1_col1:
                    matches_played = defensive.get('matches_played', 0)
                    st.metric("Matches Played", matches_played)

                    pass_completion = passing.get('pass_completion_rate', 0)
                    st.metric("Pass Completion", f"{pass_completion:.1f}%")

                with kpi_row1_col2:
                    goals = shooting.get('goals', 0)
                    st.metric("Goals Scored", goals)

                    total_passes = passing.get('total_passes', 0)
                    passes_per_match = passing.get('passes_per_match', 0)
                    st.metric("Passes/Match", f"{passes_per_match:.1f}")

                # Second row of metrics (2 columns)
                kpi_row2_col1, kpi_row2_col2 = st.columns(2)

                with kpi_row2_col1:
                    shots_on_target_pct = shooting.get('shots_on_target_percentage', 0)
                    st.metric("Shots on Target %", f"{shots_on_target_pct:.1f}%")

                    total_xg = shooting.get('total_xG', 0)
                    st.metric("Total xG", f"{total_xg:.2f}")

                with kpi_row2_col2:
                    total_shots = shooting.get('total_shots', 0)
                    st.metric("Total Shots", total_shots)

                    avg_xg_per_shot = shooting.get('xg_per_shot', 0)
                    st.metric("xG/Shot", f"{avg_xg_per_shot:.3f}")

                # Third row of metrics (2 columns)
                kpi_row3_col1, kpi_row3_col2 = st.columns(2)

                with kpi_row3_col1:
                    goals_conceded = defensive.get('goals_conceded', 0)
                    st.metric("Goals Conceded", goals_conceded)

                    shots_against = defensive.get('total_shots_against', 0)
                    st.metric("Shots Against", shots_against)

                with kpi_row3_col2:
                    shot_assists = passing.get('shot_assist_passes', 0)
                    st.metric("Shot Assists", shot_assists)

                    under_pressure_pct = passing.get('under_pressure_percentage', 0)
                    st.metric("Under Pressure %", f"{under_pressure_pct:.1f}%")

            with main_kpi_col2:
                # xG Distribution chart
                st.markdown("**xG Distribution by Shot**")
                
                @st.fragment
                def render_xg_dist():
                    with st.spinner("Generating xG distribution..."):
                        try:
                            fig_xg_dist = create_interactive_xg_distribution(client, selected_team, competition=comp_filter)
                            st.plotly_chart(fig_xg_dist, width="stretch", key="team_xg_dist")
                        except Exception as e:
                            st.error(f"Error creating xG distribution: {str(e)}")
                
                render_xg_dist()

            # Radar Chart
            st.markdown("---")
            st.markdown("### 🎯 Team Performance Radar")

            radar_col1, radar_col2 = st.columns([2, 1])

            with radar_col1:
                @st.fragment
                def render_radar():
                    with st.spinner("Generating radar chart..."):
                        try:
                            # Get radar stats
                            radar_stats = get_team_radar_stats(team_metrics)

                            # Retrieve cached radar chart bytes
                            png_bytes = get_cached_radar_chart(
                                client,
                                radar_stats,
                                team_name=selected_team,
                                competition=comp_filter,
                                team_color='#1f77b4'
                            )
                            st.image(png_bytes, use_column_width=True)
                        except Exception as e:
                            st.error(f"Error creating radar chart: {str(e)}")
                
                render_radar()

            with radar_col2:
                st.markdown("**Radar Metrics:**")
                st.markdown(f"- **Non-Penalty xG:** {shooting.get('non_penalty_avg_xG', 0):.3f}")
                st.markdown(f"- **Shots on Target %:** {shots_on_target_pct:.1f}%")
                st.markdown(f"- **Shots/Game:** {shooting.get('shots_per_match', 0):.2f}")
                st.markdown(f"- **Counter Shots/Game:** {shooting.get('counter_shots_per_match', 0):.2f}")
                st.markdown(f"- **Set Piece xG:** {shooting.get('avg_xG_set_piece', 0):.3f}")
                st.markdown(f"- **Shots Under Pressure/Game:** {shooting.get('shots_under_pressure_per_match', 0):.2f}")
                st.markdown(f"- **Through Ball %:** {passing.get('through_ball_percentage', 0):.2f}%")
                st.markdown(f"- **GK Pass Length:** {passing.get('goalkeeper_pass_avg_length', 0):.1f}m")
                st.markdown(f"- **Cross %:** {passing.get('cross_percentage', 0):.2f}%")

            # Shot Map
            st.markdown("---")
            st.markdown("### ⚽ Shot Map")

            @st.fragment
            def render_team_shot_map():
                with st.spinner("Generating shot map..."):
                    try:
                        png_bytes = get_cached_shot_map(client, selected_team, competition=comp_filter)
                        st.image(png_bytes, use_column_width=True)
                    except Exception as e:
                        st.error(f"Error creating shot map: {str(e)}")
            
            render_team_shot_map()

            # Attacking Passes Visualization
            st.markdown("---")
            st.markdown("### 🎯 Attacking Passes")
            st.markdown("*Visualization of crosses, cutbacks, switches, and through balls*")

            @st.fragment
            def render_attacking_passes():
                with st.spinner("Generating attacking passes visualization..."):
                    try:
                        # Extract pre-loaded total/completed pass counts to avoid BQ scan overhead
                        total = passing.get('total_passes', None)
                        completed = passing.get('completed_passes', None)
                        png_bytes = get_cached_attacking_passes(
                            client, selected_team, competition=comp_filter,
                            total_passes=total, completed_passes=completed
                        )
                        st.image(png_bytes, use_column_width=True)
                    except Exception as e:
                        st.error(f"Error creating attacking passes visualization: {str(e)}")
            
            render_attacking_passes()

        else:
            st.warning(f"No data found for {selected_team}")
