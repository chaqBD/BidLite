"""
Page 7 — Predictive Price Analytics
Author: Shakir  |  Qdrant Hackathon 2026

Novel dual-model architecture:
  • Ridge Regression (feature-based, LOO cross-validated)
  • Qdrant KNN Regression (vector-similarity-weighted — Qdrant as an ML engine)
  • GPT interprets the ensemble output as a procurement analyst

Why this is novel: Qdrant is used not just for search but as a prediction
engine — similarity scores become regression weights. When both models agree,
confidence is high; when they diverge the item needs market clarification.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
from core.theme import inject_theme

st.set_page_config(
    page_title="Predictive Analytics · BidLite",
    page_icon="⚡",
    layout="wide",
)
inject_theme()

st.markdown(
    """
    <div class="bl-hero">
        <h1>🔮 Predictive Price Analytics</h1>
        <p class="subtitle">
            Dual-model ensemble: Ridge regression (feature-based) +
            <strong style="color:#00d4aa;">Qdrant KNN regression</strong>
            (vector-similarity-weighted) — GPT interprets the results as a
            senior procurement analyst.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Gate checks ───────────────────────────────────────────────────────────────
df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

indexed = st.session_state.get("indexed", False)
has_openai = bool(os.getenv("OPENAI_API_KEY"))
project_name = st.session_state.get("project_label", "Current Project")

# ── Technique explanation ─────────────────────────────────────────────────────
with st.expander("ℹ️ How the prediction models work", expanded=False):
    st.markdown(
        """
        **Model 1 — Ridge Regression (always available)**
        Extracts numeric features from each line item (conductor cross-section,
        number of cores, material, armoured/unarmoured, log quantity) and fits a
        regularised linear model. Every prediction is produced by Leave-One-Out
        cross-validation so it is genuinely out-of-sample.

        **Model 2 — Qdrant KNN Regression (requires vector index)**
        Each item is embedded with OpenAI `text-embedding-3-small` and its
        K=15 nearest semantic neighbours are retrieved from Qdrant. The
        predicted price is a **similarity-score-weighted average** of neighbour
        prices. This means:
        - Qdrant similarity scores become ML regression weights
        - Items with many close neighbours get tight predictions
        - Unusual items with no close matches get flagged as uncertain

        **Ensemble** = average of Model 1 and Model 2 (or Model 1 alone if
        Qdrant is not yet indexed).

        **Confidence flag** — Uncertain when the two models diverge >20% of the
        mean price, or when ensemble error exceeds 30%. These items need direct
        market clarification before award.
        """,
    )

st.divider()

# ── Run predictions (cached) ──────────────────────────────────────────────────
from core.predictor import build_item_df, ridge_predict, qdrant_knn_predict, ensemble_predict, bidder_vs_market

@st.cache_data(show_spinner=False, ttl=300)
def run_ridge(df_hash):
    item_df = build_item_df(df)
    return ridge_predict(item_df)

@st.cache_data(show_spinner=False, ttl=300)
def run_knn(df_hash):
    from core.vector_store import get_client
    from core.embedder import embed_single
    from core.predictor import build_item_df, qdrant_knn_predict
    import os
    item_df = build_item_df(df)
    client = get_client()
    collection = os.getenv("QDRANT_COLLECTION", "bidlite")
    return qdrant_knn_predict(item_df, client, embed_single, collection, k=15)

df_hash = str(len(df)) + str(df["total_price"].sum())

with st.spinner("Running Ridge regression (LOO cross-validation)…"):
    ridge_df = run_ridge(df_hash)

predictions = ridge_df.copy()
has_knn = False

if indexed:
    with st.spinner("Running Qdrant KNN regression (vector-weighted)…"):
        try:
            knn_df = run_knn(df_hash)
            predictions["knn_pred"] = knn_df["knn_pred"].values
            has_knn = predictions["knn_pred"].notna().sum() > 0
        except Exception as e:
            st.warning(f"Qdrant KNN skipped: {e}")

predictions = ensemble_predict(predictions)
bidder_analysis = bidder_vs_market(df, predictions)

