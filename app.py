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
# VISUAL BLOCK (UNCHANGED ✅)
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
        <div style="text-align:center">
            {north[0]}<br>
            │<br>│<br>
            {south[0]}
        </div>
        """
    else:
        return f"""
        <div style="text-align:center">
            {west[0]} ───── {east[0]}
        </div>
        """

# =========================
# EXTRACT AIRWAYS
# =========================
def normalize(text):
    text = text.upper()
    text = re.sub(r"[^A-Z0-9/ ]", " ", text)
    return text

def extract_airways(text):
    tokens = re.split(r"[ /]+", normalize(text))
    return sorted(set(tokens) & valid_airways)

# =========================
# ✅ NEW: SEGMENT EXTRACTION (FIXED)
# =========================
def extract_segments(notam_text, airways):

    lines = notam_text.upper().split("\n")
    results = []

    for airway in airways:
        found = False

        for line in lines:

            # ✅ clean punctuation
            clean = re.sub(r"[^A-Z0-9/ ]", " ", line.upper())

            if airway in clean:

                match = re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)", clean)

                if match:
                    wp1 = match.group(1)
                    wp2 = match.group(2)

                    airway_points = df[df["AWID"] == airway]["WAYPOINT"].tolist()

                    if wp1 in airway_points and wp2 in airway_points:
                        results.append(f"{airway} {wp1}-{wp2}")
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
# LAYOUT (UNCHANGED ✅)
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
        airways = extract_airways(notam_input)
        st.session_state.airways = airways
        st.session_state.segments = extract_segments(notam_input, airways)

    if c2.button("Clear"):
        st.session_state.airways = []
        st.session_state.segments = []

    # ✅ LOCAL SPLIT ONLY (SAFE)
    col_air, col_out = st.columns(2)

    with col_air:
        st.markdown("### ✅ Airways")
        for a in st.session_state.airways:
            st.text(f"• {a}")

    with col_out:
        st.markdown("### 📌 Output")
        if st.session_state.segments:
            st.text_area(
                "Copy",
                value="\n".join(st.session_state.segments),
                height=260
            )

# =========================
# RIGHT PANEL (UNCHANGED ✅)
# =========================
with right:

    st.markdown("## ✈️ Airway Details")

    for i in range(0, len(st.session_state.airways), 3):

        cols = st.columns(3)

        for col, airway in zip(cols, st.session_state.airways[i:i+3]):

            with col:
                group = df[df["AWID"] == airway]

                html = f'<div style="padding:10px;border:1px solid #333;border-radius:6px;">'
                html += f'<div style="color:#4CAF50;font-weight:bold;">{airway}</div>'

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))
                    html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html += "<hr>"
                html += get_visual_block(coords_list)
                html += "</div>"

                st.markdown(html, unsafe_allow_html=True)
