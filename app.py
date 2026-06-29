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
    df["WAYPOINT"] = df["WAYPOINT"].astype(str).str.upper().str.strip()
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
# VISUAL BLOCK
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
        <div style='text-align:center'>
        {north[0]}<br>|<br>|<br>|<br>{south[0]}
        </div>
        """
    else:
        return f"""
        <div style='text-align:center'>
        {west[0]} -------- {east[0]}
        </div>
        """

# =========================
# NORMALIZE / AIRWAY EXTRACT
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
# ✅ NEW: SEGMENT EXTRACTION LOGIC
# =========================
def extract_segments(text, airways):
    text = normalize(text)

    output_lines = []

    for airway in airways:
        # Pattern: Y330 BTN FODED AND HARBG
        pattern = rf"{airway}.*?BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)"
        match = re.search(pattern, text)

        if match:
            wp1, wp2 = match.group(1), match.group(2)

            # Validate waypoints exist in airway
            airway_wps = set(df[df["AWID"] == airway]["WAYPOINT"])

            if wp1 in airway_wps and wp2 in airway_wps:
                output_lines.append(f"{airway} {wp1}-{wp2}")
            else:
                output_lines.append(f"{airway} WAYPOINT NOT FOUND")

        else:
            output_lines.append(f"{airway} ENTER MANUALLY-ENTER MANUALLY")

    return output_lines

# =========================
# STATE
# =========================
if "airways" not in st.session_state:
    st.session_state.airways = []

if "output" not in st.session_state:
    st.session_state.output = []

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
        st.session_state.output = extract_segments(notam_input, st.session_state.airways)

    if c2.button("Clear"):
        st.session_state.airways = []
        st.session_state.output = []

    # ✅ Split into 2 columns: Airways + Output
    a_col, o_col = st.columns(2)

    # ================= AIRWAYS =================
    with a_col:
        st.markdown("### ✅ Airways")
        for a in st.session_state.airways:
            st.markdown(f"• {a}")

    # ================= OUTPUT =================
    with o_col:
        st.markdown("### 📤 Output")

        output_text = ""
        for line in st.session_state.output:
            output_text += line + ",\n"

        st.text_area(
            label="Output",
            value=output_text.strip(),
            height=300
        )

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

                html = f"<div style='border:1px solid #333;padding:10px;border-radius:10px'>"
                html += f"<h4 style='color:#00FFAA'>{airway}</h4>"

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))
                    html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html += "<hr>"
                html += get_visual_block(coords_list)
                html += "</div>"

                st.markdown(html, unsafe_allow_html=True)
