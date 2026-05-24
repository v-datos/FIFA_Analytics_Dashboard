# Dashboard Enhancement Plan — Status Tracker

> This document tracks the original enhancement plan and its current implementation status.
> For the current architecture, see `ARCHITECTURE.md`.

---

## ✅ Phase 1 — Completed

### Infrastructure & Architecture
- [x] **Modular tab architecture** — `tabs/competition_tab.py`, `tabs/match_tab.py`, `tabs/team_tab.py`, `tabs/player_tab.py`
- [x] **Visualization split** — `static_viz_bq.py` (Matplotlib/mplsoccer) + `interactive_viz_bq.py` (Plotly)
- [x] **Facade module** — `fifa_visualizations_bq.py` re-exports from both viz modules
- [x] **Data loader** — `data_loader.py` centralizes all high-level data fetching
- [x] **SQL injection protection** — `escape_sql_string` removed; parameterized queries everywhere
- [x] **Streamlit cache fix** — `_query_params` + `params_hash` pattern for `list` params
- [x] **Dark theme UI** — `style.css` with dark background, card styling, custom typography
- [x] **Competition name formatting** — slug → human-readable (e.g., `african_cup_of_nations_2023_male` → `African Cup Of Nations 2023`)
- [x] **Match selectbox** — shows "Team A vs Team B" instead of raw match IDs
- [x] **Cloud Run deployment** — Dockerized with Python 3.11-slim, deployed to `us-central1`

### Tab 3: 🛡️ Team Analysis
- [x] Team performance radar chart (0-100 normalized)
- [x] Shot map with xG
- [x] Attacking passes visualization (crosses, cutbacks, switches, through balls)
- [x] xG distribution plots
- [x] Passing under pressure analysis

### Tab 2: ⚔️ Match Analysis
- [x] Shot maps comparison (both teams)
- [x] Touch heatmap comparison
- [x] xG distribution comparison
- [x] Match team stats side-by-side

### Tab 1: 🏆 Competition Analysis
- [x] Competition-wide pressure events heatmap
- [x] Pressure passing comparison chart
- [x] Top scorers table
- [x] Key competition metrics

### Tab 4: 👤 Player Analysis
- [x] Individual shot map
- [x] Player stats (goals, assists, xG, pass accuracy)
- [x] Passing under pressure scatter plot

---

## 🔄 Phase 2 — In Progress / Planned

### Tab 1: 🏆 Competition Analysis
- [ ] xG timeline chart across all matches
- [ ] Statistical distributions (violin plots for metric comparisons)
- [ ] Average shots per match metric

### Tab 2: ⚔️ Match Analysis
- [ ] Pass network visualization (arrow maps by half)
- [ ] Progressive actions (passes/carries into final third)
- [ ] Match timeline — xG accumulation by minute with goal/card markers
- [ ] Possession % by pitch zone

### Tab 3: 🛡️ Team Analysis
- [ ] Defensive metrics section (shots against, progression against)
- [ ] Goalkeeper pass length distribution

### Tab 4: 👤 Player Analysis
- [ ] Position-specific radar charts (forward/midfielder/defender presets)
- [ ] Player pass map
- [ ] Player heat map (touch locations)
- [ ] Performance over time (stats per match line chart)
- [ ] Player comparison mode (2-player side-by-side)
- [ ] Goals per 90, Assists per 90, xG per shot

### New Tab 5: 📊 Advanced Analytics (Planned)
- [ ] Multi-team comparison radar overlays
- [ ] Playing style clusters (scatter: pass completion % vs through ball %)
- [ ] Pressure analysis dashboard
- [ ] Set piece analysis (corners, free kicks)

---

## 🚀 Phase 3 — Deployment & Performance (Completed)

- [x] Dockerfile (Python 3.11-slim, libgomp1, headless mode)
- [x] Cloud Run deployment (manual `gcloud` commands)
- [x] Google Cloud SDK at `~/google-cloud-sdk/`
- [x] **Data pre-aggregation** — `team_match_summary` / `player_stats_summary` BigQuery tables
- [x] **CI/CD pipeline** — Auto-build on push to `main` via Cloud Build triggers
- [x] **IAM-based auth** — Replace service account JSON key with Secret Manager/ADC

---

## 🎨 Design System (Implemented)

| Element | Value |
|---------|-------|
| Background | `#0e1117` (dark) |
| Card background | `#1c2128` |
| Primary accent | `#1f77b4` (blue) |
| Secondary accent | `#ff7f0e` (orange) |
| Success | `#2ca02c` (green) |
| Danger | `#d62728` (red) |
| Title font | `Play-Bold.ttf` |
| Body font | `Play-Regular.ttf` |
| Pitch viz library | `mplsoccer` |
| Interactive charts | `Plotly` |
| Static charts | `Matplotlib` + `Seaborn` |
