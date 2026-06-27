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
valid_airways = set(df["AWID"].unique())

# =========================
# COORD PARSER
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
# MINI LINE GENERATOR
# =========================
def get_visual_block(coords_list):

    # remove invalid
    coords = [(w, lat, lon) for (w, c, lat, lon) in coords_list if lat is not None]

    if len(coords) < 2:
        return ""

    # find extremes
    north = max(coords, key=lambda x: x[1])
    south = min(coords, key=lambda x: x[1])
    east = max(coords, key=lambda x: x[2])
    west = min(coords, key=lambda x: x[2])

    dlat = north[1] - south[1]
    dlon = east[2] - west[2]

    # vertical vs horizontal decision
    if abs(dlat) >= abs(dlon):
        # vertical
        top = north
        bottom = south

        html = f"""
        <div class="viz">
            <div>{top[0]}</div>
            <div class="line-vertical"></div>
            <div>{bottom[0]}</div>
        </div>
        """

    else:
        # horizontal
        left = west
        right = east

        html = f"""
        <div class="viz">
            <div style="display:flex;justify-content:space-between">
                <span>{left[0]}</span>
                <span>{right[0]}</span>
            </div>
            <div class="line-horizontal"></div>
        </div>
        """

    return html

# =========================
# EXTRACT AIRWAYS
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
# CSS (FINAL CLEAN UI)
# =========================
st.markdown("""
<style>

.block-container {
    padding-top: 1.5rem !important;
}

/* TILE */
.tile {
    background-color: #0e1117;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px;
    height: 300px;
    display: flex;
    gap: 10px;
}

/* LEFT TEXT */
.text-block {
    width: 60%;
    overflow-y: auto;
}

/* RIGHT VISUAL */
.viz-container {
    width: 40%;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* VISUAL BLOCK */
.viz {
    text-align: center;
    font-size: 12px;
}

/* LINES */
.line-vertical {
    width: 3px;
    height: 80px;
    background: #ff4d4d;
    margin: auto;
}

.line-horizontal {
    height: 3px;
    width: 100%;
    background: #ff4d4d;
    margin-top: 6px;
}

.tile-title {
    color: #4CAF50;
    font-weight: bold;
    margin-bottom: 8px;
}

/* LEFT PANEL LIST */
.airway-list {
    max-height: 170px;
    overflow-y: auto;
}

h2 {
    margin-top: 10px !important;
}

</style>
""", unsafe_allow_html=True)

# =========================
# STATE
# =========================
if "airways" not in st.session_state:
    st.session_state.airways = []

# =========================
# LAYOUT
# =========================
left, right = st.columns([1,3])

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

    st.markdown("### ✅ Airways")

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

                # LEFT SIDE TEXT (UNCHANGED ORDER)
                html += '<div class="text-block">'
                html += f'<div class="tile-title">{airway}</div>'

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))

                for w, c, _, _ in coords_list:
                    html += f"{w} ({c})<br>"

                html += '</div>'

                # RIGHT SIDE VISUAL
                html += '<div class="viz-container">'
                html += get_visual_block(coords_list)
                html += '</div>'

                html += '</div>'

                st.markdown(html, unsafe_allow_html=True)
