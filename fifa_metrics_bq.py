"""
FIFA Dashboard Metrics Helper Functions - BigQuery Version
Adapted for BigQuery database queries on StatsBomb event data
"""

import pandas as pd
import numpy as np
import streamlit as st
from google.cloud import bigquery
from typing import Dict, Union, Optional, Tuple, List, Any
import warnings
warnings.filterwarnings('ignore')

from bigquery_helpers import run_query, BIGQUERY_TABLE


# ============================================================================
# PASSING METRICS
# ============================================================================

def analyze_team_passes(client: bigquery.Client, team: str,
                       competition: Optional[str] = None,
                       match_id: Optional[int] = None) -> Dict[str, Union[int, float]]:
    """
    Analyze passing statistics for a given team from BigQuery database.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client connection
    team : str
        Name of the team to analyze
    competition : str, optional
        Filter by competition name
    match_id : int, optional
        Filter by specific match

    Returns
    -------
    Dict[str, Union[int, float]]
        Dictionary containing passing metrics
    """
    # Build WHERE clause
    conditions = ["team = @team", "type = 'Pass'"]
    query_params = [bigquery.ScalarQueryParameter("team", "STRING", team)]

    if competition:
        conditions.append("competition_name = @competition")
        query_params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        conditions.append("match_id = @match_id")
        query_params.append(bigquery.ScalarQueryParameter("match_id", "INT64", match_id))

    where_clause = " AND ".join(conditions)

    # Query for pass metrics
    query = f"""
    SELECT
        COUNT(*) as total_passes,
        COUNT(DISTINCT match_id) as matches_played,
        COUNTIF(pass_outcome IS NULL) as completed_passes,
        COUNTIF(pass_cross = TRUE) as cross_passes,
        COUNTIF(pass_cut_back = TRUE) as cutback_passes,
        COUNTIF(pass_switch = TRUE) as switch_passes,
        COUNTIF(pass_through_ball = TRUE) as through_ball_passes,
        COUNTIF(pass_shot_assist = TRUE) as shot_assist_passes,
        COUNTIF(pass_goal_assist = TRUE) as goal_assist_passes,
        COUNTIF(under_pressure = TRUE) as under_pressure_passes,
        AVG(CASE WHEN position = 'Goalkeeper' THEN pass_length END) as goalkeeper_pass_avg_length
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    """

    result_df = run_query(client, query, query_params)
    if result_df.empty:
        return {
            'total_passes': 0, 'matches_played': 0, 'completed_passes': 0,
            'cross_passes': 0, 'cutback_passes': 0, 'switch_passes': 0,
            'through_ball_passes': 0, 'shot_assist_passes': 0, 'goal_assist_passes': 0,
            'under_pressure_passes': 0, 'goalkeeper_pass_avg_length': 0,
            'pass_completion_rate': 0, 'under_pressure_percentage': 0,
            'cross_percentage': 0, 'cutback_percentage': 0, 'through_ball_percentage': 0,
            'passes_per_match': 0
        }

    result = result_df.iloc[0].to_dict()

    # Calculate percentages
    total = result['total_passes']
    if total > 0:
        result['pass_completion_rate'] = (result['completed_passes'] / total) * 100
        result['under_pressure_percentage'] = (result['under_pressure_passes'] / total) * 100
        result['cross_percentage'] = (result['cross_passes'] / total) * 100
        result['cutback_percentage'] = (result['cutback_passes'] / total) * 100
        result['through_ball_percentage'] = (result['through_ball_passes'] / total) * 100
        result['passes_per_match'] = total / result['matches_played'] if result['matches_played'] > 0 else 0
    else:
        result.update({
            'pass_completion_rate': 0,
            'under_pressure_percentage': 0,
            'cross_percentage': 0,
            'cutback_percentage': 0,
            'through_ball_percentage': 0,
            'passes_per_match': 0
        })

    return result


# ============================================================================
# SHOOTING METRICS
# ============================================================================

