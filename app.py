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
# CUSTOM CSS
# =========================
st.markdown("""
<style>

/* Left Panel Scroll */
.airway-list {
    background-color: #111;
    padding: 10px;
    border-radius: 6px;
    max-height: 200px;
    overflow-y: auto;
}

/* Tile Style */
.tile {
    background-color: #0e1117;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
    height: 320px;
    overflow-y: auto;
    color: white;
}

/* Tile Title */
.tile-title {
    font-weight: bold;
    font-size: 16px;
    margin-bottom: 8px;
    color: #4CAF50;
}

/* Improve spacing */
.block-container {
    padding-top: 1rem;
}

</style>
""", unsafe_allow_html=True)

# =========================
# LAYOUT
# =========================
left, right = st.columns([1, 3])

# =========================
# SESSION STATE
# =========================
if "airways" not in st.session_state:
    st.session_state.airways = []

if "notam_text" not in st.session_state:
    st.session_state.notam_text = ""

# =========================
# LEFT PANEL
# =========================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    notam_input = st.text_area(
        "NOTAM Input",
        value=st.session_state.notam_text,
        height=220,
        placeholder="Paste NOTAM here...\nExample:\nAR16/Y299 CLSD...",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns(2)

    if col1.button("🚀 Parse"):
        st.session_state.notam_text = notam_input
        st.session_state.airways = extract_airways(notam_input)

    if col2.button("Clear"):
        st.session_state.notam_text = ""
        st.session_state.airways = []

    st.markdown("### ✅ Detected Airways")

    st.markdown('<div class="airway-list">', unsafe_allow_html=True)

    if st.session_state.airways:
        for a in st.session_state.airways:
            st.write(f"• {a}")
    else:
        st.write("No airways detected")

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RIGHT PANEL
# =========================
with right:
    st.markdown("## ✈️ Airway Details")

    airways = st.session_state.airways

    if airways:
        # Create grid (3 per row)
        for i in range(0, len(airways), 3):
            cols = st.columns(3)
            row_airways = airways[i:i+3]

            for col, airway in zip(cols, row_airways):
                with col:
                    if airway in df.index:
                        data = df.loc[[airway]]

                        html = f'<div class="tile">'
                        html += f'<div class="tile-title">{airway}</div>'

                        for _, r in data.iterrows():
                            html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                        html += "</div>"

                        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Paste NOTAM and click Parse to view airway tiles")
