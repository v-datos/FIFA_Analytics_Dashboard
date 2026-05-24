import streamlit as st
import matplotlib.pyplot as plt
from google.cloud import bigquery
from bigquery_helpers import execute_query
from data_loader import get_players, get_competitions, get_player_stats, format_competition_name
from fifa_visualizations_bq import get_cached_shot_map


def render_player_tab(client):
    st.header("Player Analysis")

    # Player search
    players_df = get_players(client)

    col1, col2 = st.columns(2)

    with col1:
        # Create player search options with team info
        player_options = [f"{row['player']} ({row['team']})" for _, row in players_df.iterrows()]
        selected_player_option = st.selectbox(
            "Search and Select Player",
            options=player_options,
            key="player_tab_search"
        )

        # Extract player name and team
        selected_player = None
        if selected_player_option:
            selected_player = selected_player_option.rsplit(" (", 1)[0]
            player_team = selected_player_option.rsplit(" (", 1)[1].rstrip(")")

    with col2:
        competitions_df = get_competitions(client, team=player_team if selected_player else None)
        player_competition = st.selectbox(
            "Filter by Competition (Optional)",
            options=["All Competitions"] + competitions_df['competition_name'].tolist(),
            format_func=format_competition_name,
            key="player_tab_competition_filter"
        )

    if selected_player:
        comp_filter = None if player_competition == "All Competitions" else player_competition

        st.subheader(f"👤 {selected_player} ({player_team})")

        # Get player statistics
        player_stats_df = get_player_stats(client, selected_player, team_name=player_team, competition=comp_filter)

        if not player_stats_df.empty:
            stats = player_stats_df.iloc[0]

            # Player KPIs
            st.markdown("### 📊 Player Statistics")

            p_col1, p_col2, p_col3, p_col4 = st.columns(4)

            with p_col1:
                st.metric("Position", stats.get('position', 'Unknown') if stats.get('position') else "Unknown")
                st.metric("Goals", int(stats['goals']))

            with p_col2:
                st.metric("Shots", int(stats['shots']))
                st.metric("Shots on Target", int(stats['shots_on_target']))

            with p_col3:
                st.metric("Assists", int(stats['assists']))
                st.metric("Passes", int(stats['passes']))

            with p_col4:
                pass_completion = (stats['successful_passes'] / stats['passes'] * 100) if stats['passes'] > 0 else 0
                st.metric("Pass Completion", f"{pass_completion:.1f}%")
                st.metric("Cards", int(stats['cards']))

            # Additional stats
            p_col5, p_col6, p_col7, p_col8 = st.columns(4)

            with p_col5:
                st.metric("Tackles", int(stats['tackles']))

            with p_col6:
                st.metric("Interceptions", int(stats['interceptions']))

            with p_col7:
                st.metric("Fouls", int(stats['fouls']))

            with p_col8:
                total_xg = stats['total_xg'] if stats['total_xg'] else 0
                st.metric("Total xG", f"{total_xg:.2f}")

            # Player Shot Map
            st.markdown("---")
            st.markdown("### ⚽ Shot Map")

            @st.fragment
            def render_player_shot_map():
                with st.spinner(f"Generating shot map for {selected_player}..."):
                    try:
                        # Use the cached static PNG wrapper
                        png_bytes = get_cached_shot_map(
                            client, 
                            player_team, 
                            player=selected_player, 
                            competition=comp_filter
                        )
                        st.image(png_bytes, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating player shot map: {str(e)}")
            
            render_player_shot_map()

            # Match History
            st.markdown("---")
            st.markdown("### 📅 Match History")

            # Build match history query from aggregated tables (slashing scans by >99.9%)
            history_params = [
                bigquery.ScalarQueryParameter("player", "STRING", selected_player),
                bigquery.ScalarQueryParameter("team", "STRING", player_team),
            ]

            if comp_filter:
                comp_condition_history = "AND tm.competition_name = @competition"
                history_params.append(bigquery.ScalarQueryParameter("competition", "STRING", comp_filter))
            else:
                comp_condition_history = ""

            match_history_query = f"""
            SELECT
                ps.match_id,
                tm.competition_name,
                ps.goals,
                ps.total_shots as shots,
                ps.assists,
                ps.successful_passes,
                ps.total_passes,
                ROUND(ps.xg, 2) as xg
            FROM `midyear-castle-328020.fifa_data.player_stats_summary` ps
            JOIN `midyear-castle-328020.fifa_data.team_match_summary` tm
                ON ps.match_id = tm.match_id AND ps.team = tm.team
            WHERE ps.player = @player
                AND ps.team = @team
                {comp_condition_history}
            ORDER BY ps.match_id
            """

            match_history = execute_query(client, match_history_query, history_params)

            if not match_history.empty:
                # Calculate pass accuracy
                match_history['pass_accuracy'] = (match_history['successful_passes'] / match_history['total_passes'] * 100).round(1)
                match_history['pass_accuracy'] = match_history['pass_accuracy'].fillna(0)

                display_history = match_history[['match_id', 'competition_name', 'goals', 'shots', 'assists', 'pass_accuracy']].copy()
                display_history['competition_name'] = display_history['competition_name'].apply(format_competition_name)
                st.dataframe(
                    display_history,
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("No match history available")
        else:
            st.warning(f"No statistics found for {selected_player}")
