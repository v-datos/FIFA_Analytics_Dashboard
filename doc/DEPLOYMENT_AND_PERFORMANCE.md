# 🚀 Deployment & Performance Guide

## 🌐 Live Services

| Dashboard | URL |
|-----------|-----|
| Main Dashboard | https://fifa-dashboard-80399171028.us-central1.run.app |

Both are deployed to **Google Cloud Run** in the `us-central1` region under GCP project `midyear-castle-328020`.

---

## 🛠️ Deployment Workflow

### Prerequisites

- Google Cloud SDK installed at `~/google-cloud-sdk/`
- Add to shell (already in `~/.zshrc`):
  ```bash
  if [ -f '~/google-cloud-sdk/path.zsh.inc' ]; then
      . '~/google-cloud-sdk/path.zsh.inc'
  fi
  ```
- Active user account: `vincent.frias@gmail.com` (has Cloud Build + Cloud Run permissions)
- The application uses IAM-based auth (`google.auth.default()`) in Cloud Run, so do not include `.streamlit/secrets.toml` in the deployment.

### Step 1: Authenticate

```bash
gcloud auth login
gcloud config set project midyear-castle-328020
```

### Step 2: Build Docker Image

```bash
cd ~/fifa_dashboard

gcloud builds submit \
    --tag gcr.io/midyear-castle-328020/fifa-dashboard .
```

This uses Cloud Build (remote) — no local Docker daemon required.

### Step 3: Deploy to Cloud Run

```bash
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

### Step 4: Verify

```bash
gcloud run services describe fifa-dashboard \
    --region us-central1 \
    --format="value(status.url)"
```

---

## 🐳 Dockerfile

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install system dependencies, install Python packages, and clean up in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8080
ENTRYPOINT ["streamlit", "run", "fifa_dashboard_bq.py", \
    "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
```

Key points:
- **Python 3.11-slim** base image
- `libgomp1` required by `mplsoccer` / OpenMP
- `--server.headless=true` suppresses browser-open attempts in the container

---

## ⚡ Performance Optimization

### Current State

The app queries the raw `events` table (1.1M+ rows) on every interaction. Caching (`@st.cache_data(ttl=600)`) reduces repeated hits for the same inputs, but cold loads can be 3-6 seconds.

### Caching Pattern

All BigQuery queries go through `run_query()` in `bigquery_helpers.py`:

```python
@st.cache_data(ttl=600)
def run_query(_client, query, _query_params=None, params_hash=None):
    ...
```

- `_client` and `_query_params` are prefixed with `_` → excluded from Streamlit's cache key
- `params_hash` (a deterministic string of param names/types/values) is used as the cache key instead
- TTL is 600 seconds (10 minutes)

### Recommended: Data Pre-Aggregation

Create summary tables in BigQuery to avoid scanning 1.1M rows on every request:

```sql
-- Team match summary (run once, refresh nightly)
CREATE OR REPLACE TABLE `midyear-castle-328020.fifa_data.team_match_summary` AS
SELECT
    match_id,
    team,
    competition_name,
    COUNTIF(type = 'Shot' AND shot_outcome = 'Goal')                                      AS goals,
    SUM(SAFE_CAST(shot_statsbomb_xg AS FLOAT64))                                          AS expected_goals,
    COUNTIF(type = 'Pass')                                                                 AS total_passes,
    SAFE_DIVIDE(
        COUNTIF(type = 'Pass' AND pass_outcome IS NULL),
        COUNTIF(type = 'Pass')
    ) * 100                                                                                AS pass_accuracy,
    COUNTIF(type = 'Pressure')                                                             AS pressure_events
FROM `midyear-castle-328020.fifa_data.events`
GROUP BY match_id, team, competition_name;
```

Expected impact: **70-80% reduction in dashboard load time** (32 rows vs 1.1M).

### Hosting Alternatives

| Option | Best For | Notes |
|--------|----------|-------|
| **Google Cloud Run** ✅ Current | GCP/BigQuery workloads | Serverless, scales to zero, same GCP network as BQ |
| Self-Hosting (VPS) | Full control | $5-10/mo on DigitalOcean; manual setup |
| AWS App Runner | AWS ecosystem | Similar to Cloud Run; more complex IAM |
| Heroku | Simplicity | Easy deploy; limited free tier |

Cloud Run is the best fit because it runs in the same GCP network as BigQuery, minimizing query latency and egress costs.

The deployed service keeps `--min-instances 0` and `--cpu-throttling` so idle instances do not keep billing CPU, and `--max-instances 3` caps runaway scale during unexpected traffic.

---

## 🔐 Credentials Management

| Credential | Location | Notes |
|------------|----------|-------|
| Local GCP Service Account | `.streamlit/secrets.toml` | Gitignored; optional for local development |
| Template | `.streamlit/secrets.toml.example` | Safe to commit; no real keys |
| gcloud user auth | System keychain | `vincent.frias@gmail.com` for Cloud Build/Run |
| Cloud Run runtime auth | Service account ADC | BigQuery read access through IAM |

**Never commit `.streamlit/secrets.toml`** — it contains a private key.

Inside Docker, secrets are injected via Cloud Run environment variables or Secret Manager (future improvement).

---

## 📋 Planned Improvements

- [x] **BigQuery Secret Manager** — Remove JSON key from container; use IAM-based auth
- [x] **Pre-aggregation tables** — `team_match_summary`, `player_stats_summary`
- [x] **CI/CD pipeline** — Auto-deploy on push to `main` via Cloud Build triggers
- [x] **Health check endpoint** — Add `/_stcore/health` monitoring in Cloud Run