def analyze_team_shots(client: bigquery.Client, team: str,
                      competition: Optional[str] = None,
                      match_id: Optional[int] = None) -> Dict[str, Union[int, float]]:
    """
    Analyze shooting statistics for a given team from BigQuery database.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client connection
    team : str
        Name of the team to analyze
    competition : str, optional
        Filter by competition name
    match_id : int, optional
        Filter by specific match

    Returns
    -------
    Dict[str, Union[int, float]]
        Dictionary containing shooting metrics
    """
    # Build WHERE clause
    conditions = ["team = @team", "type = 'Shot'"]
    query_params = [bigquery.ScalarQueryParameter("team", "STRING", team)]
    
    if competition:
        conditions.append("competition_name = @competition")
        query_params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        conditions.append("match_id = @match_id")
        query_params.append(bigquery.ScalarQueryParameter("match_id", "INT64", match_id))

    where_clause = " AND ".join(conditions)

    # Query for shot metrics
    query = f"""
    SELECT
        COUNT(DISTINCT match_id) as matches_played,
        COUNTIF(shot_type != 'Penalty') as total_shots,
        COUNTIF(shot_outcome IN ('Saved', 'Goal')) as shots_on_target,
        COUNTIF(shot_outcome = 'Goal') as goals,
        COUNTIF(shot_type = 'Open Play' AND play_pattern = 'From Counter') as counter_shots,
        COUNTIF(shot_type = 'Open Play' AND under_pressure = TRUE) as shots_under_pressure,
        SUM(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END) as total_xG,
        AVG(CASE WHEN shot_type = 'Open Play' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xG_open_play,
        AVG(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as non_penalty_avg_xG,
        AVG(CASE WHEN shot_type = 'Free Kick' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xG_set_piece
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    """

    result_df = run_query(client, query, query_params)
    if result_df.empty:
        return {
            'matches_played': 0, 'total_shots': 0, 'shots_on_target': 0, 'goals': 0,
            'counter_shots': 0, 'shots_under_pressure': 0, 'total_xG': 0,
            'avg_xG_open_play': 0, 'non_penalty_avg_xG': 0, 'avg_xG_set_piece': 0,
            'shots_per_match': 0, 'goals_per_match': 0, 'shots_on_target_percentage': 0,
            'goals_percentage': 0, 'counter_shots_percentage': 0, 'shots_under_pressure_percentage': 0,
            'xg_per_shot': 0, 'shooting_efficiency': 0, 'counter_shots_per_match': 0, 
            'shots_under_pressure_per_match': 0
        }

    result = result_df.iloc[0].to_dict()

    # Calculate percentages and per-match metrics
    total = result['total_shots']
    matches = result['matches_played']

    if total > 0:
        result['shots_on_target_percentage'] = (result['shots_on_target'] / total) * 100
        result['goals_percentage'] = (result['goals'] / total) * 100
        result['counter_shots_percentage'] = (result['counter_shots'] / total) * 100
        result['shots_under_pressure_percentage'] = (result['shots_under_pressure'] / total) * 100
        result['xg_per_shot'] = result['non_penalty_avg_xG']
    else:
        result.update({
            'shots_on_target_percentage': 0,
            'goals_percentage': 0,
            'counter_shots_percentage': 0,
            'shots_under_pressure_percentage': 0,
            'xg_per_shot': 0
        })

    if matches > 0:
        result['shots_per_match'] = total / matches
        result['goals_per_match'] = result['goals'] / matches
        result['counter_shots_per_match'] = result['counter_shots'] / matches
        result['shots_under_pressure_per_match'] = result['shots_under_pressure'] / matches
    else:
        result['shots_per_match'] = 0
        result['goals_per_match'] = 0
        result['counter_shots_per_match'] = 0
        result['shots_under_pressure_per_match'] = 0

    result['shooting_efficiency'] = result['goals'] / result['total_xG'] if result['total_xG'] > 0 else 0

    # Replace NaN values with 0
    result = {k: 0 if pd.isna(v) else v for k, v in result.items()}

    return result


# ============================================================================
# DEFENSIVE METRICS
# ============================================================================

