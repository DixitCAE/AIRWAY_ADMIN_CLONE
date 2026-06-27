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
    df["AWID"] = df["AWID"].str.strip().str.upper()
    return df

df = load_data()
valid_airways = set(df["AWID"])

# ================= COORD =================
def parse_coord(coord):
    try:
        lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
        if coord[6]=="S": lat *= -1

        lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
        if coord[14]=="W": lon *= -1

        return lat, lon
    except:
        return None, None

# ================= ✅ FINAL VISUAL =================
def build_svg(start, end):

    lat1, lon1 = start[1], start[2]
    lat2, lon2 = end[1], end[2]

    dx = lon2 - lon1
    dy = lat2 - lat1

    # normalize placement
    x1 = 20 if dx > 0 else 80
    x2 = 80 if dx > 0 else 20

    y1 = 20 if dy < 0 else 80
    y2 = 80 if dy < 0 else 20

    # labels
    return f"""
    <div class="viz">
        <div class="pt" style="left:{x1}%; top:{y1}%;">{start[0]}</div>
        <div class="pt" style="left:{x2}%; top:{y2}%;">{end[0]}</div>

        <svg width="100%" height="100%">
            <line x1="{x1}%" y1="{y1}%"
                  x2="{x2}%" y2="{y2}%"
                  stroke="#ff4d4d" stroke-width="3"/>
        </svg>
    </div>
    """

def get_visual(coords):

    pts = [(w,lat,lon) for (w,c,lat,lon) in coords if lat is not None]

    if len(pts) < 2:
        return ""

    start = pts[0]
    end   = pts[-1]

    lat1, lon1 = start[1], start[2]
    lat2, lon2 = end[1], end[2]

    dx = abs(lon2 - lon1)
    dy = abs(lat2 - lat1)

    # vertical
    if dy > dx * 1.5:
        top = start if lat1 > lat2 else end
        bottom = end if lat1 > lat2 else start

        return f"""
        <div class="viz v">
            <div>{top[0]}</div>
            <div class="linev"></div>
            <div>{bottom[0]}</div>
        </div>
        """

    # horizontal
    elif dx > dy * 1.5:
        left = start if lon1 < lon2 else end
        right = end if lon1 < lon2 else start

        return f"""
        <div class="viz h">
            <div class="left">{left[0]}</div>
            <div class="right">{right[0]}</div>
            <div class="lineh"></div>
        </div>
        """

    # diagonal ✅ FIXED
    else:
        return build_svg(start, end)

# ================= NOTAM =================
def normalize(t):
    return re.sub(r"[^A-Z0-9/ ]"," ",t.upper())

def extract_airways(t):
    return sorted(set(re.split(r"[ /]+",normalize(t))) & valid_airways)

# ================= CSS =================
st.markdown("""
<style>

.block-container{padding-top:1.5rem;}

.tile{
background:#0e1117;border:1px solid #333;
border-radius:8px;padding:10px;
display:flex;gap:10px;height:320px;
}

.text{width:60%;overflow-y:auto;}
.vizbox{width:40%;display:flex;align-items:center;justify-content:center;}

.v{ text-align:center;}
.linev{width:3px;height:90px;background:#ff4d4d;margin:auto;}

.h{ position:relative;}
.lineh{height:3px;width:80%;background:#ff4d4d;margin:20px auto;}
.left{position:absolute;left:0;}
.right{position:absolute;right:0;}

.viz{
position:relative;width:100%;height:120px;
}
.viz .pt{
position:absolute;font-size:11px;
transform:translate(-50%,-50%);
}

.airway-list{
line-height:1.1;font-size:13px;
max-height:180px;overflow:auto;
}

</style>
""",unsafe_allow_html=True)

# ================= UI =================
if "airways" not in st.session_state:
    st.session_state.airways=[]

left,right=st.columns([1,3])

with left:
    st.markdown("## 📋 NOTAM INPUT")

    txt=st.text_area("NOTAM",200,label_visibility="collapsed")

    c1,c2=st.columns(2)
    if c1.button("Parse"):
        st.session_state.airways=extract_airways(txt)
    if c2.button("Clear"):
        st.session_state.airways=[]

    st.markdown("### ✅ Airways")

    st.markdown('<div class="airway-list">',unsafe_allow_html=True)
    for a in st.session_state.airways:
        st.markdown(f"<div>• {a}</div>",unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0,len(st.session_state.airways),3):
        cols=st.columns(3)

        for col,a in zip(cols,st.session_state.airways[i:i+3]):
            with col:
                g=df[df["AWID"]==a]

                html='<div class="tile">'
                html+='<div class="text">'
                html+=f"<b style='color:#4CAF50'>{a}</b><br>"

                coords=[]
                for _,r in g.iterrows():
                    lat,lon=parse_coord(r["COORDS"])
                    coords.append((r["WAYPOINT"],r["COUNTRY"],lat,lon))
                    html+=f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html+='</div>'
                html+='<div class="vizbox">'
                html+=get_visual(coords)
                html+='</div>'
                html+='</div>'

                st.markdown(html,unsafe_allow_html=True)
