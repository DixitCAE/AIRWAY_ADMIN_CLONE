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
all_waypoints = set(df["WAYPOINT"].unique())

# =========================
# CSS (UNCHANGED)
# =========================
st.markdown("""<style>
.tile {
    background-color: #0e1117;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px;
    height: 300px;
    display: flex;
    gap: 10px;
}
.text-block { width: 60%; overflow-y: auto; }
.viz-container { width: 40%; display:flex; align-items:center; justify-content:center; }
.line-vertical { width: 3px; height: 80px; background:#ff4d4d; margin:auto; }
.viz-horizontal { width:100%; position:relative; text-align:center; }
.h-label { position:absolute; top:-5px; font-size:11px; }
.h-label.left { left:0; }
.h-label.right { right:0; }
.line-horizontal { height:3px; width:70%; background:#ff4d4d; margin:15px auto; }
.tile-title { color:#4CAF50; font-weight:bold; margin-bottom:8px; }
.airway-list div { margin:0; line-height:1.2; }
.output-box textarea { white-space: nowrap !important; }
.left-title { font-size:16px !important; }
</style>""", unsafe_allow_html=True)

# =========================
# COORD PARSER
# =========================
def parse_coord(coord):
    try:
        lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
        if coord[6] == "S": lat *= -1

        lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
        if coord[14] == "W": lon *= -1

        return lat, lon
    except:
        return None, None

# =========================
# VISUAL (UNCHANGED)
# =========================
def get_visual_block(coords_list):
    coords = [(w, lat, lon) for (w, c, lat, lon) in coords_list if lat is not None]
    if len(coords) < 2: return ""

    north = max(coords, key=lambda x:x[1])
    south = min(coords, key=lambda x:x[1])
    east = max(coords, key=lambda x:x[2])
    west = min(coords, key=lambda x:x[2])

    dlat = north[1] - south[1]
    dlon = east[2] - west[2]

    if abs(dlat) >= abs(dlon):
        return f"<div class='viz'>{north[0]}<div class='line-vertical'></div>{south[0]}</div>"
    else:
        return f"<div class='viz-horizontal'><span class='h-label left'>{west[0]}</span><span class='h-label right'>{east[0]}</span><div class='line-horizontal'></div></div>"

# =========================
# PARSERS
# =========================
def normalize(text):
    return re.sub(r"[^A-Z0-9/ ]", " ", text.upper())

def extract_airways(text):
    tokens = re.split(r"[ /]+", normalize(text))
    return sorted(set(tokens) & valid_airways)

# =========================
# ✅ UPDATED SEGMENT LOGIC (FINAL)
# =========================
def extract_segments(notam_text, airways):

    results = []
    lines = notam_text.split("\n")

    for airway in airways:
        found = False
        airway_points = df[df["AWID"] == airway]["WAYPOINT"].tolist()

        for line in lines:
            clean = normalize(line)

            if airway in clean:

                # ✅ BTN CASE
                match_btn = re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)", clean)

                if match_btn:
                    wp1 = match_btn.group(1)
                    wp2 = match_btn.group(2)

                    # ✅ Validate individually
                    valid_wp1 = wp1 in airway_points
                    valid_wp2 = wp2 in airway_points

                    if not valid_wp1 and not valid_wp2:
                        results.append(f"{airway} WAYPOINT NOT FOUND-WAYPOINT NOT FOUND")
                    elif valid_wp1 and not valid_wp2:
                        results.append(f"{airway} {wp1}-WAYPOINT NOT FOUND")
                    elif not valid_wp1 and valid_wp2:
                        results.append(f"{airway} WAYPOINT NOT FOUND-{wp2}")
                    else:
                        results.append(f"{airway} {wp1}-{wp2}")

                    found = True
                    break

                # ✅ DIRECTIONAL CASE
                match_dir = re.search(r"(N|S|E|W)\s+OF\s+([A-Z0-9]+)", clean)

                if match_dir:
                    wp = match_dir.group(2)

                    if wp in airway_points:
                        results.append(f"{airway} {wp}-ENTER MANUALLY")
                    else:
                        results.append(f"{airway} WAYPOINT NOT FOUND-ENTER MANUALLY")

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
# LAYOUT
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

    col1, col2 = st.columns([1,1.7])

    with col1:
        st.markdown('<div class="left-title">✅ Airways</div>', unsafe_allow_html=True)
        st.markdown('<div class="airway-list">', unsafe_allow_html=True)
        for a in st.session_state.airways:
            st.markdown(f"<div>• {a}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="left-title">📌 Output</div>', unsafe_allow_html=True)
        if st.session_state.segments:
            st.markdown('<div class="output-box">', unsafe_allow_html=True)
            st.text_area("Copy", value="\n".join(st.session_state.segments), height=260)
            st.markdown('</div>', unsafe_allow_html=True)

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
