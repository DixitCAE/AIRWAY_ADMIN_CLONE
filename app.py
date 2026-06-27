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
# CSS (DO NOT CHANGE)
# =========================
st.markdown("""
<style>

.tile {
    background-color: #0e1117;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px;
    height: 300px;
    display: flex;
    gap: 10px;
}

.text-block {
    width: 60%;
    overflow-y: auto;
}

.viz-container {
    width: 40%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.line-vertical {
    width: 3px;
    height: 80px;
    background: #ff4d4d;
    margin: auto;
}

.viz-horizontal {
    width: 100%;
    text-align: center;
    position: relative;
}

.h-label {
    position: absolute;
    top: -5px;
    font-size: 11px;
}

.h-label.left { left: 0; }
.h-label.right { right: 0; }

.line-horizontal {
    height: 3px;
    width: 70%;
    background: #ff4d4d;
    margin: 15px auto 0 auto;
}

.tile-title {
    color: #4CAF50;
    font-weight: bold;
    margin-bottom: 8px;
}

</style>
""", unsafe_allow_html=True)

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
# VISUAL BLOCK (UNCHANGED)
# =========================
def get_visual_block(coords_list):
    coords = [(w, lat, lon) for (w, c, lat, lon) in coords_list if lat is not None]

    if len(coords) < 2:
        return ""

    north = max(coords, key=lambda x: x[1])
    south = min(coords, key=lambda x: x[1])
    east = max(coords, key=lambda x: x[2])
    west = min(coords, key=lambda x: x[2])

    dlat = north[1] - south[1]
    dlon = east[2] - west[2]

    if abs(dlat) >= abs(dlon):
        return f"""
        <div class="viz">
            <div class="label">{north[0]}</div>
            <div class="line-vertical"></div>
            <div class="label">{south[0]}</div>
        </div>
        """
    else:
        return f"""
        <div class="viz-horizontal">
            <div class="h-label left">{west[0]}</div>
            <div class="h-label right">{east[0]}</div>
            <div class="line-horizontal"></div>
        </div>
        """

# =========================
# NORMALIZE
# =========================
def normalize(text):
    return re.sub(r"[^A-Z0-9/ ]", " ", text.upper())

# =========================
# EXTRACT AIRWAYS
# =========================
def extract_airways(text):
    tokens = re.split(r"[ /]+", normalize(text))
    return sorted(set(tokens) & valid_airways)

# =========================
# ✅ UPDATED SEGMENT LOGIC
# =========================
def extract_segments(notam_text, airways):

    results = []
    lines = notam_text.split("\n")

    for airway in airways:
        found = False

        for line in lines:
            clean = normalize(line)

            if airway in clean:

                # ✅ CASE 1: BTN A AND B
                match_btn = re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)", clean)

                if match_btn:
                    wp1, wp2 = match_btn.group(1), match_btn.group(2)

                    airway_points = df[df["AWID"] == airway]["WAYPOINT"].tolist()

                    if wp1 in airway_points and wp2 in airway_points:
                        results.append(f"{airway} {wp1}-{wp2}")
                        found = True
                        break

                # ✅ CASE 2: DIRECTIONAL (N/S/E/W OF)
                match_dir = re.search(r"(N|S|E|W)\s+OF\s+([A-Z0-9]+)", clean)

                if match_dir:
                    wp = match_dir.group(2)

                    airway_points = df[df["AWID"] == airway]["WAYPOINT"].tolist()

                    if wp in airway_points:
                        results.append(f"{airway} {wp}-ENTER MANUALLY")
                        found = True
                        break

        if not found:
            results.append(f"{airway} ENTER MANUALLY")

    return results

# =========================
# STATE
# =========================
if "airways" not in st.session_state:
    st.session_state.airways = []

if "segments" not in st.session_state:
    st.session_state.segments = []

# =========================
# MAIN LAYOUT
# =========================
left, right = st.columns([1,3])

# =========================
# LEFT PANEL
# =========================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    txt = st.text_area("NOTAM", height=200, label_visibility="collapsed")

    c1, c2 = st.columns(2)

    if c1.button("🚀 Parse"):
        airways = extract_airways(txt)
        st.session_state.airways = airways
        st.session_state.segments = extract_segments(txt, airways)

    if c2.button("Clear"):
        st.session_state.airways = []
        st.session_state.segments = []

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ Airways")
        for a in st.session_state.airways:
            st.write(f"• {a}")

    with col2:
        st.markdown("### 📌 Output")
        if st.session_state.segments:
            st.text_area("Copy", value="\n".join(st.session_state.segments), height=250)

# =========================
# RIGHT PANEL (UNCHANGED)
# =========================
with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0, len(st.session_state.airways), 3):

        cols = st.columns(3)

        for col, airway in zip(cols, st.session_state.airways[i:i+3]):

            with col:
                group = df[df["AWID"] == airway]

                html = f'<div class="tile">'

                html += '<div class="text-block">'
                html += f'<div class="tile-title">{airway}</div>'

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))
                    html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html += '</div>'
                html += '<div class="viz-container">'
                html += get_visual_block(coords_list)
                html += '</div>'
                html += '</div>'

                st.markdown(html, unsafe_allow_html=True)
