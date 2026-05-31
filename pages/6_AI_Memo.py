"""
Page 6 — AI Award Recommendation Memo
Author: Shakir

Novel feature: GPT-4o-mini synthesises all analytics (scores, anomalies,
scope gaps, risk flags) into a formal procurement recommendation memo
ready to attach to an award package.
"""

import streamlit as st
import pandas as pd
from core.theme import inject_theme
from core.env import get_env

st.set_page_config(page_title="AI Award Memo · BidLite", page_icon="⚡", layout="wide")
inject_theme()

st.markdown(
    '<div class="bl-hero"><h1>📝 AI Award Recommendation Memo</h1>'
    '<p class="subtitle">GPT-4o-mini synthesises bid scores, price anomalies, and scope gaps '
    'into a formal procurement memo — ready for sign-off.</p></div>',
    unsafe_allow_html=True,
)

df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

if not st.session_state.get("indexed"):
    st.info(
        "Set OPENAI_API_KEY in .env to enable AI memo generation. "
        "The memo uses GPT-4o-mini to write the document."
    )

from core.analytics import (
    vendor_scorecard, detect_price_anomalies, scope_gap_matrix, BIDDERS,
)

scorecard  = vendor_scorecard(df)
anomalies  = detect_price_anomalies(df)
gap        = scope_gap_matrix(df)
bidder_cols = [b for b in BIDDERS if b in gap.columns]

# ── Savings estimator ─────────────────────────────────────────────────────────
if not anomalies.empty and "direction" in anomalies.columns:
    high_anom = anomalies[anomalies["direction"] == "HIGH"].copy()
else:
    high_anom = pd.DataFrame(columns=["unit_price", "item_mean", "qty", "est_saving", "saving_per_unit"])

if not high_anom.empty:
    high_anom["saving_per_unit"] = high_anom["unit_price"] - high_anom["item_mean"]
    high_anom["est_saving"] = high_anom["saving_per_unit"] * high_anom["qty"].fillna(0)
savings_estimate = high_anom["est_saving"].sum() if "est_saving" in high_anom.columns else 0.0

# Scope gap summary
missing_cells = int((gap[bidder_cols] == "Missing").sum().sum())
na_cells      = int((gap[bidder_cols] == "N/A").sum().sum())

# ── Analytics summary panel ───────────────────────────────────────────────────
st.subheader("Analytics Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Bidders Evaluated",  df["bidder"].nunique())
c2.metric("Anomalies Flagged",  len(anomalies))
c3.metric("Est. Negotiation Savings", f"${savings_estimate:,.0f}",
          "if HIGH-anomaly prices → market mean")
c4.metric("Scope Gaps",         missing_cells + na_cells,
          f"{missing_cells} missing + {na_cells} N/A")

st.divider()

# ── Config inputs ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns([2, 1])
with col_a:
    project_name = st.text_input(
        "Project name",
        value="Project Bimbi — LV Cable Supply",
        placeholder="e.g. Substation Alpha — MV Switchgear",
    )
with col_b:
    top_n = st.slider("Bidders to include in memo", 2, min(6, len(scorecard)), 3)

custom_notes = st.text_area(
    "Additional evaluator notes (optional)",
    placeholder="e.g. Bidder B has confirmed delivery schedule; "
                "Bidder D requires clarification on warranty terms…",
    height=90,
)

st.divider()

# ── Generate button ───────────────────────────────────────────────────────────
import os
can_generate = bool(get_env("OPENAI_API_KEY"))

if not can_generate:
    st.warning("OpenAI API key required to generate memo. Add it to .env.")
    # Show a static preview so the demo still looks complete
    scorecard_rows = scorecard.head(top_n).to_dict(orient="records")
    top = scorecard_rows[0]
    st.markdown(
        f"""
        **Preview (static — add OPENAI_API_KEY for full AI generation)**

        ---
        **PROCUREMENT AWARD RECOMMENDATION MEMO**

        Project: {project_name}

        **Recommended Award: Bidder {top['bidder']}**
        Total: ${top['total_bid']:,.0f} | Score: {top['overall_score']:.1f}/100

        *Add your OPENAI_API_KEY to generate the full AI-written memo.*
        """,
    )
    st.stop()