def analyze_team_defense(client: bigquery.Client, team: str,
                        competition: Optional[str] = None,
                        match_id: Optional[int] = None) -> Dict[str, Union[int, float]]:
    """
    Analyze defensive statistics for a given team (shots against).

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client connection
    team : str
        Name of the team to analyze
    competition : str, optional
        Filter by competition name
    match_id : int, optional
        Filter by specific match

    Returns
    -------
    Dict[str, Union[int, float]]
        Dictionary containing defensive metrics
    """
    # First, get all matches where this team played
    match_conditions = ["team = @team"]
    query_params = [bigquery.ScalarQueryParameter("team", "STRING", team)]
    
    if competition:
        match_conditions.append("competition_name = @competition")
        query_params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    if match_id:
        match_conditions.append("match_id = @match_id")
        query_params.append(bigquery.ScalarQueryParameter("match_id", "INT64", match_id))

    match_where = " AND ".join(match_conditions)

    # Query for shots against (opponent shots in these matches)
    # Refactored to use a subquery/CTE to avoid fetching all match_ids
    query = f"""
    WITH match_list AS (
        SELECT DISTINCT match_id
        FROM {{{{TABLE}}}}
        WHERE {match_where}
    )
    SELECT
        (SELECT COUNT(*) FROM match_list) as matches_played,
        COUNTIF(shot_type != 'Penalty') as total_shots_against,
        COUNTIF(shot_outcome = 'Goal') as goals_conceded,
        SUM(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END) as total_xg_against,
        AVG(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xg_per_shot_against,
        AVG(CASE WHEN shot_outcome = 'Goal' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xg_goals_conceded
    FROM {{{{TABLE}}}}
    WHERE match_id IN (SELECT match_id FROM match_list)
        AND team != @team
        AND type = 'Shot'
    """
    
    result_df = run_query(client, query, query_params)
    if result_df.empty:
        return {
            'matches_played': 0,
            'total_shots_against': 0,
            'goals_conceded': 0,
            'goals_conceded_percentage': 0,
            'total_xg_against': 0,
            'avg_xg_per_shot_against': 0,
            'avg_xg_goals_conceded': 0,
            'shots_against_per_match': 0
        }

    result = result_df.iloc[0].to_dict()

    # Calculate percentages
    total = result['total_shots_against']
    matches = result['matches_played']

    if total > 0 and matches > 0:
        result['goals_conceded_percentage'] = (result['goals_conceded'] / total) * 100
        result['shots_against_per_match'] = total / matches
    else:
        result['goals_conceded_percentage'] = 0
        result['shots_against_per_match'] = 0

    # Replace NaN values with 0
    result = {k: 0 if pd.isna(v) else v for k, v in result.items()}

    return result


# ============================================================================
# COMPREHENSIVE TEAM METRICS
# ============================================================================

