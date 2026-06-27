import streamlit as st
import pandas as pd
import re

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
.tile {background:#0e1117;border:1px solid #333;border-radius:8px;padding:12px;height:300px;display:flex;gap:10px;}
.text-block { width:60%; overflow:auto; }
.viz-container { width:40%; display:flex; align-items:center; justify-content:center; }
.line-vertical { width:3px;height:80px;background:red;margin:auto;}
.viz-horizontal { position:relative;text-align:center;}
.h-label { position:absolute; top:-5px; font-size:11px;}
.h-label.left{left:0;} .h-label.right{right:0;}
.line-horizontal{height:3px;width:70%;background:red;margin:15px auto;}
.tile-title {color:#4CAF50;font-weight:bold;}
.airway-list div{margin:0;line-height:1.2;}
.output-box textarea{white-space:nowrap !important;}
</style>
""", unsafe_allow_html=True)

# ================= COORD =================
def parse_coord(coord):
    try:
        lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
        if coord[6]=="S": lat*=-1
        lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
        if coord[14]=="W": lon*=-1
        return lat, lon
    except:
        return None, None

# ================= VISUAL =================
def get_visual_block(coords_list):
    coords=[(w,lat,lon) for (w,c,lat,lon) in coords_list if lat]
    if len(coords)<2: return ""

    north=max(coords,key=lambda x:x[1])
    south=min(coords,key=lambda x:x[1])
    east=max(coords,key=lambda x:x[2])
    west=min(coords,key=lambda x:x[2])

    if abs(north[1]-south[1])>=abs(east[2]-west[2]):
        return f"<div>{north[0]}<div class='line-vertical'></div>{south[0]}</div>"
    else:
        return f"<div class='viz-horizontal'><span class='h-label left'>{west[0]}</span><span class='h-label right'>{east[0]}</span><div class='line-horizontal'></div></div>"

# ================= PARSE =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+",normalize(t))) & valid_airways)

# ================= DIRECTION =================
def get_directional_endpoint(airway, base_wp, direction):

    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]

    adf=df[(df["AWID"]==airway) & (df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in adf.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],lat,lon))

    base=next((c for c in coords if c[0]==base_wp),None)
    if not base:
        return "WAYPOINT NOT FOUND"

    lat0,lon0=base[1],base[2]

    if direction=="S":
        pts=[c for c in coords if c[1]<lat0]
        key=lambda x:x[1]; func=min
    elif direction=="N":
        pts=[c for c in coords if c[1]>lat0]
        key=lambda x:x[1]; func=max
    elif direction=="W":
        pts=[c for c in coords if c[2]<lon0]
        key=lambda x:x[2]; func=min
    elif direction=="E":
        pts=[c for c in coords if c[2]>lon0]
        key=lambda x:x[2]; func=max

    if not pts:
        return "ENTER MANUALLY"

    return func(pts,key=key)[0]

# ================= ✅ FULL AIRWAY =================
def get_full_airway_segment(airway):

    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]

    adf=df[(df["AWID"]==airway) & (df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in adf.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],lat,lon))

    if not coords:
        return "ENTER MANUALLY"

    # first & last appear in dataset order
    return f"{coords[0][0]}-{coords[-1][0]}"

# ================= SEGMENTS =================
def extract_segments(text,airways):

    results=[]
    seen={aw:set() for aw in airways}
    lines=text.split("\n")

    for line in lines:
        clean=normalize(line)
        matched=[aw for aw in airways if aw in clean]

        if not matched:
            continue

        handled=False

        # BTN
        m=re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)",clean)
        if m:
            handled=True
            wp1,wp2=m.group(1),m.group(2)

            for aw in matched:
                key=frozenset([wp1,wp2])
                if key in seen[aw]:
                    continue

                pts=df[df["AWID"]==aw]["WAYPOINT"].tolist()

                v1,v2=wp1 in pts, wp2 in pts

                if not v1 and not v2:
                    res=f"{aw} WAYPOINT NOT FOUND-WAYPOINT NOT FOUND"
                elif v1 and not v2:
                    res=f"{aw} {wp1}-WAYPOINT NOT FOUND"
                elif not v1 and v2:
                    res=f"{aw} WAYPOINT NOT FOUND-{wp2}"
                else:
                    res=f"{aw} {wp1}-{wp2}"

                results.append(res)
                seen[aw].add(key)

        # DIRECTION
        d=re.search(r"(N|S|E|W)\s+OF\s+([A-Z0-9]+)",clean)
        if d:
            handled=True
            dirn,wp=d.group(1),d.group(2)

            for aw in matched:
                key=(wp,dirn)
                if key in seen[aw]:
                    continue

                second=get_directional_endpoint(aw,wp,dirn)
                results.append(f"{aw} {wp}-{second}")
                seen[aw].add(key)

        # ✅ FULL AIRWAY CASE
        if not handled:
            for aw in matched:
                if not any(r.startswith(aw) for r in results):
                    seg=get_full_airway_segment(aw)
                    results.append(f"{aw} {seg}")

    return results

# ================= STATE =================
if "airways" not in st.session_state:
    st.session_state.airways=[]
if "segments" not in st.session_state:
    st.session_state.segments=[]

# ================= UI =================
left,right=st.columns([1,3])

with left:
    txt=st.text_area("NOTAM",200)

    c1,c2=st.columns(2)
    if c1.button("Parse"):
        aw=extract_airways(txt)
        st.session_state.airways=aw
        st.session_state.segments=extract_segments(txt,aw)
    if c2.button("Clear"):
        st.session_state.airways=[]
        st.session_state.segments=[]

    col1,col2=st.columns([1,1.7])

    with col1:
        st.markdown("### ✅ Airways")
        st.markdown('<div class="airway-list">',unsafe_allow_html=True)
        for a in st.session_state.airways:
            st.markdown(f"<div>• {a}</div>",unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

    with col2:
        st.markdown("### 📌 Output")
        if st.session_state.segments:
            st.markdown('<div class="output-box">',unsafe_allow_html=True)
            st.text_area("Copy",value="\n".join(st.session_state.segments),height=260)

# ================= RIGHT =================
with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0,len(st.session_state.airways),3):
        cols=st.columns(3)

        for col,aw in zip(cols,st.session_state.airways[i:i+3]):
            with col:
                g=df[df["AWID"]==aw]

                html='<div class="tile">'
                html+='<div class="text-block">'
                html+=f'<div class="tile-title">{aw}</div>'

                coords=[]
                for _,r in g.iterrows():
                    lat,lon=parse_coord(r["COORDS"])
                    coords.append((r["WAYPOINT"],r["COUNTRY"],lat,lon))
                    html+=f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html+='</div>'
                html+='<div class="viz-container">'
                html+=get_visual_block(coords)
                html+='</div></div>'

                st.markdown(html,unsafe_allow_html=True)
