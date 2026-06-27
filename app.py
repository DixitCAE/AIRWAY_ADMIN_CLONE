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
    return df

df = load_data()

# =========================
# PARSE COORDS
# =========================
def parse_coord(coord):
    try:
        lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
        if coord[6] == "S":
            lat *= -1

        lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
        if coord[14] == "W":
            lon *= -1

        return lat, lon
    except:
        return None, None

# =========================
# DIRECTION
# =========================
def get_direction(lat1, lon1, lat2, lon2):

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    if abs(dlat) < 0.01 and abs(dlon) < 0.01:
        return "•"

    if dlat > 0 and abs(dlon) < 0.01:
        return "↑"
    if dlat < 0 and abs(dlon) < 0.01:
        return "↓"
    if dlon > 0 and abs(dlat) < 0.01:
        return "→"
    if dlon < 0 and abs(dlat) < 0.01:
        return "←"

    if dlat > 0 and dlon > 0:
        return "↗"
    if dlat > 0 and dlon < 0:
        return "↖"
    if dlat < 0 and dlon > 0:
        return "↘"
    if dlat < 0 and dlon < 0:
        return "↙"

    return "•"

# =========================
# EXTRACT AIRWAYS
# =========================
valid_airways = set(df["AWID"].unique())

def normalize(text):
    text = text.upper()
    text = re.sub(r"[^A-Z0-9/ ]", " ", text)
    return text

def extract_airways(text):
    text = normalize(text)
    tokens = re.split(r"[ /]+", text)
    return sorted(set(tokens) & valid_airways)

# =========================
# CSS FIXES
# =========================
st.markdown("""
<style>

.block-container {
    padding-top: 0.5rem !important;
}

.tile {
    background-color: #0e1117;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px;
    height: 300px;
    overflow-y: auto;
}

.tile-title {
    font-weight: bold;
    font-size: 16px;
    color: #4CAF50;
    margin-bottom: 10px;
}

.airway-list {
    max-height: 180px;
    overflow-y: auto;
}

</style>
""", unsafe_allow_html=True)

# =========================
# SESSION
# =========================
if "airways" not in st.session_state:
    st.session_state.airways = []

# =========================
# LAYOUT
# =========================
left, right = st.columns([1, 3])

# =========================
# LEFT PANEL
# =========================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    notam_input = st.text_area(
        "NOTAM",
        height=200,
        placeholder="Paste NOTAM here...",
        label_visibility="collapsed"
    )

    c1, c2 = st.columns(2)

    if c1.button("🚀 Parse"):
        st.session_state.airways = extract_airways(notam_input)

    if c2.button("Clear"):
        st.session_state.airways = []

    st.markdown("### ✅ Airway List")

    st.markdown('<div class="airway-list">', unsafe_allow_html=True)
    for a in st.session_state.airways:
        st.write(f"• {a}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RIGHT PANEL
# =========================
with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0, len(st.session_state.airways), 3):
        cols = st.columns(3)
        for col, airway in zip(cols, st.session_state.airways[i:i+3]):

            with col:
                group = df[df["AWID"] == airway]

                html = f'<div class="tile">'
                html += f'<div class="tile-title">{airway}</div>'

                coords_list = []
                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))

                for i in range(len(coords_list)-1):
                    w1, c1, lat1, lon1 = coords_list[i]
                    w2, c2, lat2, lon2 = coords_list[i+1]

                    arrow = get_direction(lat1, lon1, lat2, lon2)

                    html += f"{w1} ({c1}) {arrow}<br>"

                # last waypoint
                w_last, c_last, _, _ = coords_list[-1]
                html += f"{w_last} ({c_last})"

                html += "</div>"

                st.markdown(html, unsafe_allow_html=True)
