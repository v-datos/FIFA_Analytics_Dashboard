"""
BigQuery Helper Functions for FIFA Dashboard
Provides utility functions for BigQuery queries and connections
"""

import streamlit as st
import pandas as pd
import google.auth
from google.oauth2 import service_account
from google.cloud import bigquery
import time
import logging

# Configure logger for performance monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fifa_dashboard")

# BigQuery Configuration
BIGQUERY_TABLE = "midyear-castle-328020.fifa_data.events"


@st.cache_resource
def get_bigquery_client():
    """Create and cache BigQuery client using Streamlit secrets or ADC."""
    try:
        # Try to use local secrets if available
        if "gcp_service_account" in st.secrets:
            creds_info = st.secrets["gcp_service_account"]
            credentials = service_account.Credentials.from_service_account_info(creds_info)
            return bigquery.Client(credentials=credentials, project=credentials.project_id)
    except Exception:
        pass  # Fall through to ADC

    try:
        # Fallback to Application Default Credentials (IAM-based)
        # This will be used when deployed to Cloud Run
        credentials, project_id = google.auth.default()
        return bigquery.Client(
            credentials=credentials,
            project=project_id or "midyear-castle-328020",
        )
    except Exception as e:
        st.error(f"Failed to connect to BigQuery: {str(e)}")
        return None


def _params_to_hashable(params):
    """Convert a list of BigQuery query parameters to a hashable string for cache keying."""
    if not params:
        return None
    parts = []
    for p in params:
        if hasattr(p, 'name') and hasattr(p, 'value'):
            value_str = f"[{','.join(str(v) for v in p.value)}]" if isinstance(p.value, list) else str(p.value)
            parts.append(f"{p.name}:{p.type_}:{value_str}")
    return "|".join(sorted(parts))


def execute_query(client, query, query_params=None):
    """Convenience wrapper — converts params to a hashable key then calls run_query."""
    params_hash = _params_to_hashable(query_params)
    return run_query(client, query, query_params, params_hash)


@st.cache_data(ttl=600)
def run_query(_client, query, _query_params=None, params_hash=None):
    """
    Execute BigQuery query and return results as DataFrame.

    Args:
        _client: BigQuery client (prefixed _ = excluded from cache key)
        query: SQL query string
        _query_params: Optional list of BigQuery query parameters (prefixed _ = excluded from cache key)
        params_hash: Hashable string representation of _query_params (used as cache key)

    Returns:
        pandas.DataFrame with query results
    """
    if _client is None:
        return pd.DataFrame()

    start_time = time.time()
    try:
        # Replace placeholder if present, otherwise fallback to safe substitution
        if "{{TABLE}}" in query:
            query = query.replace("{{TABLE}}", f"`{BIGQUERY_TABLE}`")
        else:
            # Qualify unqualified references to the events table using a more robust regex
            # This handles 'FROM {{TABLE}}' and 'JOIN {{TABLE}}' while avoiding accidental replacements
            import re
            query = re.sub(r"(\bFROM\s+)events\b", f"\\1`{BIGQUERY_TABLE}`", query, flags=re.IGNORECASE)
            query = re.sub(r"(\bJOIN\s+)events\b", f"\\1`{BIGQUERY_TABLE}`", query, flags=re.IGNORECASE)

        # Execute with or without parameters
        if _query_params:
            job_config = bigquery.QueryJobConfig(query_parameters=_query_params)
            query_job = _client.query(query, job_config=job_config)
        else:
            query_job = _client.query(query)

        df = query_job.to_dataframe()
        
        execution_time = time.time() - start_time
        logger.info(f"Query executed in {execution_time:.3f} seconds. Size: {len(df)} rows. Params hash: {params_hash}")
        
        return df
    except Exception as e:
        st.error(f"BigQuery Error: {str(e)}")
        st.code(query)
        logger.error(f"Query failed after {time.time() - start_time:.3f} seconds: {str(e)}")
        return pd.DataFrame()




def build_where_clause(team=None, competition=None, match_id=None, player=None, event_types=None):
    """
    Build SQL WHERE clause and parameters from optional filters.
    Returns: (where_clause, params)
    """
    conditions = []
    params = []

    if team:
        conditions.append("team = @team")
        params.append(bigquery.ScalarQueryParameter("team", "STRING", team))

    if competition:
        conditions.append("competition_name = @competition")
        params.append(bigquery.ScalarQueryParameter("competition", "STRING", competition))

    if match_id:
        conditions.append("match_id = @match_id")
        params.append(bigquery.ScalarQueryParameter("match_id", "INT64", int(match_id)))

    if player:
        conditions.append("player = @player")
        params.append(bigquery.ScalarQueryParameter("player", "STRING", player))

    if event_types:
        conditions.append("type IN UNNEST(@event_types)")
        params.append(bigquery.ArrayQueryParameter("event_types", "STRING", event_types))

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params