def analyze_team_metrics(client: bigquery.Client, team: str,
                        competition: Optional[str] = None,
                        match_id: Optional[int] = None,
                        return_dict: bool = True) -> Any:
    """
    Comprehensive analysis of a team's performance metrics using a single BigQuery call.
    Uses CTEs to combine passing, shooting, and defensive metrics for performance.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client connection
    team : str
        Name of the team to analyze
    competition : str, optional
        Filter by competition name
    match_id : int, optional
        Filter by specific match
    return_dict : bool, optional
        If True, returns a dictionary with all metrics, by default True

    Returns
    -------
    Union[Dict[str, Dict], None]
        Dictionary containing passing, shooting, and defensive metrics
    """
    try:
        # Build base conditions for team matches
        match_conditions = ["team = @team"]
        query_params = [bigquery.ScalarQueryParameter("team", "STRING", team)]
        if competition:
            match_conditions.append("competition_name = @competition")
            query_params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
        if match_id:
            match_conditions.append("match_id = @match_id")
            query_params.append(bigquery.ScalarQueryParameter("match_id", "INT64", match_id))
        
        match_where = " AND ".join(match_conditions)

        # Combined query using CTEs
        query = f"""
        WITH match_list AS (
            SELECT DISTINCT match_id 
            FROM {{{{TABLE}}}} 
            WHERE {match_where}
        ),
        passing_stats AS (
            SELECT
                COUNT(*) as total_passes,
                COUNTIF(pass_outcome IS NULL) as completed_passes,
                COUNTIF(pass_cross = TRUE) as cross_passes,
                COUNTIF(pass_cut_back = TRUE) as cutback_passes,
                COUNTIF(pass_switch = TRUE) as switch_passes,
                COUNTIF(pass_through_ball = TRUE) as through_ball_passes,
                COUNTIF(pass_shot_assist = TRUE) as shot_assist_passes,
                COUNTIF(pass_goal_assist = TRUE) as goal_assist_passes,
                COUNTIF(under_pressure = TRUE) as under_pressure_passes,
                AVG(CASE WHEN position = 'Goalkeeper' THEN pass_length END) as goalkeeper_pass_avg_length
            FROM {{{{TABLE}}}}
            WHERE {match_where} AND type = 'Pass'
        ),
        shooting_stats AS (
            SELECT
                COUNTIF(shot_type != 'Penalty') as total_shots,
                COUNTIF(shot_outcome IN ('Saved', 'Goal')) as shots_on_target,
                COUNTIF(shot_outcome = 'Goal') as goals,
                COUNTIF(shot_type = 'Open Play' AND play_pattern = 'From Counter') as counter_shots,
                COUNTIF(shot_type = 'Open Play' AND under_pressure = TRUE) as shots_under_pressure,
                SUM(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END) as total_xG,
                AVG(CASE WHEN shot_type = 'Open Play' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xG_open_play,
                AVG(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as non_penalty_avg_xG,
                AVG(CASE WHEN shot_type = 'Free Kick' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xG_set_piece
            FROM {{{{TABLE}}}}
            WHERE {match_where} AND type = 'Shot'
        ),
        defense_stats AS (
            SELECT
                COUNTIF(shot_type != 'Penalty') as total_shots_against,
                COUNTIF(shot_outcome = 'Goal') as goals_conceded,
                SUM(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END) as total_xg_against,
                AVG(CASE WHEN shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xg_per_shot_against,
                AVG(CASE WHEN shot_outcome = 'Goal' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) END) as avg_xg_goals_conceded
            FROM {{{{TABLE}}}}
            WHERE match_id IN (SELECT match_id FROM match_list)
                AND team != @team
                AND type = 'Shot'
        )
        SELECT 
            (SELECT COUNT(*) FROM match_list) as matches_played,
            p.*, s.*, d.*
        FROM passing_stats p, shooting_stats s, defense_stats d
        """

        result_df = run_query(client, query, query_params)
        
        if result_df.empty:
            # Fallback to individual calls if combined query fails for some reason
            return {
                'passing': analyze_team_passes(client, team, competition, match_id),
                'shooting': analyze_team_shots(client, team, competition, match_id),
                'defensive': analyze_team_defense(client, team, competition, match_id)
            }

        row = result_df.iloc[0].to_dict()
        matches_played = row['matches_played']

        # Split results and calculate derived metrics
        # PASSING
        passing = {
            'total_passes': row['total_passes'],
            'completed_passes': row['completed_passes'],
            'cross_passes': row['cross_passes'],
            'cutback_passes': row['cutback_passes'],
            'switch_passes': row['switch_passes'],
            'through_ball_passes': row['through_ball_passes'],
            'shot_assist_passes': row['shot_assist_passes'],
            'goal_assist_passes': row['goal_assist_passes'],
            'under_pressure_passes': row['under_pressure_passes'],
            'goalkeeper_pass_avg_length': row['goalkeeper_pass_avg_length'],
            'matches_played': matches_played
        }
        
        if passing['total_passes'] > 0:
            passing['pass_completion_rate'] = (passing['completed_passes'] / passing['total_passes']) * 100
            passing['under_pressure_percentage'] = (passing['under_pressure_passes'] / passing['total_passes']) * 100
            passing['cross_percentage'] = (passing['cross_passes'] / passing['total_passes']) * 100
            passing['cutback_percentage'] = (passing['cutback_passes'] / passing['total_passes']) * 100
            passing['through_ball_percentage'] = (passing['through_ball_passes'] / passing['total_passes']) * 100
            passing['passes_per_match'] = passing['total_passes'] / matches_played if matches_played > 0 else 0
        else:
            passing.update({
                'pass_completion_rate': 0, 'under_pressure_percentage': 0, 'cross_percentage': 0,
                'cutback_percentage': 0, 'through_ball_percentage': 0, 'passes_per_match': 0
            })

        # SHOOTING
        shooting = {
            'total_shots': row['total_shots'],
            'shots_on_target': row['shots_on_target'],
            'goals': row['goals'],
            'counter_shots': row['counter_shots'],
            'shots_under_pressure': row['shots_under_pressure'],
            'total_xG': row['total_xG'],
            'avg_xG_open_play': row['avg_xG_open_play'],
            'non_penalty_avg_xG': row['non_penalty_avg_xG'],
            'avg_xG_set_piece': row['avg_xG_set_piece'],
            'matches_played': matches_played
        }

        if shooting['total_shots'] > 0:
            shooting['shots_on_target_percentage'] = (shooting['shots_on_target'] / shooting['total_shots']) * 100
            shooting['goals_percentage'] = (shooting['goals'] / shooting['total_shots']) * 100
            shooting['counter_shots_percentage'] = (shooting['counter_shots'] / shooting['total_shots']) * 100
            shooting['shots_under_pressure_percentage'] = (shooting['shots_under_pressure'] / shooting['total_shots']) * 100
            shooting['xg_per_shot'] = shooting['non_penalty_avg_xG']
            shooting['shots_per_match'] = shooting['total_shots'] / matches_played if matches_played > 0 else 0
            shooting['goals_per_match'] = shooting['goals'] / matches_played if matches_played > 0 else 0
            shooting['counter_shots_per_match'] = shooting['counter_shots'] / matches_played if matches_played > 0 else 0
            shooting['shots_under_pressure_per_match'] = shooting['shots_under_pressure'] / matches_played if matches_played > 0 else 0
            shooting['shooting_efficiency'] = shooting['goals'] / shooting['total_xG'] if shooting['total_xG'] > 0 else 0
        else:
            shooting.update({
                'shots_on_target_percentage': 0, 'goals_percentage': 0, 'counter_shots_percentage': 0,
                'shots_under_pressure_percentage': 0, 'xg_per_shot': 0, 'shots_per_match': 0,
                'goals_per_match': 0, 'counter_shots_per_match': 0, 'shots_under_pressure_per_match': 0,
                'shooting_efficiency': 0
            })

        # DEFENSIVE
        defensive = {
            'total_shots_against': row['total_shots_against'],
            'goals_conceded': row['goals_conceded'],
            'total_xg_against': row['total_xg_against'],
            'avg_xg_per_shot_against': row['avg_xg_per_shot_against'],
            'avg_xg_goals_conceded': row['avg_xg_goals_conceded'],
            'matches_played': matches_played
        }

        if defensive['total_shots_against'] > 0:
            defensive['goals_conceded_percentage'] = (defensive['goals_conceded'] / defensive['total_shots_against']) * 100
            defensive['shots_against_per_match'] = defensive['total_shots_against'] / matches_played if matches_played > 0 else 0
        else:
            defensive.update({'goals_conceded_percentage': 0, 'shots_against_per_match': 0})

        # Clean up NaNs and combine
        passing = {k: 0 if pd.isna(v) else v for k, v in passing.items()}
        shooting = {k: 0 if pd.isna(v) else v for k, v in shooting.items()}
        defensive = {k: 0 if pd.isna(v) else v for k, v in defensive.items()}

        metrics = {
            'passing': passing,
            'shooting': shooting,
            'defensive': defensive
        }

        if return_dict:
            return metrics
        else:
            # Print formatted output
            print(f"\n{'='*50}")
            print(f"COMPLETE ANALYSIS FOR {team.upper()}")
            print(f"{'='*50}\n")
            print("PASSING METRICS:")
            for key, value in metrics['passing'].items():
                print(f"  {key}: {value}")
            print("\nSHOOTING METRICS:")
            for key, value in metrics['shooting'].items():
                print(f"  {key}: {value}")
            print("\nDEFENSIVE METRICS:")
            for key, value in metrics['defensive'].items():
                print(f"  {key}: {value}")
            return None

    except Exception as e:
        print(f"Error analyzing {team}: {str(e)}")
        # Attempt fallback to individual calls if anything fails
        try:
            return {
                'passing': analyze_team_passes(client, team, competition, match_id),
                'shooting': analyze_team_shots(client, team, competition, match_id),
                'defensive': analyze_team_defense(client, team, competition, match_id)
            }
        except:
            return None


