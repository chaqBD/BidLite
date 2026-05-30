"""
Page 4 — Semantic Item Search (Qdrant)
Author: Shakir

The core Qdrant demo: find bid items by meaning, not keywords.
Searching "medium voltage armoured aluminium cable" returns physically
similar items even if exact spec strings differ across bid documents.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from core.theme import inject_theme

st.set_page_config(page_title="Semantic Search · BidLite", page_icon="⚡", layout="wide")
inject_theme()
st.markdown(
    '<div class="bl-hero"><h1>🧠 Semantic Bid Item Search</h1>'
    '<p class="subtitle">Powered by Qdrant vector search — find relevant line items by meaning, '
    'not keywords. Cross-reference items across differently formatted bids.</p></div>',
    unsafe_allow_html=True,
)

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

if not st.session_state.get("indexed"):
    st.warning(
        "Semantic search requires an OpenAI API key to generate embeddings. "
        "Add OPENAI_API_KEY to your .env file and reload."
    )
    st.divider()
    st.subheader("Keyword Fallback Search")
    query = st.text_input("Search by keyword")
    if query:
        mask = df["description"].str.contains(query, case=False, na=False)
        results = df[mask][["item_no", "description", "spec_code", "bidder", "unit_price"]].drop_duplicates()
        st.dataframe(results.style.format({"unit_price": "${:.4f}"}),
                     use_container_width=True, hide_index=True)
    st.stop()

from core.vector_store import get_client, search_similar
from core.embedder import embed_single
from core.analytics import BIDDERS

client = get_client()

# ── Search UI ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(
        "Describe what you're looking for",
        placeholder="e.g. aluminium 500 kcmil single conductor low voltage cable",
    )
with col2:
    top_k = st.slider("Results", 3, 20, 8)
    bidder_filter = st.multiselect("Filter by Bidder", BIDDERS, default=[])

example_queries = [
    "large copper single conductor power cable",
    "aluminium armoured multiconductor cable",
    "small gauge ground wire",
    "medium voltage cable",
]
st.caption("Try: " + " · ".join(f"`{q}`" for q in example_queries))

if not query:
    st.stop()

with st.spinner("Searching vector index…"):
    vec = embed_single(query)
    results = search_similar(
        client, vec,
        top_k=top_k,
        bidder_filter=bidder_filter if bidder_filter else None,
    )

if not results:
    st.info("No results found.")
    st.stop()

results_df = pd.DataFrame(results)

# ── Results ───────────────────────────────────────────────────────────────────
st.subheader(f"{len(results_df)} Results")

# Score bar chart
fig = px.bar(
    results_df,
    x="score",
    y=(results_df["item_no"].astype(str) + ": " + results_df["description"].str[:45]),
    orientation="h",
    color="score",
    color_continuous_scale="Blues",
    labels={"x": "Similarity Score", "y": ""},
    text=results_df["score"].apply(lambda s: f"{s:.3f}"),
)
fig.update_traces(textposition="outside")
fig.update_layout(
    coloraxis_showscale=False,
    height=max(300, len(results_df) * 38),
    margin=dict(l=20, r=60),
    yaxis=dict(autorange="reversed"),
    xaxis_range=[0, 1.1],
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig, use_container_width=True)

# Detail table
cols_to_show = [c for c in ["score", "description", "spec_code", "bidder",
                              "unit_price", "qty", "unit"] if c in results_df.columns]
st.dataframe(
    results_df[cols_to_show]
    .style.format({
        "score": "{:.4f}",
        "unit_price": "${:.4f}",
        "qty": "{:,.0f}",
    })
    .background_gradient(subset=["score"], cmap="Blues"),
    use_container_width=True,
    hide_index=True,
)

# ── Price distribution of results ─────────────────────────────────────────────
if "unit_price" in results_df.columns and results_df["unit_price"].notna().any():
    st.subheader("Price Distribution of Results")
    fig2 = px.box(
        results_df.dropna(subset=["unit_price"]),
        x="bidder", y="unit_price",
        color="bidder",
        points="all",
        labels={"bidder": "Bidder", "unit_price": "Unit Price ($/LF)"},
    )
    fig2.update_layout(
        height=320, showlegend=False, margin=dict(t=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig2, use_container_width=True)
