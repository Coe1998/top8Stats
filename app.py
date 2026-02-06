import streamlit as st
import pandas as pd
import cloudscraper
from io import StringIO

# --- PAGE SETUP ---
st.set_page_config(page_title="Pauper Meta-Breaker", layout="wide", page_icon="🏆")

# --- DATA ENGINE ---
def process_html_to_df(html_text):
    """Shared logic to clean HTML into our tournament dataframe."""
    try:
        tables = pd.read_html(StringIO(html_text))
        if not tables: return None
        df = tables[0]
        
        # 1. Clean Headers
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
        df.rename(columns={df.columns[0]: 'Deck'}, inplace=True)
        df.columns = [c.split('_')[0] if '_' in c and c != 'Deck' else c for c in df.columns]
        
        # 2. Clean numeric data
        def clean_val(v):
            if pd.isna(v) or v == "-" or v == "": return 0.0
            return float(str(v).split('%')[0].strip()) if isinstance(v, str) else v
            
        for col in df.columns[1:]:
            df[col] = df[col].apply(clean_val)
        return df
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None

@st.cache_data(ttl=3600)
def scrape_data_automatically():
    # Use a high-fidelity browser fingerprint
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    try:
        response = scraper.get("https://mtgdecks.net/Pauper/winrates", timeout=15)
        if response.status_code == 200:
            return process_html_to_df(response.text)
        return None
    except:
        return None

# --- APP UI ---
st.title("🏆 Pauper Meta-Breaker")

# Use a sidebar for data loading options
st.sidebar.header("Data Source")
data_mode = st.sidebar.radio("Choose how to load data:", ["Auto-Scrape", "Manual Upload"])

data = None

if data_mode == "Auto-Scrape":
    data = scrape_data_automatically()
    if data is None:
        st.warning("⚠️ Auto-scrape blocked by Cloudflare. Please use 'Manual Upload' below.")

if data_mode == "Manual Upload" or data is None:
    st.info("To bypass blocks: Go to MTGDecks.net, right-click 'Save Page As', and upload the HTML file here.")
    uploaded_file = st.file_uploader("Upload MTGDecks HTML file", type=['html', 'htm'])
    if uploaded_file:
        html_content = uploaded_file.read().decode("utf-8")
        data = process_html_to_df(html_content)

# --- ANALYSIS SECTION ---
if data is not None:
    all_decks = sorted(data['Deck'].unique().tolist())
    selected_opps = st.multiselect("Select Expected Top 8 Decks:", options=all_decks)

    if selected_opps:
        data['Meta_Score'] = data[selected_opps].mean(axis=1)
        data['Win_Count'] = (data[selected_opps] > 50).sum(axis=1)
        
        results = data.sort_values(by=['Meta_Score'], ascending=False)
        
        st.subheader("Top Picks for this Meta")
        st.dataframe(results[['Deck', 'Meta_Score', 'Win_Count'] + selected_opps], hide_index=True)
