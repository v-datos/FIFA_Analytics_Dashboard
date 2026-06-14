import streamlit as st
import pandas as pd
from google.cloud import bigquery
from bigquery_helpers import execute_query

def format_competition_name(name: str) -> str:
    """Convert raw competition names to display-friendly labels."""
    if not name or name == "All Competitions":
        return name
    return (
        name.replace('_', ' ')
            .replace(' male', '')
            .replace(' female', '')
            .strip()
            .title()
    )

@st.cache_data(ttl=600)
def get_competitions(_client, team=None):
    """Get list of competitions"""
    params = None
    if team:
        query = """
        SELECT DISTINCT competition_name, COUNT(DISTINCT match_id) as matches
        FROM `midyear-castle-328020.fifa_data.team_match_summary`
        WHERE team = @team
        GROUP BY competition_name
        ORDER BY competition_name
        """
        params = [bigquery.ScalarQueryParameter("team", "STRING", team)]
    else:
        query = """
        SELECT DISTINCT competition_name, COUNT(DISTINCT match_id) as matches
        FROM `midyear-castle-328020.fifa_data.team_match_summary`
        GROUP BY competition_name
        ORDER BY competition_name
        """
    return execute_query(_client, query, params)

@st.cache_data(ttl=600)
def get_teams(_client):
    """Get list of teams"""
    query = """
    SELECT DISTINCT team, COUNT(DISTINCT match_id) as matches
    FROM `midyear-castle-328020.fifa_data.team_match_summary`
    WHERE team IS NOT NULL
    GROUP BY team
    ORDER BY team
    """
    return execute_query(_client, query)

@st.cache_data(ttl=600)
def get_players(_client):
    """Get list of players"""
    query = """
    SELECT DISTINCT player, team
    FROM `midyear-castle-328020.fifa_data.player_stats_summary`
    WHERE player IS NOT NULL
    ORDER BY player
    """
    return execute_query(_client, query)

