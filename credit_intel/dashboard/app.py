import json
import requests
import pandas as pd
import streamlit as st

API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Credit Intel", layout="wide")
st.title("Real-Time Explainable Credit Intelligence")

@st.cache_data(ttl=300)
def get_issuers():
    r = requests.get(f"{API_BASE}/issuers", timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=180)
def get_scores(ticker: str):
    r = requests.get(f"{API_BASE}/scores/{ticker}", timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=180)
def get_features(ticker: str):
    r = requests.get(f"{API_BASE}/features/{ticker}", timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=180)
def get_events(ticker: str):
    r = requests.get(f"{API_BASE}/events/{ticker}", timeout=20)
    r.raise_for_status()
    return r.json()

cols = st.columns([1,3])
with cols[0]:
    issuers = get_issuers()
    tickers = [i["ticker"] for i in issuers]
    ticker = st.selectbox("Issuer", tickers)
    if st.button("Refresh Now"):
        try:
            r = requests.post(f"{API_BASE}/refresh", timeout=60)
            st.success("Refresh triggered")
        except Exception as e:
            st.error(f"Refresh failed: {e}")

with cols[1]:
    scores = get_scores(ticker)
    if scores:
        df = pd.DataFrame(scores)
        df["as_of"] = pd.to_datetime(df["as_of"]) 
        st.subheader("Score Trend")
        st.line_chart(df.set_index("as_of")["score"])
        latest = df.iloc[0]
        st.metric("Latest Score", f"{latest['score']:.1f}")
        st.write(latest["summary"])

        st.subheader("Feature Contributions")
        contrib = pd.Series(latest["contributions"]).sort_values()
        st.bar_chart(contrib)
    else:
        st.info("No scores yet. Try Refresh.")

st.subheader("Latest Features")
feats = get_features(ticker)
if feats:
    st.json(feats)

st.subheader("Recent Events")
evts = get_events(ticker)
if evts:
    evdf = pd.DataFrame(evts)
    st.dataframe(evdf[["published_at","title","event_type","sentiment","url"]], use_container_width=True)