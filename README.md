<p align="center">
  <img src="fifa_readme.png" width="100%" alt="FIFA Football Analytics Header">
</p>


# ⚽ FIFA Football Analytics Dashboard

A high-performance, interactive football analytics platform built with **Streamlit**. This dashboard transforms raw StatsBomb event data into professional-grade visualizations, powered by a **Google BigQuery** backend.

## 🚀 Features

The dashboard is divided into four specialized analysis modules:

- **🏆 Competition Analysis:** High-level tournament stats, top scorers, team-wide metric distributions, and pressure event comparisons.
- **⚔️ Match Analysis:** Deep dives into specific games including shot maps, pass networks, xG distributions, and team touch comparisons.
- **🛡️ Team Analysis:** Performance radar charts (0-100 normalized), xG distributions, attacking pass patterns, and shot maps.
- **👤 Player Analysis:** Individual performance metrics, shot maps, and passing efficiency under pressure.

## 🛠️ Technical Stack

- **Frontend:** [Streamlit](https://streamlit.io/)
- **Data Visualization:** [Plotly](https://plotly.com/python/), [Seaborn](https://seaborn.pydata.org/), [Matplotlib](https://matplotlib.org/)
- **Pitch Graphics:** [mplsoccer](https://mplsoccer.readthedocs.io/)
- **Database:** Google BigQuery (`midyear-castle-328020.fifa_data.events`)
- **Language:** Python 3.11+
- **Infrastructure:** Docker, Google Cloud Run

## 📁 Project Structure

```text
├── fifa_dashboard_bq.py          # Main entry point — page config + tab routing
├── data_loader.py                # Data fetching layer (get_matches, get_teams, etc.)
├── bigquery_helpers.py           # BigQuery connection, parameterized query execution
├── fifa_metrics_bq.py            # Advanced metrics (xG, pressure, pass analysis)
├── fifa_visualizations_bq.py     # Facade — re-exports static + interactive functions
├── static_viz_bq.py              # Static visualizations (Matplotlib, mplsoccer)
├── interactive_viz_bq.py         # Interactive visualizations (Plotly)
├── style.css                     # Dark-theme Streamlit UI styling
├── Play-Bold.ttf                 # Custom font (bold)
├── Play-Regular.ttf              # Custom font (regular)
├── Dockerfile                    # Container config for Cloud Run (Python 3.11-slim)
├── requirements.txt              # Python dependencies
│
├── tabs/                         # One module per dashboard tab
│   ├── competition_tab.py        # 🏆 Competition Analysis tab
│   ├── match_tab.py              # ⚔️ Match Analysis tab
│   ├── team_tab.py               # 🛡️ Team Analysis tab
│   └── player_tab.py             # 👤 Player Analysis tab
│
├── .streamlit/
│   ├── secrets.toml              # GCP service account credentials (gitignored)
│   └── secrets.toml.example      # Safe credential template
│
└── doc/                          # Project documentation
    ├── ARCHITECTURE.md           # Modular architecture overview
    ├── DEPLOYMENT_AND_PERFORMANCE.md  # Cloud Run deployment guide
    ├── SQL_ESCAPING_FIX.md       # History of SQL injection fix → parameterized queries
    ├── BIGQUERY_SETUP_STATUS.md  # Schema verification and setup status
    └── bigquery/                 # BigQuery-specific references
        ├── OPTIMIZATION_SUMMARY.md
        ├── radar.md
        └── radar_integration.md
```

## 🚦 Getting Started

### 1. Prerequisites
Ensure you have Python 3.11+ installed.

### 2. Installation
Clone the repository, create a virtual environment to keep dependencies isolated, and install them:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
To connect to the BigQuery backend, you need a GCP Service Account:
1. Create a `.streamlit/secrets.toml` file in the project root.
2. Add your GCP credentials in the following format:
```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "---BEGIN PRIVATE KEY---\n...\n---END PRIVATE KEY---\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

### 4. Running the Dashboard
```bash
streamlit run fifa_dashboard_bq.py
```

## 🚢 Deployment

The project is containerized and deployed to **Google Cloud Run**.

**Live URLs:**
- Main Dashboard: `https://fifa-dashboard-80399171028.us-central1.run.app`

**Build & Deploy:**
```bash
# Authenticate (user account with Cloud Build permissions)
gcloud auth login

# Set project
gcloud config set project midyear-castle-328020

# Build and push image
gcloud builds submit \
    --tag gcr.io/midyear-castle-328020/fifa-dashboard .

# Deploy to Cloud Run
gcloud run deploy fifa-dashboard \
    --image gcr.io/midyear-castle-328020/fifa-dashboard \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 3 \
    --cpu-throttling \
    --liveness-probe=httpGet.path=/_stcore/health,httpGet.port=8080
```

Refer to `doc/DEPLOYMENT_AND_PERFORMANCE.md` for full details.

## 📊 Key Metrics Explained

- **Expected Goals (xG):** Probability that a shot results in a goal based on historical data.
- **Passes Under Pressure:** Completion rate of passes made while an opponent is within ~3m.
- **Progressive Actions:** Actions that move the ball significantly closer to the opponent's goal.
- **Normalization:** Team stats are normalized (0-100) against the entire database for radar charts.

## 📝 Roadmap & Status

- [x] BigQuery Migration (Complete)
- [x] SQLite Removal (Complete)
- [x] Modular Tab Architecture — `tabs/` directory (Complete)
- [x] Static + Interactive Viz Split — `static_viz_bq.py` / `interactive_viz_bq.py` (Complete)
- [x] Interactive Radar Charts (Complete)
- [x] SQL Injection Protection — Parameterized queries throughout (Complete)
- [x] `escape_sql_string` fully removed — replaced by `bigquery.ScalarQueryParameter` (Complete)
- [x] Streamlit Caching Fix — `_query_params` + `params_hash` pattern (Complete)
- [x] Dark-theme UI with custom CSS (`style.css`) (Complete)
- [x] Competition name formatting — slug → human-readable (Complete)
- [x] Match selectbox — shows "Team A vs Team B" instead of match IDs (Complete)
- [x] Cloud Run Deployment (Complete)
- [x] Google Cloud SDK installed at `~/google-cloud-sdk/` (Complete)
- [x] Data Pre-Aggregation Summary Tables (Complete)
- [x] Automated CI/CD for Cloud Run (Complete)
- [x] IAM-based Auth for BigQuery (Complete)
- [ ] Match xG Timelines per minute (Planned)
- [ ] Goalkeeper Advanced Metrics (Planned)

## 📄 License

TODO: Add license information (e.g., MIT, Apache 2.0).

---
*Developed for advanced football scouting and data-driven storytelling.*