# ── KPI row ───────────────────────────────────────────────────────────────────
ridge_r2   = predictions.attrs.get("ridge_r2", 0)
ridge_mape = predictions.attrs.get("ridge_mape", 0)
n_uncertain = (predictions["confidence_flag"] == "Uncertain").sum()

# Negotiation saving: items where best bidder is still above ensemble_pred
merged_all = df.merge(predictions[["item_no", "ensemble_pred"]], on="item_no", how="left")
merged_all["vs_market"] = merged_all["unit_price"] - merged_all["ensemble_pred"]
saving_total = merged_all[merged_all["vs_market"] > 0]["vs_market"].mul(
    merged_all.loc[merged_all["vs_market"] > 0, "qty"]
).sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ridge R² Score",      f"{ridge_r2:.2f}",  "1.0 = perfect fit (LOO-CV)")
k2.metric("MAPE",                 f"{ridge_mape:.1f}%", "mean abs % prediction error")
k3.metric("Uncertain Items",      n_uncertain,         "models diverge — needs clarification")
k4.metric("Max Negotiation Pool", f"${saving_total:,.0f}", "if above-market → predicted price")

st.markdown(
    f"**Models active:** Ridge Regression "
    f"{'+ **Qdrant KNN Regression** ✅ (Ensemble)' if has_knn else '(Qdrant KNN — index not built yet)'}",
)
st.divider()

# ── Chart 1: Predicted vs Actual (scatter) ────────────────────────────────────
st.subheader("Predicted vs Actual Market Price")
st.caption("Each point = one line item. Diagonal = perfect prediction. Bands = ±1.5 MAE confidence interval.")

scatter_df = predictions.copy()
scatter_df["label"] = scatter_df["item_no"].astype(str) + ": " + scatter_df["description"].str[:40]

fig = go.Figure()

# Confidence bands (ridge)
fig.add_trace(go.Scatter(
    x=scatter_df["mean_price"],
    y=scatter_df["ridge_high"],
    mode="lines", line=dict(width=0),
    showlegend=False, hoverinfo="skip",
))
fig.add_trace(go.Scatter(
    x=scatter_df["mean_price"],
    y=scatter_df["ridge_low"],
    mode="lines", line=dict(width=0),
    fill="tonexty",
    fillcolor="rgba(0,212,170,0.08)",
    name="Confidence band (±1.5 MAE)",
    hoverinfo="skip",
))

# Perfect prediction line
lim_max = max(scatter_df["mean_price"].max(), scatter_df["ensemble_pred"].max()) * 1.05
fig.add_trace(go.Scatter(
    x=[0, lim_max], y=[0, lim_max],
    mode="lines", line=dict(color="#3a4858", dash="dash", width=1),
    name="Perfect prediction", hoverinfo="skip",
))

# Ridge predictions
fig.add_trace(go.Scatter(
    x=scatter_df["mean_price"], y=scatter_df["ridge_pred"],
    mode="markers",
    marker=dict(color="#1e88e5", size=9, opacity=0.8),
    name="Ridge regression",
    text=scatter_df["label"],
    hovertemplate="<b>%{text}</b><br>Actual: $%{x:.4f}<br>Ridge: $%{y:.4f}<extra></extra>",
))

# KNN predictions (if available)
if has_knn and "knn_pred" in scatter_df.columns:
    fig.add_trace(go.Scatter(
        x=scatter_df["mean_price"],
        y=scatter_df["knn_pred"].fillna(scatter_df["ridge_pred"]),
        mode="markers",
        marker=dict(color="#00d4aa", size=9, symbol="diamond", opacity=0.85),
        name="Qdrant KNN regression",
        text=scatter_df["label"],
        hovertemplate="<b>%{text}</b><br>Actual: $%{x:.4f}<br>KNN: $%{y:.4f}<extra></extra>",
    ))

