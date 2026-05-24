import streamlit as st
from bigquery_helpers import get_bigquery_client
from tabs.competition_tab import render_competition_tab
from tabs.match_tab import render_match_tab
from tabs.team_tab import render_team_tab
from tabs.player_tab import render_player_tab

# Page Configuration
st.set_page_config(
    page_title="Football Analytics Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS from external file
def load_custom_css():
    try:
        with open("style.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback if style.css is missing
        st.markdown("<style>@import url('https://fonts.googleapis.com/css2?family=Play:wght@400;700&display=swap');</style>", unsafe_allow_html=True)

def main():
    load_custom_css()

    # Get BigQuery client
    client = get_bigquery_client()

    if client is None:
        st.error("Failed to connect to BigQuery. Please check your credentials.")
        return

    # Header
    st.markdown("""
        <div class="team-header">
            <h1 style="margin:0 0 6px 0;">⚽ Football Analytics Dashboard</h1>
            <p style="margin:0; opacity:0.8; font-size:0.95rem;">Powered by StatsBomb Event Data</p>
        </div>
    """, unsafe_allow_html=True)

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Competition Analysis",
        "⚔️ Match Analysis",
        "🛡️ Team Analysis",
        "👤 Player Analysis"
    ])

    # Tab 1: Competition Analysis
    with tab1:
        render_competition_tab(client)

    # Tab 2: Match Analysis
    with tab2:
        render_match_tab(client)

    # Tab 3: Team Analysis
    with tab3:
        render_team_tab(client)

    # Tab 4: Player Analysis
    with tab4:
        render_player_tab(client)

if __name__ == "__main__":
    main()
