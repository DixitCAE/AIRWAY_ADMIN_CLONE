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
.text-block {width:60%;overflow:auto;}
.viz-container {width:40%;display:flex;align-items:center;justify-content:center;}
.line-vertical {width:3px;height:80px;background:#ff4d4d;margin:auto;}
.viz-horizontal {position:relative;text-align:center;}
.h-label {position:absolute;top:-5px;font-size:11px;}
.h-label.left{left:0;} .h-label.right{right:0;}
.line-horizontal{height:3px;width:70%;background:#ff4d4d;margin:15px auto;}
.tile-title {color:#4CAF50;font-weight:bold;margin-bottom:6px;}
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
        return lat,lon
    except:
        return None,None

# ================= ✅ FIXED VISUAL =================
def get_visual_block(coords_list):

    coords = [(w, lat, lon) for (w,c,lat,lon) in coords_list 
              if lat is not None and lon is not None]

    if len(coords) < 2:
        return "<div style='text-align:center;color:#666;'>•</div>"

    north=max(coords,key=lambda x:x[1])
    south=min(coords,key=lambda x:x[1])
    east=max(coords,key=lambda x:x[2])
    west=min(coords,key=lambda x:x[2])

    dlat = north[1]-south[1]
    dlon = east[2]-west[2]

    if abs(dlat) >= abs(dlon):
        return f"""
        <div style="text-align:center">
            {north[0]}<br>
            <div class='line-vertical'></div>
            {south[0]}
        </div>
        """
    else:
        return f"""
        <div class='viz-horizontal'>
            <span class='h-label left'>{west[0]}</span>
            <span class='h-label right'>{east[0]}</span>
            <div class='line-horizontal'></div>
        </div>
        """

# ================= PARSE =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+",normalize(t))) & valid_airways)

# ================= FULL AIRWAY =================
def get_full_airway_segment(airway):
    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]
    adf=df[(df["AWID"]==airway)&(df["COUNTRY"].isin(allowed))]
    if adf.empty: return "ENTER MANUALLY"
    pts=adf["WAYPOINT"].tolist()
    return f"{pts[0]}-{pts[-1]}"

# ================= DIRECTION =================
def get_directional_endpoint(airway, base, direction):
    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]
    adf=df[(df["AWID"]==airway)&(df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in adf.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],lat,lon))

    base_pt=next((c for c in coords if c[0]==base),None)
    if not base_pt: return "WAYPOINT NOT FOUND"

    lat0,lon0=base_pt[1],base_pt[2]

    if direction=="S":
        pts=[c for c in coords if c[1]<lat0]; key=lambda x:x[1]; func=min
    elif direction=="N":
        pts=[c for c in coords if c[1]>lat0]; key=lambda x:x[1]; func=max
    elif direction=="E":
        pts=[c for c in coords if c[2]>lon0]; key=lambda x:x[2]; func=max
    elif direction=="W":
        pts=[c for c in coords if c[2]<lon0]; key=lambda x:x[2]; func=min

    if not pts: return "ENTER MANUALLY"
    return func(pts,key=key)[0]

# ================= ✅ DISTANCE LOGIC (FIXED PROPER) =================
def get_distance_direction_endpoint(airway, base_wp, direction, distance_nm):

    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]
    adf=df[(df["AWID"]==airway)&(df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in adf.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],lat,lon))

    base_idx=next((i for i,c in enumerate(coords) if c[0]==base_wp),None)
    if base_idx is None: return "WAYPOINT NOT FOUND"

    lat0,lon0=coords[base_idx][1],coords[base_idx][2]

    dlat=distance_nm/60.0
    cos_lat=math.cos(math.radians(lat0))
    if cos_lat==0: cos_lat=0.0001
    dlon=distance_nm/(60.0*cos_lat)

    dir_map={
        "N":(dlat,0),"S":(-dlat,0),
        "E":(0,dlon),"W":(0,-dlon),
        "NE":(dlat/1.414,dlon/1.414),
        "NW":(dlat/1.414,-dlon/1.414),
        "SE":(-dlat/1.414,dlon/1.414),
        "SW":(-dlat/1.414,-dlon/1.414)
    }

    dlat,dlon=dir_map.get(direction,(0,0))
    target_lat=lat0+dlat
    target_lon=lon0+dlon

    for i in range(base_idx,len(coords)-1):
        _,lat1,lon1=coords[i]
        wp2,lat2,lon2=coords[i+1]

        if (
            min(lat1,lat2)<=target_lat<=max(lat1,lat2)
            and min(lon1,lon2)<=target_lon<=max(lon1,lon2)
        ):
            return wp2

    return "ENTER MANUALLY"

# ================= SEGMENTS =================
def extract_segments(text,airways):

    results=[]
    seen={aw:set() for aw in airways}

    for line in text.split("\n"):
        clean=normalize(line)
        matched=[aw for aw in airways if aw in clean]
        if not matched: continue

        handled=False

        # DISTANCE
        m=re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+(\d+)NM\s+(N|S|E|W|NE|NW|SE|SW)",clean)
        if m:
            handled=True
            base,dist,dirn=m.group(1),int(m.group(2)),m.group(3)

            for aw in matched:
                key=(base,dist,dirn)
                if key in seen[aw]: continue

                sec=get_distance_direction_endpoint(aw,base,dirn,dist)
                results.append(f"{aw} {base}-{sec}")
                seen[aw].add(key)

        # BTN
        m=re.search(r"BTN\s+([A-Z0-9]+)\s+AND\s+([A-Z0-9]+)",clean)
        if m:
            handled=True
            wp1,wp2=m.group(1),m.group(2)

            for aw in matched:
                key=frozenset([wp1,wp2])
                if key in seen[aw]: continue

                pts=df[df["AWID"]==aw]["WAYPOINT"].tolist()
                v1,v2=wp1 in pts,wp2 in pts

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
                if key in seen[aw]: continue

                sec=get_directional_endpoint(aw,wp,dirn)
                results.append(f"{aw} {wp}-{sec}")
                seen[aw].add(key)

        # FULL
        if not handled:
            for aw in matched:
                if not any(r.startswith(aw) for r in results):
                    results.append(f"{aw} {get_full_airway_segment(aw)}")

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

    if st.button("Parse"):
        aw=extract_airways(txt)
        st.session_state.airways=aw
        st.session_state.segments=extract_segments(txt,aw)

    if st.button("Clear"):
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
            st.text_area("Copy","\n".join(st.session_state.segments),260)

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