# ============================================================================
# RADAR CHART HELPER
# ============================================================================

def get_team_radar_stats(team_metrics: Dict[str, Dict]) -> list:
    """
    Extract metrics for radar chart visualization.
    Returns a list in the order required by the mplsoccer Radar chart.

    Parameters
    ----------
    team_metrics : Dict[str, Dict]
        Dictionary of team metrics from analyze_team_metrics

    Returns
    -------
    list
        List of statistics in order:
        [Non-penalty xG, Shots on target %, Shots per game, Counter shots per game,
         Set piece xG, Shots under pressure per game, Through ball %, GK pass length, Cross %]
    """
    shooting = team_metrics['shooting']
    passing = team_metrics['passing']

    return [
        shooting.get('non_penalty_avg_xG', 0),
        shooting.get('shots_on_target_percentage', 0),
        shooting.get('shots_per_match', 0),
        shooting.get('counter_shots_per_match', 0),
        shooting.get('avg_xG_set_piece', 0),
        shooting.get('shots_under_pressure_per_match', 0),
        passing.get('through_ball_percentage', 0),
        passing.get('goalkeeper_pass_avg_length', 0),
        passing.get('cross_percentage', 0)
    ]


@st.cache_data(ttl=3600)
def calculate_radar_boundaries(_client: bigquery.Client, competition: Optional[str] = None) -> Tuple[List[float], List[float]]:
    """
    Dynamically calculate min/max boundaries for radar chart metrics across all teams.
    Uses a single aggregated BigQuery query for optimal performance.

    Parameters
    ----------
    _client : bigquery.Client
        BigQuery client (underscore prefix for st.cache_data)
    competition : str, optional
        Filter by specific competition, or None for all competitions

    Returns
    -------
    Tuple[List[float], List[float]]
        (low, high) - lists of minimum and maximum values for each of the 9 radar metrics
    """
    # Build competition filter using parameterized query
    radar_params = []
    if competition:
        comp_filter = "AND competition_name = @competition"
        radar_params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))
    else:
        comp_filter = ""

    # Single query to get min/max for all metrics across all teams
    query = f"""
    WITH team_metrics AS (
        SELECT
            team,
            COUNT(DISTINCT match_id) as matches,

            -- Metric 1: Non-Penalty xG per game
            SAFE_DIVIDE(
                SUM(CASE WHEN type = 'Shot' AND shot_type != 'Penalty' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END),
                COUNT(DISTINCT match_id)
            ) as non_penalty_xg,

            -- Metric 2: Shots on Target %
            SAFE_DIVIDE(
                COUNTIF(type = 'Shot' AND shot_outcome IN ('Goal', 'Saved', 'Saved to Post')) * 100.0,
                NULLIF(COUNTIF(type = 'Shot'), 0)
            ) as shots_on_target_pct,

            -- Metric 3: Shots per Game
            SAFE_DIVIDE(COUNTIF(type = 'Shot'), COUNT(DISTINCT match_id)) as shots_per_game,

            -- Metric 4: Counter Attacking Shots per Game
            SAFE_DIVIDE(
                COUNTIF(type = 'Shot' AND play_pattern = 'From Counter'),
                COUNT(DISTINCT match_id)
            ) as counter_shots_per_game,

            -- Metric 5: Set Piece xG per game
            SAFE_DIVIDE(
                SUM(CASE WHEN type = 'Shot' AND play_pattern IN ('From Corner', 'From Free Kick')
                    THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END),
                COUNT(DISTINCT match_id)
            ) as set_piece_xg,

            -- Metric 6: Shots Under Pressure per Game
            SAFE_DIVIDE(
                COUNTIF(type = 'Shot' AND under_pressure = TRUE),
                COUNT(DISTINCT match_id)
            ) as shots_under_pressure_per_game,

            -- Metric 7: Through ball %
            SAFE_DIVIDE(
                COUNTIF(pass_through_ball = TRUE) * 100.0,
                NULLIF(COUNTIF(type = 'Pass'), 0)
            ) as through_ball_pct,

            -- Metric 8: GK Pass Length (avg)
            AVG(CASE WHEN position = 'Goalkeeper' AND type = 'Pass' AND pass_length IS NOT NULL
                THEN pass_length ELSE NULL END) as gk_pass_length,

            -- Metric 9: Cross %
            SAFE_DIVIDE(
                COUNTIF(pass_cross = TRUE) * 100.0,
                NULLIF(COUNTIF(type = 'Pass'), 0)
            ) as cross_pct

        FROM {{{{TABLE}}}}
        WHERE team IS NOT NULL
            {comp_filter}
        GROUP BY team
        HAVING matches >= 1
    )
    SELECT
        MIN(non_penalty_xg) as min_npxg, MAX(non_penalty_xg) as max_npxg,
        MIN(shots_on_target_pct) as min_sot, MAX(shots_on_target_pct) as max_sot,
        MIN(shots_per_game) as min_spg, MAX(shots_per_game) as max_spg,
        MIN(counter_shots_per_game) as min_counter, MAX(counter_shots_per_game) as max_counter,
        MIN(set_piece_xg) as min_sp_xg, MAX(set_piece_xg) as max_sp_xg,
        MIN(shots_under_pressure_per_game) as min_sup, MAX(shots_under_pressure_per_game) as max_sup,
        MIN(through_ball_pct) as min_tb, MAX(through_ball_pct) as max_tb,
        MIN(gk_pass_length) as min_gk, MAX(gk_pass_length) as max_gk,
        MIN(cross_pct) as min_cross, MAX(cross_pct) as max_cross
    FROM team_metrics
    """

    res_df = run_query(_client, query, radar_params)

    if res_df.empty:
        return [0.0]*9, [100.0]*9

    row = res_df.iloc[0]
    low = [row['min_npxg'], row['min_sot'], row['min_spg'], row['min_counter'],
           row['min_sp_xg'], row['min_sup'], row['min_tb'], row['min_gk'], row['min_cross']]
    high = [row['max_npxg'], row['max_sot'], row['max_spg'], row['max_counter'],
            row['max_sp_xg'], row['max_sup'], row['max_tb'], row['max_gk'], row['max_cross']]

    # Clean up NaNs
    low = [0.0 if pd.isna(v) else v for v in low]
    high = [1.0 if pd.isna(v) or v == 0 else v for v in high]

    # Add 5% padding to make visualization better (teams won't be at exact edges)
    padding_factor = 0.05
    low = [max(0, val - abs(val) * padding_factor) for val in low]
    high = [val + abs(val) * padding_factor for val in high]

    return low, high