@st.cache_data(ttl=600)
def get_matches(_client, competition=None, team=None):
    """Get list of matches with filters"""
    conditions = []
    params = []

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if team:
        conditions.append("match_id IN (SELECT match_id FROM `midyear-castle-328020.fifa_data.team_match_summary` WHERE team = @team)")
        params.append(bigquery.ScalarQueryParameter("team", "STRING", team))

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT
        match_id,
        competition_name,
        MIN(match_start) as match_start,
        SUM(team_events) as total_events,
        STRING_AGG(DISTINCT team ORDER BY team LIMIT 2) as teams
    FROM `midyear-castle-328020.fifa_data.team_match_summary`
    WHERE {where_clause} AND team IS NOT NULL
    GROUP BY match_id, competition_name
    ORDER BY match_id
    """
    return execute_query(_client, query, params if params else None)

def get_team_stats(client, team_name, competition=None, match_id=None):
    """Get comprehensive team statistics"""
    conditions = ["team = @team"]
    params = [bigquery.ScalarQueryParameter("team", "STRING", team_name)]

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        conditions.append("match_id = @match_id")
        params.append(bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)))

    where_clause = " AND ".join(conditions)

    # Combined query for metrics and possession (if match_id provided)
    if match_id:
        query = f"""
        WITH team_metrics AS (
            SELECT
                team,
                SUM(shots) as shots,
                SUM(shots_on_target) as shots_on_target,
                SUM(goals) as goals,
                SUM(free_kick_goals) as free_kick_goals,
                SUM(headed_goals) as headed_goals,
                SUM(penalty_goals) as penalty_goals,
                SUM(total_xg) as total_xg,
                ROUND(SAFE_DIVIDE(
                    SUM(shots_on_target) * 100.0,
                    NULLIF(SUM(shots), 0)
                ), 2) as shot_accuracy,
                SUM(passes) as passes,
                SUM(successful_passes) as successful_passes,
                ROUND(SAFE_DIVIDE(
                    SUM(successful_passes) * 100.0,
                    NULLIF(SUM(passes), 0)
                ), 2) as pass_accuracy,
                SUM(tackles) as tackles,
                SUM(fouls_committed) as fouls_committed,
                SUM(corners) as corners,
                SUM(offsides) as offsides,
                SUM(yellow_cards) as yellow_cards,
                SUM(red_cards) as red_cards
            FROM `midyear-castle-328020.fifa_data.team_match_summary`
            WHERE {where_clause}
            GROUP BY team
        ),
        match_events AS (
            SELECT
                SUM(team_events) as total_match_events,
                SUM(CASE WHEN team = @team THEN team_events ELSE 0 END) as team_match_events
            FROM `midyear-castle-328020.fifa_data.team_match_summary`
            WHERE match_id = @match_id
        )
        SELECT 
            m.*,
            ROUND(SAFE_DIVIDE(e.team_match_events * 100.0, NULLIF(e.total_match_events, 0)), 2) as possession_pct
        FROM team_metrics m, match_events e
        """
    else:
        query = f"""
        SELECT
            team,
            SUM(shots) as shots,
            SUM(shots_on_target) as shots_on_target,
            SUM(goals) as goals,
            SUM(free_kick_goals) as free_kick_goals,
            SUM(headed_goals) as headed_goals,
            SUM(penalty_goals) as penalty_goals,
            SUM(total_xg) as total_xg,
            ROUND(SAFE_DIVIDE(
                SUM(shots_on_target) * 100.0,
                NULLIF(SUM(shots), 0)
            ), 2) as shot_accuracy,
            SUM(passes) as passes,
            SUM(successful_passes) as successful_passes,
            ROUND(SAFE_DIVIDE(
                SUM(successful_passes) * 100.0,
                NULLIF(SUM(passes), 0)
            ), 2) as pass_accuracy,
            SUM(tackles) as tackles,
            SUM(fouls_committed) as fouls_committed,
            SUM(corners) as corners,
            SUM(offsides) as offsides,
            SUM(yellow_cards) as yellow_cards,
            SUM(red_cards) as red_cards,
            0.0 as possession_pct
        FROM `midyear-castle-328020.fifa_data.team_match_summary`
        WHERE {where_clause}
        GROUP BY team
        """
    
    return execute_query(client, query, params)

def get_match_comparison_stats(client, team1, team2, match_id):
    """Get stats for both teams in a match"""
    params = [
        bigquery.ScalarQueryParameter("team1", "STRING", team1),
        bigquery.ScalarQueryParameter("team2", "STRING", team2),
        bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id))
    ]

    query = """
    WITH match_metrics AS (
        SELECT
            team,
            SUM(shots) as shots,
            SUM(shots_on_target) as shots_on_target,
            SUM(goals) as goals,
            SUM(passes) as passes,
            SUM(successful_passes) as successful_passes,
            ROUND(SAFE_DIVIDE(
                SUM(successful_passes) * 100.0,
                NULLIF(SUM(passes), 0)
            ), 2) as pass_accuracy,
            SUM(team_events) as team_events
        FROM `midyear-castle-328020.fifa_data.team_match_summary`
        WHERE match_id = @match_id AND team IN (@team1, @team2)
        GROUP BY team
    ),
    total_match_events AS (
        SELECT SUM(team_events) as total_events
        FROM `midyear-castle-328020.fifa_data.team_match_summary`
        WHERE match_id = @match_id
    )
    SELECT 
        m.*,
        ROUND(SAFE_DIVIDE(m.team_events * 100.0, NULLIF(e.total_events, 0)), 2) as possession_pct
    FROM match_metrics m, total_match_events e
    """
    
    df = execute_query(client, query, params)
    
    stats1 = df[df['team'] == team1].iloc[0] if not df[df['team'] == team1].empty else None
    stats2 = df[df['team'] == team2].iloc[0] if not df[df['team'] == team2].empty else None
    
    return stats1, stats2

def get_player_stats(client, player_name, team_name=None, competition=None):
    """Get comprehensive player statistics"""
    conditions = ["player = @player"]
    params = [bigquery.ScalarQueryParameter("player", "STRING", player_name)]

    if team_name:
        conditions.append("team = @team")
        params.append(bigquery.ScalarQueryParameter("team", "STRING", team_name))
    if competition:
        conditions.append("match_id IN (SELECT match_id FROM `midyear-castle-328020.fifa_data.team_match_summary` WHERE competition_name = @competition)")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))

    where_clause = " AND ".join(conditions)

    query = f"""
    SELECT
        player,
        team,
        -- Shooting Stats
        SUM(total_shots) as shots,
        SUM(shots_on_target) as shots_on_target,
        SUM(goals) as goals,
        SUM(xg) as total_xg,

        -- Passing Stats
        SUM(total_passes) as passes,
        SUM(successful_passes) as successful_passes,
        SUM(assists) as assists,

        -- Defensive Stats
        SUM(tackles) as tackles,
        SUM(interceptions) as interceptions,
        SUM(fouls_committed) as fouls,

        -- Disciplinary
        SUM(yellow_cards + red_cards) as cards

    FROM `midyear-castle-328020.fifa_data.player_stats_summary`
    WHERE {where_clause}
    GROUP BY player, team
    """
    return execute_query(client, query, params)
