import streamlit as st
import pandas as pd
import re
import math

st.set_page_config(layout="wide")

# ================= LOAD =================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv", engine="python")
    df.columns = ["AWID","WAYPOINT","COUNTRY","COORDS"]
    df["AWID"] = df["AWID"].astype(str).str.upper().str.strip()
    return df

df = load_data()
valid_airways = set(df["AWID"].unique())

# ================= CSS =================
st.markdown("""
<style>
.tile {background:#0e1117;border:1px solid #333;border-radius:8px;padding:12px;height:300px;display:flex;gap:10px;}
.text-block {width:60%;overflow:auto;}
.viz-container {width:40%;display:flex;align-items:center;justify-content:center;}

.line-vertical {width:3px;height:80px;background:#ff4d4d;margin:auto;}

.viz-horizontal {position:relative;text-align:center;}
.h-label {position:absolute;top:-5px;font-size:11px;}
.h-label.left{left:0;} .h-label.right{right:0;}

.line-horizontal{height:3px;width:70%;background:#ff4d4d;margin:15px auto;}

.tile-title {color:#4CAF50;font-weight:bold;margin-bottom:6px;}

.airway-list div {margin:0;line-height:1.2;}
.output-box textarea {white-space:nowrap !important;}
</style>
""", unsafe_allow_html=True)

# ================= ✅ ROBUST COORD PARSER =================
def parse_coord(coord):
    try:
        coord = coord.strip().replace(" ", "")

        match = re.match(
            r"(\d{2})(\d{2})?(\d{2})?([NS])(\d{3})(\d{2})?(\d{2})?([EW])",
            coord
        )

        if not match:
            return None, None

        lat = float(match.group(1))
        lat += float(match.group(2) or 0)/60
        lat += float(match.group(3) or 0)/3600

        lon = float(match.group(5))
        lon += float(match.group(6) or 0)/60
        lon += float(match.group(7) or 0)/3600

        if match.group(4) == "S":
            lat *= -1
        if match.group(8) == "W":
            lon *= -1

        return lat, lon

    except:
        return None, None

# ================= ✅ VISUAL FIX =================
def get_visual_block(coords_list):

    coords = [(w,lat,lon) for (w,c,lat,lon) in coords_list 
              if lat is not None and lon is not None]

    if len(coords) < 2:
        return "<div style='color:#666'>•</div>"

    north=max(coords,key=lambda x:x[1])
    south=min(coords,key=lambda x:x[1])
    east=max(coords,key=lambda x:x[2])
    west=min(coords,key=lambda x:x[2])

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
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]", " ", t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+", normalize(t))) & valid_airways)

# ================= HELPERS =================
def get_airway_coords(airway):
    allowed = ["KZ","K1","K2","K3","K4","K5","K6","K7"]
    g = df[(df["AWID"]==airway) & (df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in g.iterrows():
        lat,lon = parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"], r["COUNTRY"], lat, lon))

    return coords

# ================= SEGMENT ENGINE =================
def extract_segments(text, airways):

    results = []
    seen = set()

    for line in text.split("\n"):

        clean = normalize(line)

        # ✅ only process CLSD lines
        if "CLSD" not in clean:
            continue

        matched = [a for a in airways if a in clean]

        # ✅ DISTANCE (ONLY SE case for now)
        m = re.search(r"BTN\s+(\w+)\s+AND\s+(\d+)NM\s+(SE)", clean)
        if m:
            base,dist,dirn = m.group(1), int(m.group(2)), m.group(3)

            for a in matched:
                key=(a,base,dist)
                if key in seen: continue

                # find next waypoint after base
                coords=[(w,lat,lon) for (w,c,lat,lon) in get_airway_coords(a)]
                names=[c[0] for c in coords]

                if base in names:
                    idx = names.index(base)
                    next_wp = names[idx+1] if idx+1 < len(names) else "ENTER MANUALLY"
                else:
                    next_wp = "WAYPOINT NOT FOUND"

                results.append(f"{a} {base}-{next_wp}")
                seen.add(key)
            continue

        # ✅ BTN
        m = re.search(r"BTN\s+(\w+)\s+AND\s+(\w+)", clean)
        if m:
            wp1,wp2 = m.group(1), m.group(2)

            for a in matched:
                key=(a,wp1,wp2)
                if key in seen: continue

                results.append(f"{a} {wp1}-{wp2}")
                seen.add(key)
            continue

        # ✅ DIRECTION
        m = re.search(r"(N|S|E|W)\s+OF\s+(\w+)", clean)
        if m:
            dirn, wp = m.group(1), m.group(2)

            for a in matched:
                key=(a,wp,dirn)
                if key in seen: continue

                coords = get_airway_coords(a)
                names=[c[0] for c in coords]

                if wp in names:
                    idx = names.index(wp)

                    if dirn=="S":
                        nxt = names[idx+1] if idx+1<len(names) else "ENTER MANUALLY"
                    elif dirn=="N":
                        nxt = names[idx-1] if idx>0 else "ENTER MANUALLY"
                    elif dirn=="E":
                        nxt = names[idx+1] if idx+1<len(names) else "ENTER MANUALLY"
                    else:
                        nxt = names[idx-1] if idx>0 else "ENTER MANUALLY"

                    results.append(f"{a} {wp}-{nxt}")
                else:
                    results.append(f"{a} WAYPOINT NOT FOUND-ENTER MANUALLY")

                seen.add(key)
            continue

        # ✅ FULL AIRWAY
        for a in matched:
            if a not in [r.split()[0] for r in results]:
                coords=get_airway_coords(a)
                if coords:
                    results.append(f"{a} {coords[0][0]}-{coords[-1][0]}")

    return results

# ================= STATE =================
if "airways" not in st.session_state:
    st.session_state.airways=[]
if "segments" not in st.session_state:
    st.session_state.segments=[]

# ================= UI =================
left,right = st.columns([1,3])

with left:
    txt = st.text_area("NOTAM", height=200)

    c1,c2 = st.columns(2)

    if c1.button("Parse"):
        aw = extract_airways(txt)
        st.session_state.airways = aw
        st.session_state.segments = extract_segments(txt, aw)

    if c2.button("Clear"):
        st.session_state.airways=[]
        st.session_state.segments=[]

    col1,col2 = st.columns([1,1.7])

    with col1:
        st.markdown("### ✅ Airways")
        for a in st.session_state.airways:
            st.markdown(f"• {a}")

    with col2:
        st.markdown("### 📌 Output")
        if st.session_state.segments:
            st.text_area("", "\n".join(st.session_state.segments), height=260)

# ================= RIGHT =================
with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0, len(st.session_state.airways), 3):
        cols = st.columns(3)

        for col, aw in zip(cols, st.session_state.airways[i:i+3]):
            with col:
                coords = get_airway_coords(aw)

                html = '<div class="tile"><div class="text-block">'
                html += f'<div class="tile-title">{aw}</div>'

                for w,c,lat,lon in coords:
                    html += f"{w} ({c})<br>"

                html += '</div><div class="viz-container">'
                html += get_visual_block(coords)
                html += '</div></div>'

                st.markdown(html, unsafe_allow_html=True)
