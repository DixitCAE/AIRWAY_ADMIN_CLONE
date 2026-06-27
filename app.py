import streamlit as st
import pandas as pd
import re
import math

st.set_page_config(layout="wide")

# ================== LOAD ==================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv")
    df.columns = ["AWID","WAYPOINT","COUNTRY","COORDS"]
    df["AWID"] = df["AWID"].str.strip().str.upper()
    return df

df = load_data()
valid_airways = set(df["AWID"])

# ================== PARSE ==================
def parse_coord(coord):
    try:
        lat = float(coord[0:2]) + float(coord[2:4])/60 + float(coord[4:6])/3600
        if coord[6]=="S": lat *= -1

        lon = float(coord[7:10]) + float(coord[10:12])/60 + float(coord[12:14])/3600
        if coord[14]=="W": lon *= -1

        return lat, lon
    except:
        return None, None

# ================== VISUAL FIXED ==================
def get_visual_block(coords_list):

    pts = [(w,lat,lon) for (w,c,lat,lon) in coords_list if lat is not None]

    if len(pts) < 2:
        return ""

    # ✅ TRUE ROUTE FLOW (FIX)
    start = pts[0]
    end = pts[-1]

    lat1, lon1 = start[1], start[2]
    lat2, lon2 = end[1], end[2]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    angle = abs(math.degrees(math.atan2(dlat, dlon)))

    # ✅ VERTICAL
    if angle > 60:
        top = start if lat1 > lat2 else end
        bottom = end if lat1 > lat2 else start

        return f"""
        <div class="viz">
            <div>{top[0]}</div>
            <div class="line-v"></div>
            <div>{bottom[0]}</div>
        </div>
        """

    # ✅ HORIZONTAL
    elif angle < 30:
        left = start if lon1 < lon2 else end
        right = end if lon1 < lon2 else start

        return f"""
        <div class="viz-h">
            <div class="l">{left[0]}</div>
            <div class="r">{right[0]}</div>
            <div class="line-h"></div>
        </div>
        """

    # ✅ DIAGONAL (FINAL FIX)
    else:

        x1 = 15 if lon1 < lon2 else 85
        x2 = 85 if lon1 < lon2 else 15

        y1 = 15 if lat1 > lat2 else 85
        y2 = 85 if lat1 > lat2 else 15

        return f"""
        <div class="viz-svg">
            <div style="left:{x1}%; top:{y1}%;">{start[0]}</div>
            <div style="left:{x2}%; top:{y2}%;">{end[0]}</div>

            <svg width="100%" height="100%">
                <line x1="{x1}%" y1="{y1}%"
                      x2="{x2}%" y2="{y2}%"
                      stroke="red" stroke-width="3"/>
            </svg>
        </div>
        """

# ================== NOTAM ==================
def normalize(text):
    text=text.upper()
    text=re.sub(r"[^A-Z0-9/ ]"," ",text)
    return text

def extract_airways(text):
    tokens=re.split(r"[ /]+",normalize(text))
    return sorted(set(tokens)&valid_airways)

# ================== CSS ==================
st.markdown("""
<style>

.block-container{padding-top:1.5rem;}

.tile{
background:#0e1117;border:1px solid #333;
border-radius:8px;padding:10px;
height:320px;display:flex;gap:10px;
}

.text{width:60%;overflow-y:auto;}
.vizbox{width:40%;display:flex;align-items:center;justify-content:center;}

.line-v{width:3px;height:90px;background:red;margin:auto;}
.line-h{height:3px;width:80%;background:red;margin:20px auto;}

.viz{text-align:center;}
.viz-h{position:relative;}

.l{position:absolute;left:0;}
.r{position:absolute;right:0;}

.viz-svg{
position:relative;width:100%;height:120px;
}
.viz-svg div{
position:absolute;font-size:12px;
transform:translate(-50%,-50%);
}

.airway-list{
line-height:1.1;font-size:13px;
max-height:180px;overflow-y:auto;
}

</style>
""",unsafe_allow_html=True)

# ================== STATE ==================
if "airways" not in st.session_state:
    st.session_state.airways=[]

# ================== LAYOUT ==================
left,right=st.columns([1,3])

# LEFT
with left:
    st.markdown("## 📋 NOTAM INPUT")

    txt=st.text_area("NOTAM",height=200,label_visibility="collapsed")

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

# RIGHT
with right:
    st.markdown("## ✈️ Airway Details")

    for i in range(0,len(st.session_state.airways),3):
        cols=st.columns(3)

        for col,airway in zip(cols,st.session_state.airways[i:i+3]):
            with col:
                group=df[df["AWID"]==airway]

                html='<div class="tile">'

                # text
                html+='<div class="text">'
                html+=f"<b style='color:#4CAF50'>{airway}</b><br>"
                coords=[]

                for _,r in group.iterrows():
                    lat,lon=parse_coord(r["COORDS"])
                    coords.append((r["WAYPOINT"],r["COUNTRY"],lat,lon))
                    html+=f"{r['WAYPOINT']} ({r['COUNTRY']})<br>"

                html+='</div>'

                # viz
                html+='<div class="vizbox">'
                html+=get_visual_block(coords)
                html+='</div>'

                html+='</div>'

                st.markdown(html,unsafe_allow_html=True)
