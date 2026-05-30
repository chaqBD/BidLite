"""
BidLite — Vector-Powered Procurement Intelligence
Author: Shakir  |  Qdrant Hackathon 2026
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
from core.theme import inject_theme

load_dotenv()

st.set_page_config(
    page_title="BidLite · Procurement Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
            <span style="font-size:2.2rem;">⚡</span><br>
            <span style="font-size:1.3rem; font-weight:700; color:#00d4aa; letter-spacing:0.05em;">BidLite</span><br>
            <span style="font-size:0.72rem; color:#5a6878; letter-spacing:0.12em;">PROCUREMENT INTELLIGENCE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
        project_label = st.text_input(
            "Project name",
            value=st.session_state.get("project_label", ""),
            placeholder="e.g. Project Alpha — Cable Supply",
        )
    else:
        project_label = "Project Bimbi"

    st.session_state["project_label"] = project_label

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
    st.markdown(
        "<div style='text-align:center; color:#3a4858; font-size:0.72rem;'>"
        "Built for Qdrant Hackathon 2026<br>"
        "<span style='color:#00d4aa;'>⬡</span> Powered by Qdrant + OpenAI"
        "</div>",
        unsafe_allow_html=True,
    )


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


# ── Resolve data ──────────────────────────────────────────────────────────────
if data_source == "Use Sample Data (Project Bimbi)":
    df = load_df("sample")
else:
    if uploaded_file:
        df = load_df("upload", uploaded_file.read(), uploaded_file.name)
    else:
        df = pd.DataFrame()

if df.empty:
    st.markdown(
        """
        <div class="bl-hero" style="text-align:center; padding:3rem;">
            <span style="font-size:3rem;">⚡</span>
            <h1 style="margin:0.5rem 0;">BidLite</h1>
            <p class="subtitle">Load sample data or upload a QCS file using the sidebar to get started.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

st.session_state["df"] = df

if os.getenv("OPENAI_API_KEY"):
    if "indexed" not in st.session_state:
        st.session_state["indexed"] = index_data(df)
else:
    st.session_state["indexed"] = False

# ── Analytics ─────────────────────────────────────────────────────────────────
from core.analytics import total_bid_summary, vendor_scorecard, detect_price_anomalies

totals   = total_bid_summary(df)
scorecard = vendor_scorecard(df)
anomalies = detect_price_anomalies(df)
low  = totals.iloc[0]
high = totals.iloc[-1]
spread = totals["total_bid"].max() - totals["total_bid"].min()