def normalize_to_radar_scale(value: float, index: int, low_bounds: List[float], high_bounds: List[float]) -> float:
    """
    Normalize a metric value to a 0-100 scale based on dynamic boundaries.

    Parameters
    ----------
    value : float
        The raw metric value
    index : int
        Index of the metric in the radar list (0-8)
    low_bounds : List[float]
        List of minimum values for each metric
    high_bounds : List[float]
        List of maximum values for each metric

    Returns
    -------
    float
        Normalized value (0-100)
    """
    low = low_bounds[index]
    high = high_bounds[index]

    if high <= low:
        return 0.0

    normalized = ((value - low) / (high - low)) * 100
    return max(0.0, min(100.0, normalized))


# ============================================================================
# PLAYER METRICS
# ============================================================================

def analyze_player_metrics(client: bigquery.Client, player: str,
                          team: Optional[str] = None,
                          competition: Optional[str] = None) -> Dict[str, Union[int, float]]:
    """
    Analyze comprehensive player statistics.

    Parameters
    ----------
    client : bigquery.Client
        BigQuery client connection
    player : str
        Name of the player to analyze
    team : str, optional
        Filter by team name
    competition : str, optional
        Filter by competition name

    Returns
    -------
    Dict[str, Union[int, float]]
        Dictionary containing player metrics
    """
    # Use parameterized queries
    conditions = ["player = @player"]
    query_params = [bigquery.ScalarQueryParameter("player", "STRING", player)]

    if team:
        conditions.append("team = @team")
        query_params.append(bigquery.ScalarQueryParameter("team", "STRING", team))
    if competition:
        conditions.append("competition_name = @competition")
        query_params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))

    where_clause = " AND ".join(conditions)

    query = f"""
    WITH player_matches AS (
        SELECT 
            match_id,
            MAX(minute) - MIN(minute) as match_minutes
        FROM {{{{TABLE}}}}
        WHERE {where_clause}
        GROUP BY match_id
    )
    SELECT
        team,
        position,
        COUNT(DISTINCT match_id) as matches_played,
        (SELECT SUM(match_minutes) FROM player_matches) as total_minutes,
        -- Shooting Stats
        COUNTIF(type = 'Shot') as shots,
        COUNTIF(type = 'Shot' AND shot_outcome IN ('Goal', 'Saved')) as shots_on_target,
        COUNTIF(type = 'Shot' AND shot_outcome = 'Goal') as goals,
        SUM(CASE WHEN type = 'Shot' THEN SAFE_CAST(shot_statsbomb_xg AS FLOAT64) ELSE 0.0 END) as total_xg,
        -- Passing Stats
        COUNTIF(type = 'Pass') as passes,
        COUNTIF(type = 'Pass' AND pass_outcome IS NULL) as successful_passes,
        COUNTIF(pass_goal_assist = TRUE) as assists,
        -- Defensive Stats
        COUNTIF(type = 'Duel' AND duel_type = 'Tackle') as tackles,
        COUNTIF(type = 'Interception') as interceptions,
        COUNTIF(type = 'Foul Committed') as fouls,
        -- Disciplinary
        COUNTIF(foul_committed_card IN ('Yellow Card', 'Red Card')
              OR bad_behaviour_card IN ('Yellow Card', 'Red Card')) as cards
    FROM {{{{TABLE}}}}
    WHERE {where_clause}
    GROUP BY team, position
    """

    result = run_query(client, query, query_params)

    if not result.empty:
        player_stats = result.iloc[0].to_dict()

        # Calculate rates
        total_minutes = player_stats.get('total_minutes', 0)
        # Fallback to matches * 90 if total_minutes is 0 or too low
        matches = player_stats.get('matches_played', 0)
        if total_minutes < (matches * 10): # Heuristic: if avg < 10 mins, maybe data is missing
            total_minutes = matches * 90

        if total_minutes > 0:
            player_stats['goals_per_90'] = (player_stats.get('goals', 0) / total_minutes) * 90
            player_stats['assists_per_90'] = (player_stats.get('assists', 0) / total_minutes) * 90
            player_stats['actual_minutes_played'] = total_minutes
        else:
            player_stats['goals_per_90'] = 0
            player_stats['assists_per_90'] = 0
            player_stats['actual_minutes_played'] = 0

        passes = player_stats.get('passes', 0)
        if passes > 0:
            player_stats['pass_completion_rate'] = (player_stats.get('successful_passes', 0) / passes) * 100
        else:
            player_stats['pass_completion_rate'] = 0

        return player_stats
    else:
        return {}
