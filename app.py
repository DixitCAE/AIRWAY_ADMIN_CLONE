import streamlit as st
import pandas as pd
import re

st.set_page_config(layout="wide")

# ================= LOAD =================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv")
    df.columns = ["AWID","WAYPOINT","COUNTRY","COORDS"]
    df["AWID"] = df["AWID"].str.strip().str.upper()
    return df

df = load_data()
valid_airways = set(df["AWID"])

# ================= COORD =================
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

# ================= ✅ CLEAN VISUAL =================
def get_direction_visual(coords):

    pts = [(w,lat,lon) for (w,c,lat,lon) in coords if lat is not None]

    if len(pts) < 2:
        return ""

    s = pts[0]
    e = pts[-1]

    dlat = e[1] - s[1]
    dlon = e[2] - s[2]

    # ✅ VERTICAL
    if abs(dlat) > abs(dlon) * 1.5:
        top = s if s[1] > e[1] else e
        bottom = e if s[1] > e[1] else s

        return f"""
        <div style='text-align:center'>
            {top[0]}<br>
            │<br>
            │<br>
            {bottom[0]}
        </div>
        """

    # ✅ HORIZONTAL
    elif abs(dlon) > abs(dlat) * 1.5:
        left = s if s[2] < e[2] else e
        right = e if s[2] < e[2] else s

        return f"""
        <div style='text-align:center'>
            {left[0]} ───── {right[0]}
        </div>
        """

    # ✅ DIAGONAL (TEXT BASED – SAFE)
    else:
        if dlat > 0 and dlon > 0:
            arrow = "↗"
        elif dlat > 0 and dlon < 0:
            arrow = "↖"
        elif dlat < 0 and dlon > 0:
            arrow = "↘"
        else:
            arrow = "↙"

        return f"""
        <div style='text-align:center'>
            {s[0]}<br>
            &nbsp;&nbsp;{arrow}<br>
            {e[0]}
        </div>
        """

# ================= NOTAM =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+",normalize(t))) & valid_airways)

# ================= STATE =================
if "airways" not in st.session_state:
    st.session_state.airways = []

# ================= UI =================
left, right = st.columns([1,3])

# LEFT
with left:
    st.markdown("## 📋 NOTAM INPUT")

    txt = st.text_area("NOTAM", height=200, label_visibility="collapsed")

    c1, c2 = st.columns(2)

    if c1.button("Parse"):
        st.session_state.airways = extract_airways(txt)

    if c2.button("Clear"):
        st.session_state.airways = []

    st.markdown("### ✅ Airways")

    for a in st.session_state.airways:
        st.text(f"• {a}")

# RIGHT
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

                    st.text(f"{r['WAYPOINT']} ({r['COUNTRY']})")

                st.markdown("---")

                st.markdown(get_direction_visual(coords), unsafe_allow_html=True)
