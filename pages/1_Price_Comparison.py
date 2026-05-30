"""
Page 1 — Item-by-Item Price Comparison
Author: Shakir
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Price Comparison · BidLite", layout="wide")
st.title("📊 Item-by-Item Price Comparison")

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

from core.analytics import price_comparison, BIDDERS

pivot = price_comparison(df)

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    search = st.text_input("Filter by description keyword", "")
with col2:
    spec_options = ["All"] + sorted(pivot["spec_code"].dropna().unique().tolist())
    spec_filter = st.selectbox("Filter by spec code", spec_options)
with col3:
    sort_by = st.selectbox("Sort by", ["item_no", "spread_pct", "avg_price"])

mask = pd.Series([True] * len(pivot))
if search:
    mask &= pivot["description"].str.contains(search, case=False, na=False)
if spec_filter != "All":
    mask &= pivot["spec_code"] == spec_filter

filtered = pivot[mask].sort_values(sort_by, ascending=True)

# ── Grouped bar chart: unit prices per item per bidder ────────────────────────
st.subheader("Unit Price Comparison ($/LF)")

bidder_present = [b for b in BIDDERS if b in filtered.columns]
plot_df = filtered.melt(
    id_vars=["item_no", "description", "qty"],
    value_vars=bidder_present,
    var_name="Bidder",
    value_name="Unit Price",
)
plot_df = plot_df.dropna(subset=["Unit Price"])
plot_df["label"] = plot_df["item_no"].astype(str) + ": " + plot_df["description"].str[:40]

fig = px.bar(
    plot_df,
    x="label",
    y="Unit Price",
    color="Bidder",
    barmode="group",
    color_discrete_sequence=px.colors.qualitative.Bold,
    labels={"label": "Line Item", "Unit Price": "Unit Price ($/LF)"},
)
fig.update_layout(
    xaxis_tickangle=-40,
    height=480,
    legend_title="Bidder",
    margin=dict(b=120),
)
st.plotly_chart(fig, use_container_width=True)

# ── Spread heatmap ────────────────────────────────────────────────────────────
st.subheader("Price Spread Heatmap (% spread = (max−min)/min)")

heat_data = filtered[["item_no", "description"] + bidder_present + ["spread_pct"]].copy()
heat_data["short_desc"] = heat_data["item_no"].astype(str) + ": " + heat_data["description"].str[:35]

fig2 = px.imshow(
    heat_data[bidder_present].values,
    x=bidder_present,
    y=heat_data["short_desc"].tolist(),
    color_continuous_scale="RdYlGn_r",
    aspect="auto",
    labels={"color": "Unit Price"},
)
fig2.update_layout(height=max(300, len(heat_data) * 22), margin=dict(l=280))
st.plotly_chart(fig2, use_container_width=True)

# ── Detail table ──────────────────────────────────────────────────────────────
st.subheader("Detailed Pricing Table")
display_cols = ["item_no", "description", "spec_code", "qty", "unit"] + bidder_present + ["avg_price", "min_price", "max_price", "spread_pct"]
st.dataframe(
    filtered[display_cols]
    .style.format({b: "${:.4f}" for b in bidder_present} | {
        "avg_price": "${:.4f}", "min_price": "${:.4f}", "max_price": "${:.4f}",
        "spread_pct": "{:.1f}%", "qty": "{:,.0f}",
    })
    .highlight_min(subset=bidder_present, color="#c6efce", axis=1)
    .highlight_max(subset=bidder_present, color="#ffc7ce", axis=1),
    use_container_width=True,
    hide_index=True,
)
