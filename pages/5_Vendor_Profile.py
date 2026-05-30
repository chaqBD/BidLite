"""
Page 5 — Vendor Fingerprinting & Radar
Author: Shakir

Each vendor is positioned in multi-dimensional scoring space.
The radar chart shows their relative strengths across five dimensions.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from core.theme import inject_theme

st.set_page_config(page_title="Vendor Profile · BidLite", page_icon="⚡", layout="wide")
inject_theme()
st.markdown(
    '<div class="bl-hero"><h1>🎯 Vendor Profiles &amp; Competitive Positioning</h1>'
    '<p class="subtitle">Multi-dimensional scoring across price, coverage, consistency, '
    'bid validity, and warranty risk — build your award recommendation.</p></div>',
    unsafe_allow_html=True,
)

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

from core.analytics import vendor_scorecard, total_bid_summary, BIDDERS

scorecard = vendor_scorecard(df)

# ── Commercial terms from sample data ─────────────────────────────────────────
commercial = pd.DataFrame({
    "bidder": ["A", "B", "C", "D", "E", "F"],
    "bid_type": ["Budgetary", "Firm", "Firm", "Firm", "Budgetary", "Firm"],
    "validity_days": [30, 4, 30, 1, 1, 30],
    "security": ["No (surety letter available)", "100% Supply Bond", "Other",
                  "100% Supply Bond", "10% LOC", "Not Provided"],
    "warranty_confirmed": [True, True, True, False, False, True],
    "payment_terms": ["Not Provided", "100% at delivery", "Not Provided",
                      "60-day terms", "100% Net 60", "All at shipment"],
    "shipping": ["DDP", "DDP", "DDP", "FOB", "DDP", "DDP"],
})

merged = scorecard.merge(commercial, on="bidder", how="left")

# ── Validity risk score ───────────────────────────────────────────────────────
max_val = merged["validity_days"].max()
merged["validity_score"] = (merged["validity_days"] / max_val * 100).round(1)

# ── Warranty score ────────────────────────────────────────────────────────────
merged["warranty_score"] = merged["warranty_confirmed"].map({True: 100, False: 0})

# ── Radar chart ───────────────────────────────────────────────────────────────
st.subheader("Vendor Radar — Multi-Dimensional Comparison")

dimensions = ["price_score", "coverage_score", "consistency_score",
              "validity_score", "warranty_score"]
dim_labels = ["Price", "Coverage", "Consistency", "Bid Validity", "Warranty"]

selected_bidders = st.multiselect(
    "Select bidders to compare", BIDDERS, default=BIDDERS
)

fig = go.Figure()
colors = px.colors.qualitative.Bold
for i, bidder in enumerate(selected_bidders):
    row = merged[merged["bidder"] == bidder]
    if row.empty:
        continue
    values = [float(row[d].values[0]) for d in dimensions]
    values_closed = values + [values[0]]
    labels_closed = dim_labels + [dim_labels[0]]
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        name=f"Bidder {bidder}",
        line_color=colors[i % len(colors)],
        opacity=0.7,
    ))

fig.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 110], gridcolor="rgba(255,255,255,0.08)", color="#7a8899"),
        angularaxis=dict(color="#c9d1d9"),
        bgcolor="rgba(0,0,0,0)",
    ),
    showlegend=True,
    height=520,
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
st.plotly_chart(fig, use_container_width=True)

# ── Bubble chart: price vs overall score ─────────────────────────────────────
st.subheader("Price vs Score Positioning")
bubble_df = merged.copy()
bubble_df["coverage_score"] = bubble_df["coverage_score"].fillna(0).clip(lower=1)
fig2 = px.scatter(
    bubble_df,
    x="total_bid",
    y="overall_score",
    size="coverage_score",
    color="bidder",
    text="bidder",
    color_discrete_sequence=px.colors.qualitative.Bold,
    labels={"total_bid": "Total Bid (USD)", "overall_score": "Overall Score",
            "coverage_score": "Coverage (bubble size)"},
    size_max=50,
)
fig2.update_traces(textposition="top center", textfont_size=13)
fig2.update_layout(
    height=420, showlegend=False, margin=dict(t=30),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)
fig2.update_xaxes(tickformat="$,.0f")
st.plotly_chart(fig2, use_container_width=True)

# ── Scorecard table ───────────────────────────────────────────────────────────
st.subheader("Full Vendor Scorecard")
display = merged[[
    "bidder", "total_bid", "rank", "premium_vs_low",
    "price_score", "coverage_score", "consistency_score",
    "validity_score", "warranty_score", "overall_score",
    "bid_type", "shipping", "warranty_confirmed",
]].rename(columns={
    "bidder": "Bidder", "total_bid": "Total Bid", "rank": "Rank",
    "premium_vs_low": "Premium %", "price_score": "Price",
    "coverage_score": "Coverage", "consistency_score": "Consistency",
    "validity_score": "Validity", "warranty_score": "Warranty",
    "overall_score": "Score", "bid_type": "Bid Type",
    "shipping": "Incoterms", "warranty_confirmed": "Warranty OK",
})
st.dataframe(
    display.style.format({
        "Total Bid": "${:,.0f}", "Premium %": "{:.1f}%",
        "Price": "{:.1f}", "Coverage": "{:.1f}",
        "Consistency": "{:.1f}", "Validity": "{:.1f}",
        "Warranty": "{:.0f}", "Score": "{:.1f}",
    }).background_gradient(subset=["Score"], cmap="Greens"),
    use_container_width=True,
    hide_index=True,
)

# ── Award recommendation ──────────────────────────────────────────────────────
st.divider()
st.subheader("🏆 Award Recommendation")
top = merged.sort_values("overall_score", ascending=False).iloc[0]
second = merged.sort_values("overall_score", ascending=False).iloc[1]

c1, c2 = st.columns(2)
with c1:
    st.success(
        f"**Recommended Award: Bidder {top['bidder']}**\n\n"
        f"- Total Bid: ${top['total_bid']:,.0f}\n"
        f"- Overall Score: {top['overall_score']:.1f}/100\n"
        f"- Bid Type: {top['bid_type']}\n"
        f"- Warranty Confirmed: {'Yes' if top['warranty_confirmed'] else 'No'}"
    )
with c2:
    st.info(
        f"**Alternate: Bidder {second['bidder']}**\n\n"
        f"- Total Bid: ${second['total_bid']:,.0f}\n"
        f"- Overall Score: {second['overall_score']:.1f}/100\n"
        f"- Bid Type: {second['bid_type']}\n"
        f"- Warranty Confirmed: {'Yes' if second['warranty_confirmed'] else 'No'}"
    )
