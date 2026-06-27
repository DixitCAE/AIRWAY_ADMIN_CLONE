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
# ✅ NEW VISUAL LOGIC (3 MODES)
# =========================
def get_visual_block(coords_list):

    coords = [(w, lat, lon) for (w, c, lat, lon) in coords_list if lat is not None]

    if len(coords) < 2:
        return ""

    # extremes
    north = max(coords, key=lambda x: x[1])
    south = min(coords, key=lambda x: x[1])
    east = max(coords, key=lambda x: x[2])
    west = min(coords, key=lambda x: x[2])

    dlat = north[1] - south[1]
    dlon = east[2] - west[2]

    ratio = abs(dlat) / (abs(dlon) + 1e-6)

    # ---------- VERTICAL ----------
    if ratio > 1.5:
        return f"""
        <div class="viz">
            <div class="label">{north[0]}</div>
            <div class="line-vertical"></div>
            <div class="label">{south[0]}</div>
        </div>
        """

    # ---------- HORIZONTAL ----------
    elif ratio < 0.67:
        return f"""
        <div class="viz-horizontal">
            <div class="h-label left">{west[0]}</div>
            <div class="h-label right">{east[0]}</div>
            <div class="line-horizontal"></div>
        </div>
        """

    # ---------- ✅ DIAGONAL ----------
    else:
        # decide slope direction
        # NW -> SE OR NE -> SW

        # NW = north lat + west lon
        if north[2] < east[2]:
            # NW → SE (down-right)
            return f"""
            <div class="viz-diagonal">
                <div class="tl">{north[0]}</div>
                <div class="diag-down"></div>
                <div class="br">{south[0]}</div>
            </div>
            """
        else:
            # NE → SW (down-left)
            return f"""
            <div class="viz-diagonal">
                <div class="tr">{north[0]}</div>
                <div class="diag-up"></div>
                <div class="bl">{south[0]}</div>
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
    text = normalize(text)
    tokens = re.split(r"[ /]+", text)
    return sorted(set(tokens) & valid_airways)

# =========================
# ✅ CSS (FINAL)
# =========================
st.markdown("""
<style>

.block-container {
    padding-top: 1.8rem !important;
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

/* TEXT */
.text-block {
    width: 60%;
    overflow-y: auto;
}

/* VISUAL */
.viz-container {
    width: 40%;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* ---------- VERTICAL ---------- */
.line-vertical {
    width: 3px;
    height: 80px;
    background: red;
    margin: auto;
}

/* ---------- HORIZONTAL ---------- */
.viz-horizontal {
    width: 100%;
    position: relative;
    text-align: center;
}

.h-label {
    position: absolute;
    top: -5px;
    font-size: 11px;
}

.h-label.left {
    left: 0;
}

.h-label.right {
    right: 0;
}

.line-horizontal {
    height: 3px;
    width: 70%;
    background: red;
    margin: 15px auto 0 auto;
}

/* ---------- DIAGONAL ---------- */
.viz-diagonal {
    width: 100%;
    height: 80px;
    position: relative;
}

.diag-down {
    width: 3px;
    height: 100%;
    background: red;
    transform: rotate(45deg);
    margin: auto;
}

.diag-up {
    width: 3px;
    height: 100%;
    background: red;
    transform: rotate(-45deg);
    margin: auto;
}

.tl { position:absolute; top:0; left:0; font-size:11px;}
.tr { position:absolute; top:0; right:0; font-size:11px;}
.bl { position:absolute; bottom:0; left:0; font-size:11px;}
.br { position:absolute; bottom:0; right:0; font-size:11px;}

/* TITLE */
.tile-title {
    color: #4CAF50;
    font-weight: bold;
    margin-bottom: 8px;
}

/* ✅ COMPACT LIST */
.airway-list {
    max-height: 180px;
    overflow-y: auto;
    line-height: 1.1;
    font-size: 13px;
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
# LEFT
# =========================
with left:
    st.markdown("## 📋 NOTAM INPUT")

    notam_input = st.text_area(
        "NOTAM",
        height=200,
        placeholder="Paste NOTAM...",
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
        st.markdown(f"<div>• {a}</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RIGHT
# =========================
with right:

    st.markdown("## ✈️ Airway Details")

    for i in range(0, len(st.session_state.airways), 3):

        cols = st.columns(3)

        for col, airway in zip(cols, st.session_state.airways[i:i+3]):

            with col:
                group = df[df["AWID"] == airway]

                html = f'<div class="tile">'

                # TEXT
                html += '<div class="text-block">'
                html += f'<div class="tile-title">{airway}</div>'

                coords_list = []

                for _, r in group.iterrows():
                    lat, lon = parse_coord(r["COORDS"])
                    coords_list.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))

                for w, c, _, _ in coords_list:
                    html += f"{w} ({c})<br>"

                html += '</div>'

                # VISUAL
                html += '<div class="viz-container">'
                html += get_visual_block(coords_list)
                html += '</div>'

                html += '</div>'

                st.markdown(html, unsafe_allow_html=True)
