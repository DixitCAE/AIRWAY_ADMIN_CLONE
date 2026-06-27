import streamlit as st
import pandas as pd
import re
import math

st.set_page_config(layout="wide")

# ================= LOAD =================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv", engine="python")
    df.columns = ["AWID", "WAYPOINT", "COUNTRY", "COORDS"]
    df["AWID"] = df["AWID"].astype(str).str.upper().str.strip()
    return df

df = load_data()
valid_airways = set(df["AWID"].unique())

# ================= CSS =================
st.markdown("""
<style>
.tile {
    background:#0e1117;
    border:1px solid #333;
    border-radius:8px;
    padding:12px;
    height:300px;
    display:flex;
    gap:10px;
}

.text-block { width:60%; overflow:auto; }

.viz-container {
    width:40%;
    display:flex;
    align-items:center;
    justify-content:center;
}

.line-vertical {
    width:3px;
    height:80px;
    background:#ff4d4d;
    margin:auto;
}

.viz-horizontal {
    position:relative;
    text-align:center;
}

.h-label {
    position:absolute;
    top:-5px;
    font-size:11px;
}

.h-label.left { left:0; }
.h-label.right { right:0; }

.line-horizontal {
    height:3px;
    width:70%;
    background:#ff4d4d;
    margin:15px auto;
}

.tile-title {
    color:#4CAF50;
    font-weight:bold;
    margin-bottom:6px;
}

.airway-list div { margin:0; line-height:1.2; }

.output-box textarea { white-space:nowrap !important; }

</style>
""", unsafe_allow_html=True)

# ================= ✅ FIXED COORD =================
def parse_coord(coord):
    try:
        coord = coord.strip()

        if len(coord) >= 15:
            lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
            if coord[6] == "S":
                lat *= -1

            lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
            if coord[14] == "W":
                lon *= -1
        else:
            lat = float(coord[0:2]) + float(coord[2:4])/60
            if coord[4] == "S":
                lat *= -1

            lon = float(coord[5:8]) + float(coord[8:10])/60
            if coord[10] == "W":
                lon *= -1

        return lat, lon
    except:
        return None, None


# ================= ✅ VISUAL (FIXED) =================
def get_visual_block(coords_list):

    coords = [(w, lat, lon) for (w, c, lat, lon) in coords_list
              if lat is not None and lon is not None]

    if len(coords) < 2:
        return "<div style='color:#666'>•</div>"

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
            <div class="line-vertical"></div>
            {south[0]}
        </div>
        """
    else:
        return f"""
        <div class="viz-horizontal">
            <span class="h-label left">{west[0]}</span>
            <span class="h-label right">{east[0]}</span>
            <div class="line-horizontal"></div>
        </div>
        """

# ================= PARSE =================
def normalize(text):
    return re.sub(r"[^A-Z0-9/ ]", " ", text.upper())

def extract_airways(text):
    tokens = re.split(r"[ /]+", normalize(text))
    return sorted(set(tokens) & valid_airways)

# ================= SEGMENTS =================
def extract_segments(text, airways):

    results = []
    seen = {a: set() for a in airways}

    for line in text.split("\n"):

        clean = normalize(line)

        # ✅ ONLY CLSD lines
        if "CLSD" not in clean:
            continue

        matched = [a for a in airways if a in clean]

        # ================= BTN =================
        if "BTN" in clean:

            m = re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)", clean)

            if m:
                wp1, wp2 = m.group(1), m.group(2)

                for a in matched:
                    key = frozenset([wp1, wp2])

                    if key in seen[a]:
                        continue

                    results.append(f"{a} {wp1}-{wp2}")
                    seen[a].add(key)

        # ================= DIRECTION =================
        elif " OF " in clean:

            m = re.search(r"(N|S|E|W)\s+OF\s+([A-Z0-9]+)", clean)

            if m:
                dirn, wp = m.group(1), m.group(2)

                for a in matched:

                    key = (wp, dirn)

                    if key in seen[a]:
                        continue

                    results.append(f"{a} {wp}-ENTER MANUALLY")
                    seen[a].add(key)

        # ================= FULL =================
        else:
            for a in matched:
                if a not in [r.split()[0] for r in results]:

                    g = df[df["AWID"] == a]
                    pts = g["WAYPOINT"].tolist()

                    if pts:
                        results.append(f"{a} {pts[0]}-{pts[-1]}")
                    else:
                        results.append(f"{a} ENTER MANUALLY")

    return results


# ================= STATE =================
if "airways" not in st.session_state:
    st.session_state.airways = []

if "segments" not in st.session_state:
    st.session_state.segments = []


# ================= UI =================
left, right = st.columns([1, 3])

with left:
    txt = st.text_area("NOTAM", height=200)

    c1, c2 = st.columns(2)

    if c1.button("Parse"):
        aw = extract_airways(txt)
        st.session_state.airways = aw
        st.session_state.segments = extract_segments(txt, aw)

    if c2.button("Clear"):
        st.session_state.airways = []
        st.session_state.segments = []

    for a in st.session_state.airways:
        st.write("•", a)

    st.text_area("", "\n".join(st.session_state.segments), height=250)

# ================= RIGHT =================
with right:

    st.markdown("## ✈️ Airway Details")

    for i in range(0, len(st.session_state.airways), 3):

        cols = st.columns(3)

        for col, aw in zip(cols, st.session_state.airways[i:i+3]):

            with col:

                group = df[df["AWID"] == aw]

                html = '<div class="tile"><div class="text-block">'
                html += f'<div class="tile-title">{aw}</div>'

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))
                    html += f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html += '</div><div class="viz-container">'
                html += get_visual_block(coords_list)
                html += '</div></div>'

                st.markdown(html, unsafe_allow_html=True)
