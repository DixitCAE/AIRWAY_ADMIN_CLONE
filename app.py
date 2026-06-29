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
    df["COUNTRY"] = df["COUNTRY"].astype(str).str.upper().str.strip()
    return df

df = load_data()
valid_airways = set(df["AWID"].unique())

VALID_COUNTRIES = {"KZ", "K1", "K2", "K3", "K4", "K5", "K6", "K7"}

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
        return f"{north[0]}<br>{south[0]}"
    else:
        return f"{west[0]}<br>{east[0]}"

# =========================
# NORMALIZE
# =========================
def normalize(text):
    text = text.upper()
    text = re.sub(r"[^A-Z0-9/ ]", " ", text)
    return text

# =========================
# EXTRACT AIRWAYS
# =========================
def extract_airways(text):
    text = normalize(text)
    tokens = re.split(r"[ /]+", text)
    return sorted(set(tokens) & valid_airways)

# =========================
# FEATURE 1: SEGMENT PARSER (BTN CASE)
# =========================
def extract_btn_segments(text):
    results = {}
    for airway in valid_airways:
        if airway in text:
            pattern = rf"{airway}.*?BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)"
            match = re.search(pattern, text)

            if match:
                wp1, wp2 = match.group(1), match.group(2)
                airway_wps = set(df[df["AWID"] == airway]["WAYPOINT"])

                if wp1 in airway_wps and wp2 in airway_wps:
                    results[airway] = f"{airway} {wp1}-{wp2}"
                else:
                    results[airway] = f"{airway} WAYPOINT NOT FOUND"
    return results

# =========================
# ✅ FEATURE 2: FULL AIRWAY CLOSED
# =========================
def extract_full_closure_segments(text):
    results = {}

    pattern = r"([A-Z0-9/]+)\s+CLSD"
    matches = re.findall(pattern, text)

    for match in matches:
        airways = match.split("/")

        for airway in airways:
            airway = airway.strip()

            if airway in valid_airways:
                group = df[df["AWID"] == airway]

                # filter required countries
                group = group[group["COUNTRY"].isin(VALID_COUNTRIES)]

                if not group.empty:
                    first_wp = group.iloc[0]["WAYPOINT"]
                    last_wp = group.iloc[-1]["WAYPOINT"]
                    results[airway] = f"{airway} {first_wp}-{last_wp}"
                else:
                    results[airway] = f"{airway} WAYPOINT NOT FOUND"

    return results

# =========================
# MASTER OUTPUT GENERATOR
# =========================
def extract_segments(text):
    text = normalize(text)

    final = {}

    # Priority 1: BTN cases
    btn_results = extract_btn_segments(text)
    final.update(btn_results)

    # Priority 2: FULL closure
    full_results = extract_full_closure_segments(text)
    for k, v in full_results.items():
        if k not in final:
            final[k] = v

    # Remaining airways → manual
    all_airways = extract_airways(text)

    for a in all_airways:
        if a not in final:
            final[a] = f"{a} ENTER MANUALLY-ENTER MANUALLY"

    return [final[a] for a in sorted(final.keys())]

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

    notam_input = st.text_area(
        "NOTAM",
        height=200,
        placeholder="Paste NOTAM here...",
        label_visibility="collapsed"
    )

    c1, c2 = st.columns(2)

    if c1.button("🚀 Parse"):
        st.session_state.airways = extract_airways(notam_input)
        st.session_state.segments = extract_segments(notam_input)

    if c2.button("Clear"):
        st.session_state.airways = []
        st.session_state.segments = []

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### ✅ Airways")
        for a in st.session_state.airways:
            st.markdown(f"- {a}")

    with col_b:
        st.markdown("### 📤 Output")
        output_text = "\n".join(st.session_state.segments)
        st.text_area("Output", value=output_text, height=200)

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

                html = '<div style="border:1px solid #333;padding:10px;border-radius:10px;">'
                html += f"<b>{airway}</b><br>"

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))
                    html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html += "<hr>"
                html += get_visual_block(coords_list)
                html += "</div>"

                st.markdown(html, unsafe_allow_html=True)
