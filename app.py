"""
BidLite — Vector-Powered Procurement Intelligence
Author: Shakir
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from core.parser import load_sample_data, parse_excel, parse_pdf_text
from core.embedder import item_to_text, embed_texts
from core.vector_store import (
    get_client,
    upsert_items,
    collection_exists_and_populated,
    drop_collection,
)

load_dotenv()

st.set_page_config(
    page_title="BidLite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/ChaqBD/BidLite/main/assets/logo.png",
             use_column_width=True) if False else None
    st.title("⚡ BidLite")
    st.caption("Vector-Powered Procurement Intelligence")
    st.divider()

    data_source = st.radio(
        "Data Source",
        ["Use Sample Data (Project Bimbi)", "Upload QCS File"],
        index=0,
    )

    uploaded_file = None
    if data_source == "Upload QCS File":
        uploaded_file = st.file_uploader(
            "Upload QCS (.xlsx or .pdf)",
            type=["xlsx", "xls", "pdf"],
        )

    st.divider()
    if st.button("🔄 Reset & Re-index", use_container_width=True):
        st.session_state.pop("df", None)
        st.session_state.pop("indexed", None)
        try:
            drop_collection(get_client())
        except Exception:
            pass
        st.success("Reset complete.")
        st.rerun()

    st.divider()
    st.caption("Built for Qdrant Hackathon 2026")


# ── Load / Index Data ─────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_df(source: str, _file_bytes=None, _file_name=None) -> pd.DataFrame:
    if source == "sample":
        return load_sample_data()
    if _file_bytes and _file_name:
        from io import BytesIO
        buf = BytesIO(_file_bytes)
        if _file_name.endswith(".pdf"):
            return parse_pdf_text(buf)
        return parse_excel(buf)
    return pd.DataFrame()


def index_data(df: pd.DataFrame) -> bool:
    """Embed and upsert all items. Returns True on success."""
    try:
        client = get_client()
        if collection_exists_and_populated(client):
            return True
        texts = [item_to_text(r) for _, r in df.iterrows()]
        with st.spinner("Generating embeddings via OpenAI…"):
            vectors = embed_texts(texts)
        with st.spinner("Indexing into Qdrant…"):
            n = upsert_items(client, df, vectors)
        return n > 0
    except Exception as e:
        st.error(f"Indexing failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
if data_source == "Use Sample Data (Project Bimbi)":
    df = load_df("sample")
else:
    if uploaded_file:
        df = load_df("upload", uploaded_file.read(), uploaded_file.name)
    else:
        df = pd.DataFrame()

if df.empty:
    st.info("Load sample data or upload a QCS file using the sidebar to get started.")
    st.stop()

st.session_state["df"] = df

# Index into Qdrant if API key is present
if os.getenv("OPENAI_API_KEY"):
    if "indexed" not in st.session_state:
        st.session_state["indexed"] = index_data(df)
else:
    st.session_state["indexed"] = False

# ── Home Dashboard ────────────────────────────────────────────────────────────
from core.analytics import total_bid_summary, vendor_scorecard

st.title("⚡ BidLite — Procurement Bid Intelligence")
st.caption(f"Project Bimbi · {df['item_no'].nunique()} line items · "
           f"{df['bidder'].nunique()} bidders · "
           f"{df['total_price'].sum():,.0f} USD total market")

totals = total_bid_summary(df)
scorecard = vendor_scorecard(df)

# KPI row
cols = st.columns(4)
low = totals.iloc[0]
high = totals.iloc[-1]
spread = totals["total_bid"].max() - totals["total_bid"].min()

cols[0].metric("Lowest Bid", f"${low['total_bid']:,.0f}", f"Bidder {low['bidder']}")
cols[1].metric("Highest Bid", f"${high['total_bid']:,.0f}", f"+{high['premium_vs_low']:.1f}% vs low")
cols[2].metric("Bid Spread", f"${spread:,.0f}", "max − min")
cols[3].metric("Best Scored Vendor", f"Bidder {scorecard.iloc[0]['bidder']}",
               f"Score {scorecard.iloc[0]['overall_score']:.0f}/100")

st.divider()

import plotly.express as px
import plotly.graph_objects as go

col1, col2 = st.columns(2)

with col1:
    st.subheader("Total Bid Ranking")
    fig = px.bar(
        totals.sort_values("total_bid"),
        x="bidder", y="total_bid",
        color="total_bid",
        color_continuous_scale="Blues",
        text=totals.sort_values("total_bid")["total_bid"].apply(lambda x: f"${x/1e6:.2f}M"),
        labels={"bidder": "Bidder", "total_bid": "Total Bid (USD)"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, coloraxis_showscale=False,
                      yaxis_title="Total Bid (USD)", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Vendor Overall Score")
    fig2 = px.bar(
        scorecard,
        x="bidder", y="overall_score",
        color="overall_score",
        color_continuous_scale="Greens",
        text=scorecard["overall_score"].apply(lambda x: f"{x:.0f}"),
        labels={"bidder": "Bidder", "overall_score": "Score (0–100)"},
    )
    fig2.update_traces(textposition="outside")
    fig2.update_layout(showlegend=False, coloraxis_showscale=False,
                       yaxis_range=[0, 110], margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Bid Summary Table")
st.dataframe(
    scorecard[["bidder", "total_bid", "rank", "premium_vs_low",
               "coverage_score", "consistency_score", "overall_score"]]
    .rename(columns={
        "bidder": "Bidder", "total_bid": "Total Bid (USD)", "rank": "Price Rank",
        "premium_vs_low": "Premium vs Low (%)", "coverage_score": "Coverage (%)",
        "consistency_score": "Consistency (%)", "overall_score": "Overall Score"
    })
    .style.format({
        "Total Bid (USD)": "${:,.0f}",
        "Premium vs Low (%)": "{:.1f}%",
        "Coverage (%)": "{:.1f}",
        "Consistency (%)": "{:.1f}",
        "Overall Score": "{:.1f}",
    })
    .background_gradient(subset=["Overall Score"], cmap="Greens"),
    use_container_width=True,
    hide_index=True,
)

if not st.session_state.get("indexed"):
    st.info(
        "Set OPENAI_API_KEY in your .env file to enable semantic search "
        "and vector-powered anomaly detection on the detail pages."
    )
