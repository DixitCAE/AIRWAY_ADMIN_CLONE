import streamlit as st
import pandas as pd
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="NOTAM Airway Parser", layout="wide")

# =========================
# LOAD DATA (Cached)
# =========================
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path, engine="python")

    # Clean column names
    df.columns = ["AWID", "WAYPOINT", "COUNTRY", "COORDS"]

    # Normalize AWID
    df["AWID"] = df["AWID"].astype(str).str.strip().str.upper()

    return df

# =========================
# NORMALIZE NOTAM TEXT
# =========================
def normalize_text(text):
    text = text.upper()

    # Remove all unwanted chars except slash and space
    text = re.sub(r"[^A-Z0-9/ ]", " ", text)

    return text

# =========================
# EXTRACT AIRWAYS (HYBRID)
# =========================
def extract_airways(notam_text, valid_airways_set):
    text = normalize_text(notam_text)

    # Split tokens using space + slash
    tokens = re.split(r"[ /]+", text)

    tokens_set = set(tokens)

    # INTERSECTION → accurate + fast
    found_airways = sorted(tokens_set & valid_airways_set)

    return found_airways

# =========================
# GET AIRWAY DATA
# =========================
def get_airway_data(df, airways):
    return df[df["AWID"].isin(airways)]

# =========================
# UI
# =========================
st.title("✈️ NOTAM Airway Parser (Production Ready)")

uploaded_file = st.file_uploader("Upload airway dataset (CSV)", type=["csv"])

if uploaded_file:
    df = load_data(uploaded_file)

    # Create valid airway set
    valid_airways_set = set(df["AWID"].unique())

    st.success(f"✅ Data loaded | Total Airways: {len(valid_airways_set)}")

    notam_text = st.text_area("📋 Paste NOTAM text here", height=300)

    if st.button("🚀 Parse NOTAM"):

        if not notam_text.strip():
            st.warning("Please enter NOTAM text")
        else:
            # Extract airways
            airways = extract_airways(notam_text, valid_airways_set)

            st.subheader(f"✅ Detected Airways ({len(airways)})")
            st.write(airways)

            if airways:
                df_filtered = get_airway_data(df, airways)

                # Display grouped output
                st.subheader("📊 Airway Details")

                for airway, group in df_filtered.groupby("AWID"):
                    st.markdown(f"### 🛫 {airway}")
                    st.dataframe(
                        group[["WAYPOINT", "COUNTRY"]],
                        use_container_width=True,
                    )

                # Download option
                csv = df_filtered.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "⬇️ Download Result CSV",
                    csv,
                    "airway_output.csv",
                    "text/csv"
                )
            else:
                st.warning("No airways detected")
