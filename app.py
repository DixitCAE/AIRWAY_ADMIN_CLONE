import streamlit as st
import pandas as pd
import re

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv", engine="python")
    df.columns = ["AWID", "WAYPOINT", "COUNTRY", "COORDS"]
    df["AWID"] = df["AWID"].astype(str).str.upper().str.strip()
    df.set_index("AWID", inplace=True)
    return df

df = load_data()
valid_airways = set(df.index.unique())

# =========================
# TEXT PROCESSING
# =========================
def normalize(text):
    text = text.upper()
    text = re.sub(r"[^A-Z0-9/ ]", " ", text)
    return text

def extract_airways(text):
    text = normalize(text)
    tokens = re.split(r"[ /]+", text)
    return sorted(set(tokens) & valid_airways)

# =========================
# CUSTOM CSS (IMPORTANT)
# =========================
st.markdown("""
<style>

.tile {
    background-color: #0e1117;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
    height: 320px;
    overflow-y: auto;
    color: white;
}

.tile-title {
    font-weight: bold;
    font-size: 16px;
    margin-bottom: 5px;
    color: #4CAF50;
}

.left-panel {
    border-right: 1px solid #333;
    padding-right: 10px;
}

.airway-list {
    background-color: #111;
    padding: 10px;
    border-radius: 6px;
    max-height: 200px;
    overflow-y: auto;
}

</style>
""", unsafe_allow_html=True)

# =========================
# LAYOUT
# =========================
left, right = st.columns([1, 3])

# =========================
# LEFT PANEL
# =========================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    notam_input = st.text_area("", height=200, placeholder="Paste NOTAM here...")

    col1, col2 = st.columns(2)
    parse_clicked = col1.button("🚀 Parse")
    clear_clicked = col2.button("Clear")

    if clear_clicked:
        notam_input = ""

    # placeholder for results
    if "airways" not in st.session_state:
        st.session_state.airways = []

    if parse_clicked:
        st.session_state.airways = extract_airways(notam_input)

    st.markdown("### ✅ Detected Airways")

    st.markdown('<div class="airway-list">', unsafe_allow_html=True)

    for a in st.session_state.airways:
        st.write(f"• {a}")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RIGHT PANEL (GRID)
# =========================
with right:
    st.markdown("## ✈️ Airway Details")

    airways = st.session_state.airways

    if airways:

        # chunk into rows of 3
        for i in range(0, len(airways), 3):
            row_airways = airways[i:i+3]
            cols = st.columns(3)

            for col, airway in zip(cols, row_airways):

                with col:

                    if airway in df.index:
                        data = df.loc[[airway]]

                        # HTML tile
                        html = f'<div class="tile">'
                        html += f'<div class="tile-title">{airway}</div>'

                        for _, r in data.iterrows():
                            html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                        html += "</div>"

                        st.markdown(html, unsafe_allow_html=True)

    else:
        st.info("Paste NOTAM and click Parse")
