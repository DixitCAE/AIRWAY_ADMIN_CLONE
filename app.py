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
.tile-title {color:#4CAF50;font-weight:bold;}
.airway-list div {margin:0;line-height:1.2;}
</style>
""", unsafe_allow_html=True)

# ================= COORD =================
def parse_coord(coord):
    try:
        coord=coord.strip()

        if len(coord)>=15:
            lat=float(coord[0:2])+float(coord[2:4])/60+float(coord[4:6])/3600
            if coord[6]=="S": lat*=-1

            lon=float(coord[7:10])+float(coord[10:12])/60+float(coord[12:14])/3600
            if coord[14]=="W": lon*=-1
        else:
            lat=float(coord[0:2])+float(coord[2:4])/60
            if coord[4]=="S": lat*=-1

            lon=float(coord[5:8])+float(coord[8:10])/60
            if coord[10]=="W": lon*=-1

        return lat,lon
    except:
        return None,None

# ================= VISUAL FIX =================
def get_visual_block(coords_list):

    coords=[(w,lat,lon) for (w,c,lat,lon) in coords_list if lat is not None and lon is not None]

    if len(coords)<2:
        return "<div style='color:#666'>•</div>"

    north=max(coords,key=lambda x:x[1])
    south=min(coords,key=lambda x:x[1])
    east=max(coords,key=lambda x:x[2])
    west=min(coords,key=lambda x:x[2])

    if abs(north[1]-south[1])>=abs(east[2]-west[2]):
        return f"<div>{north[0]}<br><div class='line-vertical'></div>{south[0]}</div>"
    else:
        return f"<div class='viz-horizontal'><span class='h-label left'>{west[0]}</span><span class='h-label right'>{east[0]}</span><div class='line-horizontal'></div></div>"

# ================= PARSE =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+", normalize(t))) & valid_airways)

# ================= HELPERS =================
def get_airway_coords(airway):
    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]
    g=df[(df["AWID"]==airway)&(df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in g.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],r["COUNTRY"],lat,lon))
    return coords

# ================= DISTANCE =================
def get_distance_endpoint(airway,base,dirn,dist):

    coords=[(w,lat,lon) for (w,c,lat,lon) in get_airway_coords(airway)]

    idx=next((i for i,c in enumerate(coords) if c[0]==base),None)
    if idx is None:
        return "WAYPOINT NOT FOUND"

    lat0,lon0=coords[idx][1],coords[idx][2]

    dlat=dist/60
    dlon=dist/(60*math.cos(math.radians(lat0)) or 1)

    dm={"SE":(-dlat/1.414,dlon/1.414)}

    dl,do=dm.get(dirn,(0,0))
    target_lat, target_lon=lat0+dl, lon0+do

    for i in range(idx,len(coords)-1):
        _,la1,lo1=coords[i]
        wp2,la2,lo2=coords[i+1]

        if min(la1,la2)<=target_lat<=max(la1,la2):
            return wp2

    return "ENTER MANUALLY"

# ================= SEGMENTS =================
def extract_segments(text,airways):

    results=[]
    seen=set()

    for line in text.split("\n"):
        clean=normalize(line)

        # ✅ ONLY CLSD lines processed
        if "CLSD" not in clean:
            continue

        matched=[a for a in airways if a in clean]

        # ✅ DISTANCE
        m=re.search(r"BTN\s+(\w+)\s+AND\s+(\d+)NM\s+(SE)",clean)
        if m:
            base,dist,dirn=m.group(1),int(m.group(2)),m.group(3)

            for a in matched:
                key=(a,base,dist,dirn)
                if key in seen: continue

                sec=get_distance_endpoint(a,base,dirn,dist)
                results.append(f"{a} {base}-{sec}")
                seen.add(key)

        # ✅ BTN
        elif "BTN" in clean:
            m=re.search(r"BTN\s+(\w+)\s+AND\s+(\w+)",clean)
            if m:
                wp1,wp2=m.group(1),m.group(2)

                for a in matched:
                    key=frozenset([a,wp1,wp2])
                    if key in seen: continue

                    results.append(f"{a} {wp1}-{wp2}")
                    seen.add(key)

        # ✅ DIRECTION
        elif " OF " in clean:
            d=re.search(r"(N|S|E|W)\s+OF\s+(\w+)",clean)
            if d:
                dirn,wp=d.groups()

                for a in matched:
                    key=(a,wp,dirn)
                    if key in seen: continue

                    results.append(f"{a} {wp}-ENTER MANUALLY")
                    seen.add(key)

        # ✅ FULL
        else:
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
left,right=st.columns([1,3])

with left:
    txt=st.text_area("NOTAM",height=200)

    if st.button("Parse"):
        aw=extract_airways(txt)
        st.session_state.airways=aw
        st.session_state.segments=extract_segments(txt,aw)

    if st.button("Clear"):
        st.session_state.airways=[]
        st.session_state.segments=[]

    for a in st.session_state.airways:
        st.write("•",a)

    st.text_area("", "\n".join(st.session_state.segments), height=250)

# ================= RIGHT =================
with right:
    for i in range(0,len(st.session_state.airways),3):
        cols=st.columns(3)

        for col,aw in zip(cols,st.session_state.airways[i:i+3]):
            with col:
                coords=get_airway_coords(aw)

                html='<div class="tile"><div class="text-block">'
                html+=f'<div class="tile-title">{aw}</div>'

                for w,c,lat,lon in coords:
                    html+=f"{w} ({c})<br>"

                html+='</div><div class="viz-container">'
                html+=get_visual_block(coords)
                html+='</div></div>'

                st.markdown(html,unsafe_allow_html=True)
