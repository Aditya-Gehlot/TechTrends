"""Streamlit dashboard starter for Tech Trends Intelligence.

Run with: `streamlit run dashboard/streamlit_app.py`
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

try:
    API_URL = st.secrets.get("API_URL", "http://localhost:8000")
except Exception:
    API_URL = "http://localhost:8000"


st.set_page_config(page_title="Tech Trends Dashboard", layout="wide")
st.title("Tech Trends Intelligence — Dashboard")

st.sidebar.header("Controls")
limit = st.sidebar.slider("Top N", 5, 50, 10)

st.header("Trending Technologies")
try:
    r = requests.get(f"{API_URL}/trends/top?limit={limit}")
    data = r.json().get("top", [])
    df = pd.DataFrame(data)
    if not df.empty:
        fig = px.bar(df, x="tech", y="score", title="Top technologies by popularity score")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trends data available. Run processing + feature pipelines.")
except Exception:
    st.error("Could not reach API. Ensure the API is running at %s" % API_URL)

st.header("Forecast a Technology")
tech = st.text_input("Technology name (exact)")
if st.button("Get Forecast") and tech:
    try:
        r = requests.get(f"{API_URL}/forecast/{tech}")
        if r.status_code == 200:
            resp = r.json()
            st.subheader(f"{resp.get('technology')} — {resp.get('trend')}")
            st.write("Confidence:", resp.get("confidence"))
            # show numeric predicted growth if present
            pg = resp.get("predicted_growth")
            if pg is not None:
                st.metric("Predicted growth (fraction)", f"{pg:.2%}")
            # feature importances
            fi = resp.get("feature_importances") or {}
            if fi:
                import pandas as _pd
                import plotly.express as _px

                fi_df = _pd.DataFrame([{"feature": k, "importance": v} for k, v in fi.items()])
                fi_df = fi_df.sort_values("importance", ascending=False).head(10)
                fig_fi = _px.bar(fi_df, x="feature", y="importance", title="Top feature importances")
                st.plotly_chart(fig_fi, use_container_width=True)
            st.json(resp)
        else:
            st.error(r.text)
    except Exception as e:
        st.error(f"Error fetching forecast: {e}")
