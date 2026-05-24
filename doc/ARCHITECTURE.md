# Architecture Overview

## High-Level Design

```
Browser (Streamlit UI)
        │
        ▼
fifa_dashboard_bq.py          ← Entry point: page config + tab routing
        │
        ├── tabs/competition_tab.py   ← 🏆 Competition Analysis
        ├── tabs/match_tab.py         ← ⚔️ Match Analysis
        ├── tabs/team_tab.py          ← 🛡️ Team Analysis
        └── tabs/player_tab.py        ← 👤 Player Analysis
                │
                ├── data_loader.py           ← Data fetching layer
                ├── fifa_metrics_bq.py       ← Metric calculations
                └── fifa_visualizations_bq.py ← Viz facade
                            │
                    ┌───────┴───────┐
                    │               │
            static_viz_bq.py   interactive_viz_bq.py
            (Matplotlib /       (Plotly charts)
             mplsoccer)
                    │               │
                    └───────┬───────┘
                            │
                    bigquery_helpers.py      ← BQ client + query execution
                            │
                    Google BigQuery
              midyear-castle-328020.fifa_data.events
```

---

## Module Responsibilities

### `fifa_dashboard_bq.py`
- Configures Streamlit page (`set_page_config`)
- Loads `style.css` for dark-theme styling
- Creates the BigQuery client (once, via `@st.cache_resource`)
- Creates the 4 tabs and delegates rendering to the `tabs/` modules
- No business logic or query code

### `tabs/*.py`
Each tab module exports a single `render_*_tab(client)` function:
- Owns the UI layout for that tab (selectors, columns, expanders)
- Calls `data_loader.py` functions to fetch data
- Calls visualization functions from `static_viz_bq.py` / `interactive_viz_bq.py`
- No raw SQL

### `data_loader.py`
High-level data access functions consumed by tabs:

| Function | Returns |
|----------|---------|
| `get_competitions(client)` | DataFrame of competitions + match counts |
| `get_teams(client, competition)` | DataFrame of teams |
| `get_matches(client, competition, team)` | DataFrame of matches with team names |
| `get_team_stats(client, team, competition)` | Dict of team metrics |
| `get_match_comparison_stats(client, match_id)` | Dict of stats for both teams |
| `get_player_stats(client, player, team)` | Dict of player metrics |
| `format_competition_name(slug)` | Human-readable name from slug |

### `bigquery_helpers.py`
Low-level BigQuery utilities:

| Function | Purpose |
|----------|---------|
| `get_bigquery_client()` | `@st.cache_resource` — BQ client singleton |
| `execute_query(client, query, params)` | Wrapper that computes `params_hash` then calls `run_query` |
| `run_query(_client, query, _params, hash)` | `@st.cache_data(ttl=600)` — executes and caches query |
| `build_where_clause(...)` | Returns `(sql_str, [QueryParameter])` tuple |
| `_params_to_hashable(params)` | Converts param list → stable string for cache key |

### `fifa_metrics_bq.py`
Domain-specific metric calculations:
- `analyze_team_passes()` — pass completion, under-pressure stats
- `analyze_team_shots()` — xG, shot outcomes, accuracy
- `analyze_team_defense()` — tackles, blocks, clearances
- `analyze_player_metrics()` — individual player performance
- `calculate_radar_boundaries()` — min/max for radar chart normalization

### `fifa_visualizations_bq.py` (Facade)
Exists only to re-export functions from `static_viz_bq` and `interactive_viz_bq`. Code that imports from this module doesn't need to know which sub-module a function lives in.

### `static_viz_bq.py`
Matplotlib + mplsoccer visualizations (returned as `(fig, ax)` or `fig`):
- `create_shot_map()` — pitch with shot scatter (size = xG, color = outcome)
- `create_team_radar_chart()` — normalized 0-100 spider chart
- `create_pass_network()` — pass flow arrows on pitch
- `create_touch_heatmap()` — kernel density heat map
- `plot_xg_distribution()` — histogram/KDE of xG values
- `plot_pressure_events()` — pressure heatmap on pitch
- `plot_attacking_passes()` — 4-panel: crosses, cutbacks, switches, through balls

### `interactive_viz_bq.py`
Plotly visualizations (returned as `go.Figure`):
- `create_interactive_pressure_heatmap()` — multi-team pressure density
- `create_interactive_pressure_passing_comparison()` — passing under pressure bar chart
- `create_interactive_shot_map()` — hover-enabled shot scatter
- `create_interactive_radar_chart()` — polar chart with hover
- `create_interactive_touch_heatmap()` — density heat map with zoom
- `create_interactive_xg_distribution()` — xG histogram with animation
- `create_xg_distribution_comparison()` — side-by-side xG comparison

---

## Data Flow for a Typical User Action

**Example: User selects "Argentina" in Team Analysis tab**

1. `team_tab.py` receives team name from `st.selectbox`
2. Calls `data_loader.get_team_stats(client, team="Argentina")`
3. `data_loader` calls `execute_query(client, query, params=[ScalarQueryParameter("team", "STRING", "Argentina")])`
4. `execute_query` converts params → `params_hash = "team:STRING:Argentina"`
5. `run_query` checks Streamlit cache — on miss, sends parameterized query to BigQuery
6. BigQuery returns DataFrame → cached for 600s
7. `team_tab.py` calls `create_team_radar_chart(client, "Argentina")` → `static_viz_bq.py`
8. Returns `fig` → rendered with `st.pyplot(fig)` or `st.image(fig_to_image(fig))`

---

## SQL Safety Model

All user-controlled values (team names, competition names, match IDs) are passed as `bigquery.QueryParameter` objects — never interpolated into SQL strings.

```python
# Safe ✅
params = [bigquery.ScalarQueryParameter("team", "STRING", user_input)]
query = "SELECT * FROM {{TABLE}} WHERE team = @team"

# Never do this ❌
query = f"SELECT * FROM {{TABLE}} WHERE team = '{user_input}'"
```

The `{{TABLE}}` placeholder is resolved server-side in `run_query()` before execution.

> **Why this matters for BigQuery specifically:** The common MySQL escaping trick of doubling single quotes (`''`) is invalid in BigQuery Standard SQL. For example, `WHERE team = 'Côte d''Ivoire'` causes a syntax error because BigQuery interprets `d''Ivoire` as two adjacent string literals without whitespace. Parameterized queries sidestep this entirely — BigQuery handles all escaping internally.

---

## Caching Strategy

| Level | Mechanism | Scope |
|-------|-----------|-------|
| BigQuery client | `@st.cache_resource` | Singleton per server process |
| Query results | `@st.cache_data(ttl=600)` | Per unique (query, params_hash) |
| Font objects | Module-level variables | Loaded once on import |

The `params_hash` pattern solves Streamlit's inability to hash `list[QueryParameter]`:
- The list (`_query_params`) is prefixed with `_` → excluded from Streamlit's auto-hash
- `params_hash` (a plain string) is passed as a separate argument → used as the cache key

---

## Deployment

Containerized with Docker (Python 3.11-slim), deployed to Google Cloud Run.

See `doc/DEPLOYMENT_AND_PERFORMANCE.md` for full deploy instructions.