# Uncertain items highlighted
uncertain = scatter_df[scatter_df["confidence_flag"] == "Uncertain"]
if not uncertain.empty:
    fig.add_trace(go.Scatter(
        x=uncertain["mean_price"], y=uncertain["ensemble_pred"],
        mode="markers",
        marker=dict(color="#ff6b35", size=14, symbol="circle-open", line=dict(width=2, color="#ff6b35")),
        name="Uncertain (models diverge)",
        text=uncertain["label"],
        hovertemplate="<b>%{text}</b><br>Actual: $%{x:.4f}<br>Ensemble: $%{y:.4f}<extra></extra>",
    ))

fig.update_layout(
    height=480,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    xaxis=dict(title="Actual Mean Market Price ($/unit)", gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(title="Predicted Price ($/unit)", gridcolor="rgba(255,255,255,0.05)"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
    margin=dict(t=20),
)
st.plotly_chart(fig, use_container_width=True)

# ── Chart 2: Bidder deviation heatmap ─────────────────────────────────────────
st.divider()
st.subheader("Bidder vs Predicted Market Price")
st.caption("How far each bidder's prices sit above (+) or below (−) the model's predicted fair market value.")

merged_heat = df.merge(predictions[["item_no", "ensemble_pred"]], on="item_no", how="left")
merged_heat["vs_mkt"] = ((merged_heat["unit_price"] - merged_heat["ensemble_pred"]) / merged_heat["ensemble_pred"] * 100).round(1)

pivot_heat = merged_heat.pivot_table(
    index="item_no", columns="bidder", values="vs_mkt", aggfunc="mean"
).round(1)

item_labels = [
    f"{i}: {r['description'][:35]}"
    for i, r in predictions.set_index("item_no")[["description"]].iterrows()
    if i in pivot_heat.index
]

bid_cols = sorted(pivot_heat.columns.tolist())
z = pivot_heat[bid_cols].values

heat = go.Figure(go.Heatmap(
    z=z,
    x=bid_cols,
    y=item_labels,
    colorscale=[
        [0.0,  "#1a5276"],   # deeply below market  (dark blue)
        [0.35, "#2980b9"],   # below market          (blue)
        [0.5,  "#2c3e50"],   # at market             (neutral dark)
        [0.65, "#c0392b"],   # above market          (red)
        [1.0,  "#7b241c"],   # deeply above market   (dark red)
    ],
    zmid=0,
    colorbar=dict(title="% vs Market"),
    text=pivot_heat[bid_cols].values,
    texttemplate="%{text:.1f}%",
    hovertemplate="Bidder %{x}<br>Item %{y}<br>Deviation: %{z:.1f}%<extra></extra>",
))
heat.update_layout(
    height=max(380, len(pivot_heat) * 26),
    margin=dict(l=320, t=30, b=20, r=120),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    xaxis_side="top",
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(heat, use_container_width=True)

# ── Chart 3: Bidder market risk ───────────────────────────────────────────────
st.divider()
st.subheader("Bidder Market-Price Risk Score")
st.caption("Combines average premium vs prediction + % of items priced >10% above market. Higher = riskier.")

risk_fig = px.bar(
    bidder_analysis.sort_values("market_risk_score", ascending=True),
    x="market_risk_score", y="bidder",
    orientation="h",
    color="market_risk_score",
    color_continuous_scale=[[0, "#00d4aa"], [0.5, "#f4a261"], [1, "#d62728"]],
    text=bidder_analysis.sort_values("market_risk_score", ascending=True)["market_risk_score"].apply(
        lambda v: f"{v:.0f}/100"
    ),
    labels={"market_risk_score": "Risk Score", "bidder": "Bidder"},
    hover_data=["avg_premium", "pct_above_10", "pct_below_10"],
)
risk_fig.update_traces(textposition="outside")
risk_fig.update_layout(
    height=320, coloraxis_showscale=False,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    xaxis=dict(range=[0, 115], gridcolor="rgba(255,255,255,0.05)"),
    margin=dict(t=10),
)
st.plotly_chart(risk_fig, use_container_width=True)

# ── Detailed prediction table ─────────────────────────────────────────────────
st.divider()
with st.expander("📋 Full Prediction Table", expanded=False):
    show_cols = ["item_no", "description", "qty", "mean_price",
                 "ridge_pred", "ensemble_pred", "model_divergence_pct", "confidence_flag"]
    if has_knn:
        show_cols.insert(5, "knn_pred")

    disp = predictions[show_cols].rename(columns={
        "item_no": "#", "description": "Description", "qty": "Qty",
        "mean_price": "Actual Mean", "ridge_pred": "Ridge Pred",
        "knn_pred": "KNN Pred", "ensemble_pred": "Ensemble Pred",
        "model_divergence_pct": "Model Divergence %",
        "confidence_flag": "Confidence",
    })
    fmt = {
        "Actual Mean": "${:.4f}", "Ridge Pred": "${:.4f}",
        "Ensemble Pred": "${:.4f}", "Qty": "{:,.0f}",
        "Model Divergence %": "{:.1f}%",
    }
    if has_knn:
        fmt["KNN Pred"] = "${:.4f}"

    st.dataframe(
        disp.style.format(fmt).apply(
            lambda col: ["background: rgba(255,100,50,0.12)" if v == "Uncertain" else ""
                         for v in col],
            subset=["Confidence"],
        ),
        use_container_width=True, hide_index=True,
    )

# ── GPT Prediction Commentary ─────────────────────────────────────────────────
st.divider()
st.subheader("🤖 AI Prediction Commentary")
st.caption(
    "GPT-4o-mini interprets the ML results as a senior procurement analyst — "
    "not just numbers, but strategy."
)

if not has_openai:
    st.info("Add OPENAI_API_KEY to .env to enable AI commentary.")
else:
    if "pred_commentary" not in st.session_state:
        st.session_state["pred_commentary"] = ""

    custom_notes = st.text_area(
        "Additional context for the AI (optional)",
        placeholder="e.g. Market steel prices rose 15% this quarter; "
                    "Bidder B is incumbent…",
        height=70,
    )

    if st.button("⚡ Generate AI Market Commentary", use_container_width=True, type="primary"):
        from core.ai_insight import generate_prediction_insight

        uncertain_items = predictions[predictions["confidence_flag"] == "Uncertain"][
            ["description", "mean_price", "ensemble_pred", "model_divergence_pct"]
        ].to_dict(orient="records")

        bidder_rows = bidder_analysis[
            ["bidder", "avg_premium", "pct_above_10", "market_risk_score"]
        ].to_dict(orient="records")

        # top overpriced items (bidder level)
        top_op = (
            merged_all[merged_all["vs_market"] > 0]
            .nlargest(5, "vs_market")
            [["description", "bidder", "unit_price", "ensemble_pred", "vs_market"]]
            .rename(columns={"vs_market": "vs_market_pct"})
        )
        # convert vs_market from $ to %
        top_op["vs_market_pct"] = (top_op["vs_market_pct"] / top_op["ensemble_pred"] * 100).round(1)
        top_op_rows = top_op.to_dict(orient="records")

        with st.spinner("GPT-4o-mini is analysing predictions…"):
            commentary = generate_prediction_insight(
                project_name=project_name,
                ridge_r2=ridge_r2,
                ridge_mape=ridge_mape,
                n_items=len(predictions),
                has_knn=has_knn,
                uncertain_items=uncertain_items,
                bidder_summary=bidder_rows,
                top_overprice=top_op_rows,
                top_savings=saving_total,
                custom_notes=custom_notes,
            )
        st.session_state["pred_commentary"] = commentary

    if st.session_state["pred_commentary"]:
        st.markdown(
            f"""
            <div style="
                background: rgba(0,212,170,0.04);
                border: 1px solid rgba(0,212,170,0.18);
                border-radius: 12px;
                padding: 2rem 2.4rem;
                font-family: 'Georgia', serif;
                font-size: 0.93rem;
                line-height: 1.8;
                color: #d8e0ec;
                white-space: pre-wrap;
            ">{st.session_state["pred_commentary"]}</div>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            "📥 Download Commentary (.txt)",
            data=st.session_state["pred_commentary"],
            file_name="prediction_commentary.txt",
            mime="text/plain",
            use_container_width=True,
        )
