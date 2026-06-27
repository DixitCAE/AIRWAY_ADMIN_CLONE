import streamlit as st
import pandas as pd
import re
import math

st.set_page_config(layout="wide")

# ================= LOAD =================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv")
    df.columns = ["AWID","WAYPOINT","COUNTRY","COORDS"]
    df["AWID"] = df["AWID"].astype(str).str.upper().str.strip()
    df["WAYPOINT"] = df["WAYPOINT"].astype(str).str.upper().str.strip()
    return df

df = load_data()
valid_airways=set(df["AWID"].unique())

# ================= CSS =================
st.markdown("""
<style>
.tile{background:#0e1117;border:1px solid #333;border-radius:8px;padding:12px;height:300px;display:flex;gap:10px;}
.text-block{width:60%;overflow:auto;}
.viz-container{width:40%;display:flex;align-items:center;justify-content:center;}
.line-vertical{width:3px;height:80px;background:#ff4d4d;margin:auto;}
.viz-horizontal{position:relative;text-align:center;}
.h-label{position:absolute;top:-5px;font-size:11px;}
.h-label.left{left:0;} .h-label.right{right:0;}
.line-horizontal{height:3px;width:70%;background:#ff4d4d;margin:15px auto;}
.tile-title{color:#4CAF50;font-weight:bold;}
</style>
""",unsafe_allow_html=True)

# ================= ✅ ROBUST COORD PARSER =================
def parse_coord(c):
    try:
        c=c.strip().replace(" ","")
        m=re.match(r"(\d{2})(\d{2})?(\d{2})?([NS])(\d{3})(\d{2})?(\d{2})?([EW])",c)
        if not m: return None,None

        lat=float(m.group(1))
        lat+=float(m.group(2) or 0)/60
        lat+=float(m.group(3) or 0)/3600

        lon=float(m.group(5))
        lon+=float(m.group(6) or 0)/60
        lon+=float(m.group(7) or 0)/3600

        if m.group(4)=="S": lat*=-1
        if m.group(8)=="W": lon*=-1

        return lat,lon
    except:
        return None,None

# ================= ✅ YOUR WORKING VISUAL =================
def get_visual_block(coords_list):
    coords=[(w,lat,lon) for (w,c,lat,lon) in coords_list if lat is not None]
    if len(coords)<2: return ""

    north=max(coords,key=lambda x:x[1])
    south=min(coords,key=lambda x:x[1])
    east=max(coords,key=lambda x:x[2])
    west=min(coords,key=lambda x:x[2])

    if abs(north[1]-south[1])>=abs(east[2]-west[2]):
        return f"""
        <div>
            {north[0]}
            <div class='line-vertical'></div>
            {south[0]}
        </div>
        """
    else:
        return f"""
        <div class='viz-horizontal'>
            <div class='h-label left'>{west[0]}</div>
            <div class='h-label right'>{east[0]}</div>
            <div class='line-horizontal'></div>
        </div>
        """

# ================= PARSE =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+",normalize(t))) & valid_airways)

# ================= HELPERS =================
def airway_coords(a):
    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]
    g=df[(df["AWID"]==a)&(df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in g.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],r["COUNTRY"],lat,lon))
    return coords

# ================= ✅ DIRECTION =================
def directional_endpoint(a,wp,dirn):
    coords=airway_coords(a)
    base=next((c for c in coords if c[0]==wp),None)
    if not base: return "WAYPOINT NOT FOUND"

    lat0,lon0=base[2],base[3]

    pts=[]
    for w,c,lat,lon in coords:
        if dirn=="S" and lat<lat0: pts.append((w,lat))
        if dirn=="N" and lat>lat0: pts.append((w,lat))
        if dirn=="E" and lon>lon0: pts.append((w,lon))
        if dirn=="W" and lon<lon0: pts.append((w,lon))

    if not pts: return "ENTER MANUALLY"
    return min(pts,key=lambda x:abs(x[1]))[0]

# ================= ✅ DISTANCE =================
def distance_endpoint(a,base,dirn,dist):
    coords=[(w,lat,lon) for (w,c,lat,lon) in airway_coords(a)]
    idx=next((i for i,x in enumerate(coords) if x[0]==base),None)
    if idx is None: return "WAYPOINT NOT FOUND"
    return coords[idx+1][0] if idx+1<len(coords) else "ENTER MANUALLY"

# ================= SEGMENTS =================
def extract_segments(txt,airways):

    res=[]
    seen=set()

    for line in txt.split("\n"):
        clean=normalize(line)

        if "CLSD" not in clean: continue

        matched=[a for a in airways if a in clean]

        # DISTANCE
        m=re.search(r"BTN (\w+) AND (\d+)NM (SE)",clean)
        if m:
            base,dist,dirn=m.group(1),int(m.group(2)),m.group(3)
            for a in matched:
                key=(a,base,dist)
                if key in seen: continue
                res.append(f"{a} {base}-{distance_endpoint(a,base,dirn,dist)}")
                seen.add(key)
            continue

        # BTN
        m=re.search(r"BTN (\w+) AND (\w+)",clean)
        if m:
            wp1,wp2=m.group(1),m.group(2)
            for a in matched:
                key=(a,wp1,wp2)
                if key in seen: continue
                res.append(f"{a} {wp1}-{wp2}")
                seen.add(key)
            continue

        # DIR
        m=re.search(r"(N|S|E|W) OF (\w+)",clean)
        if m:
            dirn,wp=m.groups()
            for a in matched:
                key=(a,wp,dirn)
                if key in seen: continue
                res.append(f"{a} {wp}-{directional_endpoint(a,wp,dirn)}")
                seen.add(key)
            continue

        # FULL
        for a in matched:
            coords=airway_coords(a)
            if coords:
                res.append(f"{a} {coords[0][0]}-{coords[-1][0]}")

    return res

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

    col1,col2=st.columns([1,1.7])

    with col1:
        for a in st.session_state.airways:
            st.write("•",a)

    with col2:
        st.text_area("Output","\n".join(st.session_state.segments),
                     height=260,label_visibility="collapsed")

# ================= RIGHT =================
with right:
    for i in range(0,len(st.session_state.airways),3):
        cols=st.columns(3)

        for col,a in zip(cols,st.session_state.airways[i:i+3]):
            with col:
                coords=airway_coords(a)

                html="<div class='tile'><div class='text-block'>"
                html+=f"<div class='tile-title'>{a}</div>"

                for w,c,lat,lon in coords:
                    html+=f"{w} ({c})<br>"

                html+="</div><div class='viz-container'>"
                html+=get_visual_block(coords)
                html+="</div></div>"

                st.markdown(html,unsafe_allow_html=True)
