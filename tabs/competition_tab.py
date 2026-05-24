import streamlit as st
import matplotlib.pyplot as plt
from google.cloud import bigquery
from bigquery_helpers import execute_query
from data_loader import get_competitions, format_competition_name
from fifa_visualizations_bq import plot_pressure_events, create_interactive_pressure_passing_comparison

def render_competition_tab(client):
    st.header("Competition Overview")

    # Get competitions
    competitions_df = get_competitions(client)

    # Competition selector
    selected_competition = st.selectbox(
        "Select Competition",
        options=competitions_df['competition_name'].tolist(),
        format_func=format_competition_name,
        key="comp_tab_selector"
    )

    if selected_competition:
        st.subheader(f"📊 {format_competition_name(selected_competition)}")

        # Get competition statistics
        comp_query = """
        SELECT
            COUNT(DISTINCT match_id) as total_matches,
            COUNT(DISTINCT team) as total_teams,
            COUNT(DISTINCT player) as total_players,
            COUNTIF(type = 'Shot' AND shot_outcome = 'Goal') as total_goals,
            COUNTIF(type = 'Shot') as total_shots,
            COUNTIF(foul_committed_card IN ('Yellow Card', 'Red Card')) as total_cards,
            COUNTIF(type = 'Shot' AND shot_type = 'Penalty' AND shot_outcome = 'Goal') as total_penalty_goals,
            SUM(CASE WHEN type = 'Shot' AND shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END) as total_xg,
            COUNTIF(type = 'Foul Committed') as total_fouls,
            COUNTIF(type = 'Duel' AND duel_type = 'Tackle') as total_tackles
        FROM {{TABLE}}
        WHERE competition_name = @competition
        """
        comp_params = [bigquery.ScalarQueryParameter("competition", "STRING", selected_competition)]
        comp_stats = execute_query(client, comp_query, comp_params)

        if not comp_stats.empty:
            # Display metrics - First row
            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            col_a.metric("Total Matches", int(comp_stats['total_matches'].iloc[0]))
            col_b.metric("Total Teams", int(comp_stats['total_teams'].iloc[0]))
            col_c.metric("Total Players", int(comp_stats['total_players'].iloc[0]))
            col_d.metric("Total Goals", int(comp_stats['total_goals'].iloc[0]))
            col_e.metric("Total Penalty Goals", int(comp_stats['total_penalty_goals'].iloc[0]))

            # Second row
            col_f, col_g, col_h, col_i, col_j = st.columns(5)
            col_f.metric("Total Shots", int(comp_stats['total_shots'].iloc[0]))
            col_g.metric("Total xG", f"{comp_stats['total_xg'].iloc[0]:.2f}" if comp_stats['total_xg'].iloc[0] else "0.00")
            col_h.metric("Total Fouls", int(comp_stats['total_fouls'].iloc[0]))
            col_i.metric("Total Tackles", int(comp_stats['total_tackles'].iloc[0]))
            col_j.metric("Total Cards", int(comp_stats['total_cards'].iloc[0]))
        else:
            st.error("No competition statistics found. Query may have failed.")

        # Top scorers in competition
        st.subheader("🥇 Top Scorers")
        top_scorers_query = """
        SELECT
            player,
            team,
            COUNTIF(type = 'Shot' AND shot_outcome = 'Goal') as goals,
            COUNTIF(type = 'Shot') as shots,
            ROUND(SUM(CASE WHEN type = 'Shot' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END), 2) as total_xg
        FROM (
            SELECT player, team, type, shot_outcome, shot_statsbomb_xg
            FROM {{TABLE}}
            WHERE competition_name = @competition
            LIMIT 100000
        )
        WHERE player IS NOT NULL
        GROUP BY player, team
        HAVING goals > 0
        ORDER BY goals DESC
        LIMIT 10
        """
        top_scorers = execute_query(client, top_scorers_query, comp_params)
        st.dataframe(
            top_scorers.style
                .format({"total_xg": "{:.2f}"})
                .background_gradient(subset=["goals"], cmap="Greens"),
            width="stretch",
            hide_index=True
        )

        # Pressure Events Comparison
        st.markdown("---")
        st.subheader("📊 Pressure Events Comparison")
        
        @st.fragment
        def render_pressure_events():
            with st.spinner("Generating pressure events visualization..."):
                try:
                    fig_pressure = plot_pressure_events(client, selected_competition)
                    st.pyplot(fig_pressure)
                    plt.close(fig_pressure)
                except Exception as e:
                    st.error(f"Error creating pressure events comparison: {str(e)}")
        
        render_pressure_events()

        # Pass Pressure Analysis Comparison
        st.markdown("---")
        st.subheader("🎯 Pass Pressure Analysis")
        st.markdown("*Interactive scatter plot - Compare overall passing accuracy vs accuracy under pressure*")
        
        @st.fragment
        def render_pass_pressure():
            with st.spinner("Generating pass pressure comparison..."):
                fig_pass_pressure = create_interactive_pressure_passing_comparison(client, selected_competition)
                st.plotly_chart(fig_pass_pressure, width="stretch", key="pass_pressure_comparison")
        
        render_pass_pressure()