generate_btn = st.button("⚡ Generate AI Memo", use_container_width=True, type="primary")

if "memo_text" not in st.session_state:
    st.session_state["memo_text"] = ""

if generate_btn:
    from core.ai_memo import generate_award_memo
    scorecard_rows = scorecard.head(top_n).to_dict(orient="records")
    anomaly_summary = {
        "count":      len(anomalies),
        "high_count": int((anomalies["direction"] == "HIGH").sum()),
        "low_count":  int((anomalies["direction"] == "LOW").sum()),
        "max_z":      float(anomalies["z_score"].max()) if not anomalies.empty else 0.0,
    }
    scope_gap_summary = {"missing_cells": missing_cells, "na_cells": na_cells}

    with st.spinner("GPT-4o-mini is drafting your memo…"):
        memo = generate_award_memo(
            project_name=project_name,
            scorecard_rows=scorecard_rows,
            anomaly_summary=anomaly_summary,
            scope_gap_summary=scope_gap_summary,
            savings_estimate=savings_estimate,
            custom_notes=custom_notes,
        )
    st.session_state["memo_text"] = memo

if st.session_state["memo_text"]:
    st.divider()
    st.subheader("Generated Memo")

    # Memo rendered in a styled container
    st.markdown(
        f"""
        <div style="
            background: rgba(0,212,170,0.04);
            border: 1px solid rgba(0,212,170,0.18);
            border-radius: 12px;
            padding: 2rem 2.4rem;
            font-family: 'Georgia', serif;
            font-size: 0.93rem;
            line-height: 1.75;
            color: #d8e0ec;
            white-space: pre-wrap;
        ">{st.session_state["memo_text"]}</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.download_button(
        label="📥 Download Memo (.txt)",
        data=st.session_state["memo_text"],
        file_name=f"award_memo_{project_name.replace(' ','_')[:40]}.txt",
        mime="text/plain",
        use_container_width=True,
    )

# ── Supporting tables ─────────────────────────────────────────────────────────
st.divider()
with st.expander("📊 Supporting Data — Vendor Scorecard"):
    st.dataframe(
        scorecard[["bidder", "total_bid", "rank", "price_score",
                   "coverage_score", "consistency_score", "overall_score"]]
        .rename(columns={"bidder": "Bidder", "total_bid": "Total Bid",
                         "rank": "Rank", "price_score": "Price",
                         "coverage_score": "Coverage", "consistency_score": "Consistency",
                         "overall_score": "Score"})
        .style.format({"Total Bid": "${:,.0f}", "Price": "{:.1f}",
                       "Coverage": "{:.1f}", "Consistency": "{:.1f}", "Score": "{:.1f}"})
        .background_gradient(subset=["Score"], cmap="YlGn"),
        use_container_width=True, hide_index=True,
    )

with st.expander("💰 Negotiation Opportunities — High-Anomaly Items"):
    if high_anom.empty:
        st.success("No overpriced anomalies detected.")
    else:
        display = high_anom[[
            "item_no", "description", "bidder", "unit_price", "item_mean",
            "z_score", "saving_per_unit", "qty", "est_saving",
        ]].rename(columns={
            "item_no": "#", "description": "Description", "bidder": "Bidder",
            "unit_price": "Bid Price", "item_mean": "Market Mean",
            "z_score": "Z-score", "saving_per_unit": "Δ/Unit",
            "qty": "Qty", "est_saving": "Est. Saving",
        }).sort_values("Est. Saving", ascending=False)
        st.dataframe(
            display.style.format({
                "Bid Price": "${:.4f}", "Market Mean": "${:.4f}",
                "Z-score": "{:.2f}", "Δ/Unit": "${:.4f}",
                "Qty": "{:,.0f}", "Est. Saving": "${:,.0f}",
            }),
            use_container_width=True, hide_index=True,
        )
        st.metric(
            "Total Estimated Savings (if all HIGH anomalies negotiated to market mean)",
            f"${savings_estimate:,.0f}",
        )
