"""
Page 3 — Scope Gap Heatmap
Author: Shakir

Visualises which bidders priced which items — missing or N/A items
represent scope gaps that must be resolved before awarding.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Scope Gaps · BidLite", layout="wide")
st.title("🗺️ Scope Gap Analysis")
st.caption(
    "A 'Missing' cell means the bidder did not price that item. "
    "'N/A' means the bidder explicitly excluded it. Both require resolution before award."
)

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

from core.analytics import scope_gap_matrix, BIDDERS

gap = scope_gap_matrix(df)
bidder_cols = [b for b in BIDDERS if b in gap.columns]

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_cells = len(gap) * len(bidder_cols)
missing_cells = (gap[bidder_cols] == "Missing").sum().sum()
na_cells = (gap[bidder_cols] == "N/A").sum().sum()
priced_cells = (gap[bidder_cols] == "Priced").sum().sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Item-Bidder Pairs", total_cells)
k2.metric("Fully Priced", int(priced_cells), f"{priced_cells/total_cells*100:.0f}%")
k3.metric("Missing (unpriced)", int(missing_cells))
k4.metric("Excluded (N/A)", int(na_cells))

st.divider()

# ── Heatmap ───────────────────────────────────────────────────────────────────
st.subheader("Coverage Heatmap")

status_map = {"Priced": 2, "N/A": 1, "Missing": 0}
z_matrix = gap[bidder_cols].applymap(lambda v: status_map.get(v, 0)).values
labels = (gap["item_no"].astype(str) + ": " + gap["description"].str[:40]).tolist()

colorscale = [
    [0.0, "#ffc7ce"],   # Missing — red
    [0.5, "#ffeb9c"],   # N/A — yellow
    [0.5, "#ffeb9c"],
    [1.0, "#c6efce"],   # Priced — green
]

fig = go.Figure(go.Heatmap(
    z=z_matrix,
    x=bidder_cols,
    y=labels,
    colorscale=colorscale,
    zmin=0, zmax=2,
    showscale=False,
    hoverongaps=False,
    text=gap[bidder_cols].values,
    hovertemplate="Item: %{y}<br>Bidder: %{x}<br>Status: %{text}<extra></extra>",
))
fig.update_layout(
    height=max(350, len(gap) * 24),
    margin=dict(l=340, t=30, b=30),
    yaxis=dict(autorange="reversed"),
    xaxis_side="top",
)
st.plotly_chart(fig, use_container_width=True)

# ── Per-bidder coverage bar ───────────────────────────────────────────────────
st.subheader("Coverage by Bidder")
coverage_rows = []
for b in bidder_cols:
    priced = (gap[b] == "Priced").sum()
    missing = (gap[b] == "Missing").sum()
    na = (gap[b] == "N/A").sum()
    coverage_rows.append({"Bidder": b, "Priced": priced, "Missing": missing, "N/A": na})
cov_df = pd.DataFrame(coverage_rows)

fig2 = px.bar(
    cov_df.melt(id_vars="Bidder", var_name="Status", value_name="Count"),
    x="Bidder", y="Count", color="Status", barmode="stack",
    color_discrete_map={"Priced": "#70ad47", "Missing": "#ff0000", "N/A": "#ffc000"},
)
fig2.update_layout(height=320, margin=dict(t=20))
st.plotly_chart(fig2, use_container_width=True)

# ── Missing items list ────────────────────────────────────────────────────────
st.subheader("Items with Missing Prices (any bidder)")
missing_items = gap[gap[bidder_cols].isin(["Missing", "N/A"]).any(axis=1)]
if missing_items.empty:
    st.success("All items are priced by all bidders.")
else:
    st.dataframe(missing_items[["item_no", "description"] + bidder_cols],
                 use_container_width=True, hide_index=True)
