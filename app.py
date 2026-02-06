import streamlit as st
import pandas as pd
import cloudscraper
from io import StringIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pauper Meta-Breaker", layout="wide", page_icon="🏆")

# --- STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE (With Caching to prevent 403 blocks) ---
@st.cache_data(ttl=3600)
def get_mtg_data():
    # We tell cloudscraper to specifically impersonate a real Chrome browser
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    try:
        url = "https://mtgdecks.net/Pauper/winrates"
        response = scraper.get(url, timeout=15)
        
        if response.status_code == 403:
            st.error("Access Forbidden (403). The site is blocking the cloud server's IP.")
            return None
            
        if response.status_code != 200:
            return None
        
        # Load and clean as before
        df = pd.read_html(StringIO(response.text))[0]
        # ... (keep your existing cleaning logic here) ...
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- APP UI ---
st.title("🏆 Pauper Tournament Meta-Breaker")
st.write("Target your specific Top 8 and find the statistical winner.")

data = get_mtg_data()

if data is not None:
    # SIDEBAR: Tournament Setup
    st.sidebar.header("Tournament Setup")
    all_decks = sorted(data['Deck'].unique().tolist())
    
    selected_opponents = st.sidebar.multiselect(
        "Select your expected opponents:",
        options=all_decks,
        default=all_decks[:3] if len(all_decks) > 3 else None,
        help="Add the decks you expect to face in the Top 8."
    )

    if selected_opponents:
        # CALCULATION
        data['Meta_Score'] = data[selected_opponents].mean(axis=1)
        data['Bad_Matchups'] = (data[selected_opponents] < 45).sum(axis=1)
        data['Win_Count'] = (data[selected_opponents] > 50).sum(axis=1)
        
        results = data.sort_values(by=['Meta_Score', 'Bad_Matchups'], ascending=[False, True])
        best_deck = results.iloc[0]

        # TOP METRICS
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Top Recommended Deck", best_deck['Deck'])
        with col2:
            st.metric("Avg. Win Rate", f"{best_deck['Meta_Score']:.1f}%")
        with col3:
            st.metric("Matchup Coverage", f"{best_deck['Win_Count']}/{len(selected_opponents)}")

        # RESULTS TABLE
        st.subheader("Detailed Matchup Analysis")
        display_cols = ['Deck', 'Meta_Score', 'Bad_Matchups'] + selected_opponents
        st.dataframe(
            results[display_cols].style.background_gradient(cmap='RdYlGn', subset=selected_opponents),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("👈 Select at least one opponent in the sidebar to begin analysis.")
else:
    st.error("Could not retrieve data. The site might be down or blocking the request.")
