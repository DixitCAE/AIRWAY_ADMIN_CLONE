import streamlit as st
import pandas as pd
import re

st.set_page_config(layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv")
    df.columns = ["AWID","WAYPOINT","COUNTRY","COORDS"]
    df["AWID"] = df["AWID"].str.strip().str.upper()
    return df

df = load_data()
valid_airways = set(df["AWID"])

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
# SIMPLE VISUAL
# =========================
def get_direction_visual(coords):

    pts = [(w,lat,lon) for (w,c,lat,lon) in coords if lat is not None]

    if len(pts) < 2:
        return ""

    s = pts[0]
    e = pts[-1]

    dlat = e[1] - s[1]
    dlon = e[2] - s[2]

    if abs(dlat) > abs(dlon) * 1.5:
        top = s if s[1] > e[1] else e
        bottom = e if s[1] > e[1] else s
        return f"{top[0]}<br>│<br>│<br>{bottom[0]}"

    elif abs(dlon) > abs(dlat) * 1.5:
        left = s if s[2] < e[2] else e
        right = e if s[2] < e[2] else s
        return f"{left[0]} ───── {right[0]}"

    else:
        return f"{s[0]} → {e[0]}"

# =========================
# NOTAM PARSER
# =========================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    tokens = re.split(r"[ /]+", normalize(t))
    return sorted(set(tokens) & valid_airways)

# =========================
# ✅ NEW LOGIC: SEGMENT EXTRACTION
# =========================
def extract_segments(notam_text, airways):

    text = normalize(notam_text)
    lines = text.split("\n")

    results = []

    for airway in airways:
        found = False

        for line in lines:
            if airway in line:

                # match: BTN X AND Y
                match = re.search(r"BTN ([A-Z0-9]+) AND ([A-Z0-9]+)", line)

                if match:
                    wp1 = match.group(1)
                    wp2 = match.group(2)

                    # validate using dataset
                    airway_data = df[df["AWID"] == airway]["WAYPOINT"].tolist()

                    if wp1 in airway_data and wp2 in airway_data:
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
# LAYOUT
# =========================
left, middle, right = st.columns([1,1,2])

# =========================
# LEFT PANEL
# =========================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    txt = st.text_area("NOTAM", height=200, label_visibility="collapsed")

    c1, c2 = st.columns(2)

    if c1.button("Parse"):
        airways = extract_airways(txt)
        st.session_state.airways = airways
        st.session_state.segments = extract_segments(txt, airways)

    if c2.button("Clear"):
        st.session_state.airways = []
        st.session_state.segments = []

    st.markdown("### ✅ Airways")

    for a in st.session_state.airways:
        st.text(f"• {a}")

# =========================
# ✅ NEW PANEL (SEGMENTS)
# =========================
with middle:
    st.markdown("## 📌 Restriction Output")

    if st.session_state.segments:
        output_text = "\n".join(st.session_state.segments)

        st.text_area(
            "Copy Output",
            value=output_text,
            height=250
        )

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

                st.markdown(f"### {airway}")

                coords = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))

                    st.write(f"{r['WAYPOINT']} ({r['COUNTRY']})")

                st.markdown("---")

                st.markdown(get_direction_visual(coords), unsafe_allow_html=True)