# ── Hero banner ───────────────────────────────────────────────────────────────
display_project = project_label or "Untitled Project"
st.markdown(
    f"""
    <div class="bl-hero">
        <h1>⚡ BidLite — Procurement Bid Intelligence</h1>
        <p class="subtitle">
            {display_project} &nbsp;·&nbsp; {df['item_no'].nunique()} line items
            &nbsp;·&nbsp; {df['bidder'].nunique()} bidders
            &nbsp;·&nbsp; ${df['total_price'].sum():,.0f} USD total market
            &nbsp;·&nbsp; {len(anomalies)} price anomalies detected
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────────
cols = st.columns(4)
cols[0].metric("Lowest Bid",        f"${low['total_bid']:,.0f}",   f"Bidder {low['bidder']}")
cols[1].metric("Highest Bid",       f"${high['total_bid']:,.0f}",  f"+{high['premium_vs_low']:.1f}% vs low")
cols[2].metric("Bid Spread",        f"${spread:,.0f}",             "max − min")
cols[3].metric("Best Scored Vendor", f"Bidder {scorecard.iloc[0]['bidder']}",
               f"Score {scorecard.iloc[0]['overall_score']:.0f}/100")

st.divider()

# ── Risk Flags ────────────────────────────────────────────────────────────────
COMMERCIAL = {
    "A": {"bid_type": "Budgetary", "validity_days": 30, "warranty": True},
    "B": {"bid_type": "Firm",      "validity_days": 4,  "warranty": True},
    "C": {"bid_type": "Firm",      "validity_days": 30, "warranty": True},
    "D": {"bid_type": "Firm",      "validity_days": 1,  "warranty": False},
    "E": {"bid_type": "Budgetary", "validity_days": 1,  "warranty": False},
    "F": {"bid_type": "Firm",      "validity_days": 30, "warranty": True},
}

risks  = []
warns  = []

for bidder, info in COMMERCIAL.items():
    if info["bid_type"] == "Budgetary":
        risks.append(f"**Bidder {bidder}** — Budgetary bid: prices are indicative only, not binding")
    if info["validity_days"] < 5:
        risks.append(f"**Bidder {bidder}** — Bid validity only {info['validity_days']} day(s): expired before award decision")
    if not info["warranty"]:
        warns.append(f"**Bidder {bidder}** — Warranty not confirmed")

if risks or warns:
    with st.expander("⚠️ Risk Flags — Action Required Before Award", expanded=True):
        rc, wc = st.columns(2)
        with rc:
            st.markdown("##### 🔴 Critical")
            for r in risks:
                st.markdown(
                    f'<div class="bl-risk-card">{r}</div>',
                    unsafe_allow_html=True,
                )
        with wc:
            st.markdown("##### 🟡 Warnings")
            for w in warns:
                st.markdown(
                    f'<div class="bl-warn-card">{w}</div>',
                    unsafe_allow_html=True,
                )

st.divider()

# ── Charts row ────────────────────────────────────────────────────────────────
import plotly.express as px

col1, col2 = st.columns(2)

with col1:
    st.subheader("Total Bid Ranking")
    fig = px.bar(
        totals.sort_values("total_bid"),
        x="bidder", y="total_bid",
        color="total_bid",
        color_continuous_scale=[[0, "#0d2137"], [0.5, "#006e8a"], [1, "#00d4aa"]],
        text=totals.sort_values("total_bid")["total_bid"].apply(lambda x: f"${x/1e6:.2f}M"),
        labels={"bidder": "Bidder", "total_bid": "Total Bid (USD)"},
    )
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(
        showlegend=False, coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Total Bid (USD)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Vendor Overall Score")
    fig2 = px.bar(
        scorecard,
        x="bidder", y="overall_score",
        color="overall_score",
        color_continuous_scale=[[0, "#0d2137"], [0.5, "#007a5e"], [1, "#00d4aa"]],
        text=scorecard["overall_score"].apply(lambda x: f"{x:.0f}"),
        labels={"bidder": "Bidder", "overall_score": "Score (0–100)"},
    )
    fig2.update_traces(textposition="outside", marker_line_width=0)
    fig2.update_layout(
        showlegend=False, coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", range=[0, 110]),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        margin=dict(t=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Bid Summary Table ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Bid Summary Table")
st.dataframe(
    scorecard[["bidder", "total_bid", "rank", "premium_vs_low",
               "coverage_score", "consistency_score", "overall_score"]]
    .rename(columns={
        "bidder": "Bidder", "total_bid": "Total Bid (USD)", "rank": "Price Rank",
        "premium_vs_low": "Premium vs Low (%)", "coverage_score": "Coverage (%)",
        "consistency_score": "Consistency (%)", "overall_score": "Overall Score",
    })
    .style.format({
        "Total Bid (USD)": "${:,.0f}",
        "Premium vs Low (%)": "{:.1f}%",
        "Coverage (%)": "{:.1f}",
        "Consistency (%)": "{:.1f}",
        "Overall Score": "{:.1f}",
    })
    .background_gradient(subset=["Overall Score"], cmap="YlGn"),
    use_container_width=True,
    hide_index=True,
)

if not st.session_state.get("indexed"):
    st.info(
        "Set OPENAI_API_KEY in your .env file to enable semantic search, "
        "vector-powered anomaly context, and AI award memo generation."
    )
