import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt

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

# ================= PARSE COORD =================
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

# ================= ✅ VISUAL FIX =================
def draw_airway(coords):

    pts = [(lat,lon,name) for (name,c,lat,lon) in coords if lat is not None]

    if len(pts) < 2:
        return None

    start = pts[0]
    end   = pts[-1]

    fig, ax = plt.subplots(figsize=(2,2))

    # plot line
    ax.plot([start[1], end[1]], [start[0], end[0]], color="red")

    # plot points
    ax.scatter([start[1], end[1]], [start[0], end[0]], color="white", s=10)

    # labels
    ax.text(start[1], start[0], start[2], fontsize=6, color="white")
    ax.text(end[1], end[0], end[2], fontsize=6, color="white")

    # clean look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#0e1117")
    fig.patch.set_facecolor("#0e1117")

    return fig

# ================= NOTAM =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    tokens = re.split(r"[ /]+",normalize(t))
    return sorted(set(tokens) & valid_airways)

# ================= UI =================

if "airways" not in st.session_state:
    st.session_state.airways = []

left,right = st.columns([1,3])

# ================= LEFT =================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    txt = st.text_area("NOTAM", height=200, label_visibility="collapsed")

    c1,c2 = st.columns(2)
    if c1.button("Parse"):
        st.session_state.airways = extract_airways(txt)
    if c2.button("Clear"):
        st.session_state.airways = []

    st.markdown("### ✅ Airways")

    for a in st.session_state.airways:
        st.write(f"• {a}")

# ================= RIGHT =================
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

                fig = draw_airway(coords)
                if fig:
                    st.pyplot(fig, use_container_width=True)
