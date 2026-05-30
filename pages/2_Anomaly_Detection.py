"""
Page 2 — Vector-Powered Price Anomaly Detection
Author: Shakir

Uses Qdrant nearest-neighbour search to surface line items where a bidder's
price is statistically distant from the cluster of similar items.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.theme import inject_theme

st.set_page_config(page_title="Anomaly Detection · BidLite", page_icon="⚡", layout="wide")
inject_theme()
st.markdown(
    '<div class="bl-hero"><h1>🔍 Price Anomaly Detection</h1>'
    '<p class="subtitle">Z-score outlier flagging + Qdrant nearest-neighbour context — '
    'surface negotiation opportunities and scope differences</p></div>',
    unsafe_allow_html=True,
)

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

from core.analytics import detect_price_anomalies, price_comparison, BIDDERS

# ── Controls ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 3])
with col1:
    z_thresh = st.slider("Z-score threshold", 1.0, 3.0, 1.8, 0.1,
                         help="Higher = only flag extreme outliers")

anomalies = detect_price_anomalies(df, z_threshold=z_thresh)

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Anomalous Items", len(anomalies))
if not anomalies.empty:
    high_count = (anomalies["direction"] == "HIGH").sum()
    low_count  = (anomalies["direction"] == "LOW").sum()
    k2.metric("Overpriced Flags", int(high_count))
    k3.metric("Underpriced Flags", int(low_count))
    worst = anomalies.loc[anomalies["z_score"].idxmax()]
    k4.metric("Highest Z-score", f"{worst['z_score']:.1f}",
              f"Bidder {worst['bidder']} · Item {int(worst['item_no'])}")

st.divider()

if anomalies.empty:
    st.success("No anomalies detected at the current threshold.")
    st.stop()

# ── Scatter: z-score per item per bidder ─────────────────────────────────────
st.subheader("Anomaly Map — Z-score per Bidder per Item")
anomalies["label"] = anomalies["item_no"].astype(str) + ": " + anomalies["description"].str[:35]
fig = px.scatter(
    anomalies,
    x="label",
    y="z_score",
    color="direction",
    size="z_score",
    symbol="bidder",
    color_discrete_map={"HIGH": "#d62728", "LOW": "#1f77b4"},
    hover_data=["bidder", "unit_price", "item_mean", "z_score"],
    labels={"label": "Line Item", "z_score": "Z-score"},
)
fig.add_hline(y=z_thresh, line_dash="dot", line_color="gray",
              annotation_text=f"Threshold ({z_thresh})")
fig.update_layout(
    height=420, xaxis_tickangle=-40, margin=dict(b=120),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig, use_container_width=True)

# ── Waterfall: price vs market mean for anomalous items ──────────────────────
st.subheader("Price vs Market Mean (Anomalous Items)")
anomalies["delta"] = anomalies["unit_price"] - anomalies["item_mean"]
anomalies["delta_pct"] = (anomalies["delta"] / anomalies["item_mean"] * 100).round(1)

fig2 = px.bar(
    anomalies.sort_values("delta_pct"),
    x="label",
    y="delta_pct",
    color="direction",
    color_discrete_map={"HIGH": "#d62728", "LOW": "#1f77b4"},
    text="delta_pct",
    facet_col=None,
    labels={"delta_pct": "Deviation from Mean (%)", "label": ""},
    hover_data=["bidder", "unit_price", "item_mean"],
)
fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig2.update_layout(
    height=400, xaxis_tickangle=-40, margin=dict(b=120), showlegend=True,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
st.plotly_chart(fig2, use_container_width=True)

# ── Negotiation Savings Estimator ────────────────────────────────────────────
st.divider()
st.subheader("💰 Negotiation Savings Estimator")
st.caption(
    "If every overpriced (HIGH) item is negotiated down to the market mean, "
    "the estimated total saving is:"
)

high_anom = (
    anomalies[anomalies["direction"] == "HIGH"].copy()
    if not anomalies.empty and "direction" in anomalies.columns
    else pd.DataFrame()
)
if not high_anom.empty:
    high_anom["saving_per_unit"] = high_anom["unit_price"] - high_anom["item_mean"]
    high_anom["est_saving"] = high_anom["saving_per_unit"] * high_anom["qty"].fillna(0)
    total_saving = high_anom["est_saving"].sum()

    s1, s2, s3 = st.columns(3)
    s1.metric("Overpriced Flags",        len(high_anom))
    s2.metric("Max Single-Item Saving",  f"${high_anom['est_saving'].max():,.0f}")
    s3.metric("Total Estimated Saving",  f"${total_saving:,.0f}",
              "if all HIGH anomalies → market mean")

    sav_fig = px.bar(
        high_anom.sort_values("est_saving", ascending=False).head(10),
        x="label",
        y="est_saving",
        color="bidder",
        color_discrete_sequence=["#d62728","#ff7f0e","#f4a261","#e76f51","#d62728","#c0392b"],
        labels={"label": "", "est_saving": "Estimated Saving (USD)", "bidder": "Bidder"},
        text=high_anom.sort_values("est_saving", ascending=False).head(10)["est_saving"]
            .apply(lambda x: f"${x:,.0f}"),
    )
    sav_fig.update_traces(textposition="outside")
    sav_fig.update_layout(
        height=340, xaxis_tickangle=-35, margin=dict(b=100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(sav_fig, use_container_width=True)
else:
    st.success("No overpriced anomalies — no negotiation savings available at this threshold.")

st.divider()

# ── Anomaly table ─────────────────────────────────────────────────────────────
st.subheader("Anomaly Detail")
display = anomalies[[
    "item_no", "description", "bidder", "unit_price",
    "item_mean", "z_score", "direction", "delta_pct",
]].rename(columns={
    "item_no": "#", "description": "Description", "bidder": "Bidder",
    "unit_price": "Unit Price", "item_mean": "Market Mean",
    "z_score": "Z-score", "direction": "Flag", "delta_pct": "Δ Mean (%)",
})

st.dataframe(
    display.style.format({
        "Unit Price": "${:.4f}",
        "Market Mean": "${:.4f}",
        "Z-score": "{:.2f}",
        "Δ Mean (%)": "{:.1f}%",
    }).map(
        lambda v: "color: #d62728; font-weight:bold" if v == "HIGH"
                  else ("color: #1f77b4; font-weight:bold" if v == "LOW" else ""),
        subset=["Flag"]
    ),
    use_container_width=True,
    hide_index=True,
)

# ── Qdrant semantic context ───────────────────────────────────────────────────
st.divider()
st.subheader("🔎 Semantic Nearest Neighbours (Qdrant)")
st.caption("Select an anomalous item to retrieve the most similar items from the vector index.")

if st.session_state.get("indexed"):
    from core.vector_store import get_client, search_similar
    from core.embedder import embed_single, item_to_text

    item_labels = anomalies["label"].unique().tolist()
    chosen = st.selectbox("Select anomalous item", item_labels)
    row = anomalies[anomalies["label"] == chosen].iloc[0]

    if st.button("Find Similar Items in Vector Store"):
        text = item_to_text(row.to_dict())
        vec = embed_single(text)
        results = search_similar(get_client(), vec, top_k=8)
        st.dataframe(pd.DataFrame(results)[
            ["score", "description", "bidder", "unit_price", "spec_code"]
        ].style.format({"score": "{:.3f}", "unit_price": "${:.4f}"}),
            use_container_width=True, hide_index=True)
else:
    st.info("Set OPENAI_API_KEY in .env to enable Qdrant semantic search.")
