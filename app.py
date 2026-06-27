import streamlit as st
import pandas as pd
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="NOTAM Airway Parser", layout="wide")

# =========================
# LOAD DATA (FROM REPO FILE)
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("waypoints.csv", engine="python")

    # Clean column names
    df.columns = ["AWID", "WAYPOINT", "COUNTRY", "COORDS"]

    # Normalize AWID
    df["AWID"] = df["AWID"].astype(str).str.strip().str.upper()

    return df

# =========================
# NORMALIZE TEXT
# =========================
def normalize_text(text):
    text = text.upper()

    # Remove unwanted chars except slash and space
    text = re.sub(r"[^A-Z0-9/ ]", " ", text)

    return text

# =========================
# EXTRACT AIRWAYS (HYBRID APPROACH)
# =========================
def extract_airways(notam_text, valid_airways_set):
    text = normalize_text(notam_text)

    # Split using space and slash
    tokens = re.split(r"[ /]+", text)

    tokens_set = set(tokens)

    # Intersection with real airway DB
    found_airways = sorted(tokens_set & valid_airways_set)

    return found_airways

# =========================
# GET FILTERED DATA
# =========================
def get_airway_data(df, airways):
    return df[df["AWID"].isin(airways)]

# =========================
# LOAD DATA
# =========================
df = load_data()

# Precompute airway set (VERY FAST LOOKUP)
valid_airways_set = set(df["AWID"].unique())

# =========================
# UI
# =========================
st.title("✈️ NOTAM Airway Parser")

st.success(f"✅ Loaded Airway Database | Total Airways: {len(valid_airways_set)}")

notam_text = st.text_area("📋 Paste NOTAM text here", height=300)

if st.button("🚀 Parse NOTAM"):
    if not notam_text.strip():
        st.warning("⚠️ Please paste NOTAM text")
    else:
        # Extract airways
        airways = extract_airways(notam_text, valid_airways_set)

        st.subheader(f"✅ Detected Airways ({len(airways)})")
        st.write(airways)

        if airways:
            df_filtered = get_airway_data(df, airways)

            st.subheader("📊 Airway Details")

            for airway, group in df_filtered.groupby("AWID"):
                st.markdown(f"### 🛫 {airway}")

                st.dataframe(
                    group[["WAYPOINT", "COUNTRY"]],
                    use_container_width=True
                )

            # Download button
            csv = df_filtered.to_csv(index=False).encode("utf-8")

            st.download_button(
                "⬇️ Download Output CSV",
                csv,
                "airway_output.csv",
                "text/csv"
            )

        else:
            st.warning("❌ No airways detected in NOTAM")
