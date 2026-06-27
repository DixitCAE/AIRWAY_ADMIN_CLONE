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
.viz-container { width:40%; display:flex; align-items:center; justify-content:center; }
.line-vertical { width:3px; height:80px; background:#ff4d4d; margin:auto;}
.viz-horizontal { position:relative; text-align:center;}
.h-label { position:absolute; top:-5px; font-size:11px;}
.h-label.left { left:0;} .h-label.right { right:0;}
.line-horizontal { height:3px; width:70%; background:#ff4d4d; margin:15px auto;}
.tile-title { color:#4CAF50; font-weight:bold; margin-bottom:6px;}
.airway-list div { margin:0; line-height:1.2;}
.output-box textarea { white-space:nowrap !important;}
</style>
""", unsafe_allow_html=True)

# ================= ✅ FIXED COORD PARSER =================
def parse_coord(coord):
    try:
        coord = coord.strip()

        # FULL FORMAT
        if len(coord) >= 15:
            lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
            if coord[6] == "S": lat *= -1

            lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
            if coord[14] == "W": lon *= -1

        # SHORT FORMAT
        else:
            lat = float(coord[0:2]) + float(coord[2:4])/60
            if coord[4] == "S": lat *= -1

            lon = float(coord[5:8]) + float(coord[8:10])/60
            if coord[10] == "W": lon *= -1

        return lat, lon
    except:
        return None, None

# ================= ✅ VISUAL FIX =================
def get_visual_block(coords_list):

    coords = [(w,lat,lon) for (w,c,lat,lon) in coords_list
              if lat is not None and lon is not None]

    if len(coords) < 2:
        return "<div style='text-align:center;color:#888'>•</div>"

    north=max(coords,key=lambda x:x[1])
    south=min(coords,key=lambda x:x[1])
    east=max(coords,key=lambda x:x[2])
    west=min(coords,key=lambda x:x[2])

    dlat=north[1]-south[1]
    dlon=east[2]-west[2]

    if abs(dlat)>=abs(dlon):
        return f"""
        <div style="text-align:center">
            {north[0]}<br>
            <div class='line-vertical'></div>
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
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+", normalize(t))) & valid_airways)

# ================= HELPERS =================
def get_airway_coords(airway):
    allowed=["KZ","K1","K2","K3","K4","K5","K6","K7"]
    g=df[(df["AWID"]==airway) & (df["COUNTRY"].isin(allowed))]

    coords=[]
    for _,r in g.iterrows():
        lat,lon=parse_coord(r["COORDS"])
        coords.append((r["WAYPOINT"],lat,lon))
    return coords

def get_full_airway_segment(airway):
    coords=get_airway_coords(airway)
    if not coords: return "ENTER MANUALLY"
    return f"{coords[0][0]}-{coords[-1][0]}"

def get_directional_endpoint(airway,wp,dirn):
    coords=get_airway_coords(airway)
    base=next((c for c in coords if c[0]==wp),None)
    if not base: return "WAYPOINT NOT FOUND"

    lat0,lon0=base[1],base[2]

    if dirn=="S":
        pts=[c for c in coords if c[1]<lat0]; key=lambda x:x[1]; f=min
    elif dirn=="N":
        pts=[c for c in coords if c[1]>lat0]; key=lambda x:x[1]; f=max
    elif dirn=="W":
        pts=[c for c in coords if c[2]<lon0]; key=lambda x:x[2]; f=min
    elif dirn=="E":
        pts=[c for c in coords if c[2]>lon0]; key=lambda x:x[2]; f=max

    return f(pts,key=key)[0] if pts else "ENTER MANUALLY"

# ✅ DISTANCE (FINAL FIX)
def get_distance_endpoint(airway,base,dirn,dist):

    coords=get_airway_coords(airway)

    idx=next((i for i,c in enumerate(coords) if c[0]==base),None)
    if idx is None: return "WAYPOINT NOT FOUND"

    lat0,lon0=coords[idx][1],coords[idx][2]

    dlat=dist/60
    cos_lat=math.cos(math.radians(lat0)) or 0.0001
    dlon=dist/(60*cos_lat)

    dm={
        "N":(dlat,0),"S":(-dlat,0),
        "E":(0,dlon),"W":(0,-dlon),
        "NE":(dlat/1.414,dlon/1.414),
        "NW":(dlat/1.414,-dlon/1.414),
        "SE":(-dlat/1.414,dlon/1.414),
        "SW":(-dlat/1.414,-dlon/1.414)
    }

    dl,do=dm.get(dirn,(0,0))
    tlat,tlon=lat0+dl,lon0+do

    for i in range(idx,len(coords)-1):
        _,la1,lo1=coords[i]
        wp2,la2,lo2=coords[i+1]

        if (min(la1,la2)<=tlat<=max(la1,la2) and
            min(lo1,lo2)<=tlon<=max(lo1,lo2)):
            return wp2

    return "ENTER MANUALLY"

# ================= SEGMENTS =================
def extract_segments(text,airways):

    results=[]
    seen={a:set() for a in airways}

    for line in text.split("\n"):
        clean=normalize(line)
        matched=[a for a in airways if a in clean]
        if not matched: continue

        handled=False

        # DISTANCE
        m=re.search(r"BTN\s+(\w+)\s+AND\s+(\d+)NM\s+(N|S|E|W|NE|NW|SE|SW)",clean)
        if m:
            handled=True
            base,dist,dirn=m.group(1),int(m.group(2)),m.group(3)
            for a in matched:
                if (base,dist,dirn) not in seen[a]:
                    sec=get_distance_endpoint(a,base,dirn,dist)
                    results.append(f"{a} {base}-{sec}")
                    seen[a].add((base,dist,dirn))

        # BTN
        m=re.search(r"BTN\s+(\w+)\s+AND\s+(\w+)",clean)
        if m:
            handled=True
            wp1,wp2=m.group(1),m.group(2)
            for a in matched:
                key=frozenset([wp1,wp2])
                if key not in seen[a]:
                    results.append(f"{a} {wp1}-{wp2}")
                    seen[a].add(key)

        # DIR
        d=re.search(r"(N|S|E|W)\s+OF\s+(\w+)",clean)
        if d:
            handled=True
            dirn,wp=d.groups()
            for a in matched:
                if (wp,dirn) not in seen[a]:
                    sec=get_directional_endpoint(a,wp,dirn)
                    results.append(f"{a} {wp}-{sec}")
                    seen[a].add((wp,dirn))

        # FULL
        if not handled:
            for a in matched:
                results.append(f"{a} {get_full_airway_segment(a)}")

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

    c1,c2=st.columns([1,1.7])

    with c1:
        st.markdown("### ✅ Airways")
        for a in st.session_state.airways:
            st.markdown(f"• {a}")

    with c2:
        st.markdown("### 📌 Output")
        if st.session_state.segments:
            st.text_area("", "\n".join(st.session_state.segments), height=260)

# ================= RIGHT =================
with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0,len(st.session_state.airways),3):
        cols=st.columns(3)
        for col,aw in zip(cols,st.session_state.airways[i:i+3]):
            with col:
                g=df[df["AWID"]==aw]

                html='<div class="tile"><div class="text-block">'
                html+=f'<div class="tile-title">{aw}</div>'

                coords=[]
                for _,r in g.iterrows():
                    lat,lon=parse_coord(r["COORDS"])
                    coords.append((r["WAYPOINT"],r["COUNTRY"],lat,lon))
                    html+=f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html+='</div><div class="viz-container">'
                html+=get_visual_block(coords)
                html+='</div></div>'

                st.markdown(html, unsafe_allow_html=True)
