# BigQuery Setup Status

## ✅ All Setup Tasks Complete

**Last verified:** 2026-04-07

---

## Schema Verification

Verified live against `midyear-castle-328020.fifa_data.events`:

| Column | Type | Status |
|--------|------|--------|
| `shot_statsbomb_xg` | FLOAT64 | ✅ Correct |
| `pass_cross` | BOOLEAN | ✅ Correct |
| `pass_cut_back` | BOOLEAN | ✅ Correct |
| `pass_switch` | BOOLEAN | ✅ Correct |
| `under_pressure` | BOOLEAN | ✅ Correct |
| `x` | FLOAT64 | ✅ Correct |
| `y` | FLOAT64 | ✅ Correct |
| `duration` | FLOAT64 | ✅ Correct |

No schema changes required. All columns are the correct types.
The `SAFE_CAST()` guards in queries are retained as defensive practice.

---

## Connection Setup

Authentication is handled via a GCP service account stored in `.streamlit/secrets.toml`:

```python
# bigquery_helpers.py
@st.cache_resource
def get_bigquery_client():
    creds_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)
    return client
```

The `@st.cache_resource` decorator ensures the client is created once per session (not per query).

---

## BigQuery Table Reference

```
midyear-castle-328020.fifa_data.events
```

All queries use the `{{TABLE}}` placeholder which is resolved at runtime:

```python
query = "SELECT * FROM {{TABLE}} WHERE ..."
# Resolved to:
# SELECT * FROM `midyear-castle-328020.fifa_data.events` WHERE ...
```

---

## File Architecture (Current)

### Core Files

| File | Purpose |
|------|---------|
| `fifa_dashboard_bq.py` | Main Streamlit entry point; tab routing |
| `bigquery_helpers.py` | BQ client, `execute_query()`, `build_where_clause()` |
| `data_loader.py` | High-level data functions (`get_matches`, `get_teams`, etc.) |
| `fifa_metrics_bq.py` | Metric calculations (xG, passes, shots, defense) |
| `fifa_visualizations_bq.py` | Facade re-exporting from static + interactive modules |
| `static_viz_bq.py` | Matplotlib/mplsoccer visualizations |
| `interactive_viz_bq.py` | Plotly interactive charts |

### Tab Modules

| File | Tab |
|------|-----|
| `tabs/competition_tab.py` | 🏆 Competition Analysis |
| `tabs/match_tab.py` | ⚔️ Match Analysis |
| `tabs/team_tab.py` | 🛡️ Team Analysis |
| `tabs/player_tab.py` | 👤 Player Analysis |

### Config & Deployment

| File | Purpose |
|------|---------|
| `.streamlit/secrets.toml` | Service account credentials **(gitignored — never commit)** |
| `.streamlit/secrets.toml.example` | Safe template for new environments |
| `Dockerfile` | Python 3.11-slim container for Cloud Run |
| `requirements.txt` | Python dependencies |
| `.gitignore` / `.dockerignore` | Excludes secrets and venv |

---

## Query Safety Guarantees

- **Parameterized queries everywhere** — `bigquery.ScalarQueryParameter` / `bigquery.ArrayQueryParameter`
- **`escape_sql_string` removed** — no string interpolation of user input
- **`SAFE_CAST()` / `SAFE_DIVIDE()`** — prevents runtime errors on NULL / type mismatches
- **`@st.cache_data(ttl=600)`** on all queries; `params_hash` as the stable cache key

---

## Running Locally

```bash
cd ~/fifa_dashboard
streamlit run fifa_dashboard_bq.py
```

Requires `.streamlit/secrets.toml` with valid GCP service account credentials.
