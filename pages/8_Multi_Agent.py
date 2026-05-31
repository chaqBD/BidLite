"""
Page 8 — Multi-Agent Procurement Assistant
Author: Shakir  |  Qdrant Hackathon 2026

Five specialised AI agents collaborate in sequence:
  PMA  Procurement Memory Agent  — Qdrant historical retrieval
  RA   Risk Agent                — Vendor risk scoring
  NA   Negotiation Agent         — Savings quantification
  ACA  Award Committee Agent     — Multi-committee simulation
  PIA  Procurement Intelligence  — Final recommendation

The committee simulation (ACA) is the wow factor: Finance, Engineering,
Procurement, and Executive committees each vote with different weightings,
producing a realistic multi-stakeholder consensus.
"""

import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.theme import inject_theme
from core.env import get_env

st.set_page_config(
    page_title="Multi-Agent Assistant · BidLite",
    page_icon="⚡",
    layout="wide",
)
inject_theme()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="bl-hero">
        <h1>🤖 Multi-Agent Procurement Assistant</h1>
        <p class="subtitle">
            Five specialised AI agents collaborate to produce a complete procurement review —
            <strong style="color:#00d4aa;">Qdrant</strong> powers the memory,
            GPT-4o-mini powers the deliberation.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Gate ──────────────────────────────────────────────────────────────────────
df = st.session_state.get("df")
if df is None or df.empty:
    st.warning("Return to the Home page to load data first.")
    st.stop()

project_name = st.session_state.get("project_label", "Current Project")
has_openai   = bool(get_env("OPENAI_API_KEY"))
indexed      = st.session_state.get("indexed", False)

# ── Architecture diagram ──────────────────────────────────────────────────────
with st.expander("ℹ️ Agent Architecture", expanded=False):
    st.markdown(
        """
| Agent | Role | Qdrant Use |
|---|---|---|
| 🧠 **PMA** — Procurement Memory | Retrieves similar historical tenders | Vector similarity search across project history |
| ⚠️ **RA** — Risk Agent | Scores each bidder's risk profile | Anomaly context from nearest neighbours |
| 💰 **NA** — Negotiation Agent | Identifies savings, suggests targets | Prediction-informed target pricing |
| 🏛️ **ACA** — Award Committee | Simulates Finance / Engineering / Procurement / Executive committees | Risk-adjusted committee scoring |
| 🎯 **PIA** — Procurement Intelligence | Orchestrates and synthesises final recommendation | All of the above |

PIA coordinates — it does not do everything itself. Each agent has a specific remit.
        """
    )

st.divider()

# ── Run button ────────────────────────────────────────────────────────────────
if not has_openai:
    st.info(
        "Add OPENAI_API_KEY to secrets to enable GPT narratives. "
        "All agent computations still run — only the narrative text will be templated."
    )

col_btn, col_note = st.columns([2, 3])
with col_btn:
    run_btn = st.button(
        "⚡ Run Full Procurement Review",
        use_container_width=True,
        type="primary",
    )
with col_note:
    st.caption(
        "Runs all 5 agents sequentially. "
        "GPT-4o-mini generates the narrative for each agent. "
        "Computation is always from real bid data."
    )

# ── Clear previous results when re-running ────────────────────────────────────
if run_btn:
    for k in ["ma_pma","ma_ra","ma_na","ma_aca","ma_pia","ma_report"]:
        st.session_state.pop(k, None)

# ── Pre-compute analytics (needed by agents) ──────────────────────────────────
from core.analytics import vendor_scorecard, detect_price_anomalies, scope_gap_matrix
from core.predictor import build_item_df, ridge_predict, ensemble_predict

@st.cache_data(show_spinner=False)
def get_analytics(df_hash):
    sc   = vendor_scorecard(df)
    anom = detect_price_anomalies(df)
    gaps = scope_gap_matrix(df)
    item_df = build_item_df(df)
    try:
        rd   = ridge_predict(item_df)
        pred = ensemble_predict(rd)
    except Exception:
        pred = None
    return sc, anom, gaps, pred

df_hash   = str(len(df)) + str(df["total_price"].sum())
scorecard, anomalies, gaps, predictions = get_analytics(df_hash)

# ── Agent pipeline execution ──────────────────────────────────────────────────
if run_btn:
    from core.agents import run_pma, run_ra, run_na, run_aca, run_pia

    st.markdown("### 🔄 Agent Pipeline")

    # Placeholder slots for each agent's status line
    slots = {a: st.empty() for a in ["PMA","RA","NA","ACA","PIA"]}
    agent_icons = {"PMA":"🧠","RA":"⚠️","NA":"💰","ACA":"🏛️","PIA":"🎯"}

    def agent_status(name, state):
        icon = agent_icons[name]
        if state == "running":
            slots[name].markdown(
                f'<div style="padding:0.5rem 1rem; margin:0.3rem 0; background:rgba(30,136,229,0.1); '
                f'border:1px solid rgba(30,136,229,0.3); border-radius:8px;">'
                f'🔵 <b>{icon} {name}</b> — running…</div>',
                unsafe_allow_html=True,
            )
        elif state == "done":
            slots[name].markdown(
                f'<div style="padding:0.5rem 1rem; margin:0.3rem 0; background:rgba(0,212,170,0.08); '
                f'border:1px solid rgba(0,212,170,0.3); border-radius:8px;">'
                f'✅ <b>{icon} {name}</b> — Complete</div>',
                unsafe_allow_html=True,
            )

    # PMA
    agent_status("PMA", "running")
    pma_result = run_pma(df, project_name, indexed)
    st.session_state["ma_pma"] = pma_result
    agent_status("PMA", "done")

    # RA
    agent_status("RA", "running")
    ra_result = run_ra(df, scorecard, anomalies, gaps)
    st.session_state["ma_ra"] = ra_result
    agent_status("RA", "done")

    # NA
    agent_status("NA", "running")
    na_result = run_na(df, anomalies, predictions)
    st.session_state["ma_na"] = na_result
    agent_status("NA", "done")

    # ACA
    agent_status("ACA", "running")
    aca_result = run_aca(scorecard, ra_result)
    st.session_state["ma_aca"] = aca_result
    agent_status("ACA", "done")

    # PIA
    agent_status("PIA", "running")
    pia_result = run_pia(project_name, df, scorecard, pma_result, ra_result, na_result, aca_result)
    st.session_state["ma_pia"] = pia_result
    agent_status("PIA", "done")

    st.success("All agents complete — full procurement review ready.")

# ── Display results (from session_state so they persist across reruns) ─────────
pma = st.session_state.get("ma_pma")
ra  = st.session_state.get("ma_ra")
na  = st.session_state.get("ma_na")
aca = st.session_state.get("ma_aca")
pia = st.session_state.get("ma_pia")

if not all([pma, ra, na, aca, pia]):
    st.stop()

# ── Final Recommendation Banner ───────────────────────────────────────────────
st.divider()
winner    = pia["recommended_vendor"]
conf      = pia["confidence"]
risk_col  = {"Low":"#00d4aa","Medium":"#f4a261","High":"#d62728"}.get(pia["risk_level"], "#c9d1d9")

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, rgba(0,212,170,0.12), rgba(30,136,229,0.08));
        border: 1px solid rgba(0,212,170,0.35);
        border-radius: 16px;
        padding: 1.8rem 2.2rem;
        margin-bottom: 1.2rem;
    ">
        <div style="font-size:0.8rem; color:#7a8899; text-transform:uppercase; letter-spacing:0.12em;">
            PIA Final Recommendation
        </div>
        <div style="font-size:2rem; font-weight:800; color:#00d4aa; margin:0.3rem 0;">
            Bidder {winner}
        </div>
        <div style="font-size:0.9rem; color:#c9d1d9;">
            Confidence <strong style="color:#00d4aa;">{conf}%</strong> &nbsp;·&nbsp;
            Total Bid <strong>${pia['total_bid']:,.0f}</strong> &nbsp;·&nbsp;
            Score <strong>{pia['overall_score']:.0f}/100</strong> &nbsp;·&nbsp;
            Risk <strong style="color:{risk_col};">{pia['risk_level']}</strong>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# KPI row
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Recommended",         f"Bidder {winner}")
k2.metric("Confidence",          f"{conf}%")
k3.metric("Expected Savings",    f"${pia['expected_savings']:,.0f}")
k4.metric("Risk Level",          pia["risk_level"])
k5.metric("Similar Hist. Projects", pia["similar_historical_projects"])
k6.metric("Negotiation Items",   pia["negotiation_opportunities"])

st.markdown(
    f'<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(0,212,170,0.1); '
    f'border-radius:10px; padding:1rem 1.4rem; margin:1rem 0; font-style:italic; color:#c9d1d9; '
    f'font-size:0.9rem; line-height:1.7;">{pia["exec_summary"]}</div>',
    unsafe_allow_html=True,
)

st.divider()

# ── Agent detail cards ─────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

# PMA card
with col_l:
    with st.expander("🧠 PMA — Historical Analysis Complete", expanded=True):
        p1, p2, p3 = st.columns(3)
        p1.metric("Similar Projects",  pma["similar_projects"])
        p2.metric("Avg Award Value",   pma["avg_award_fmt"])
        p3.metric("Avg Savings",       f"{pma['avg_savings_pct']:.1f}%")
        st.caption(pma["narrative"])
        if pma["qdrant_used"]:
            st.markdown("✅ Qdrant vector search used for retrieval")
        else:
            st.markdown("ℹ️ Index the project to enable live Qdrant retrieval")

# RA card
with col_r:
    with st.expander("⚠️ RA — Risk Assessment Complete", expanded=True):
        st.caption(ra["narrative"])
        for r in ra["vendor_risks"]:
            color = "#d62728" if r["risk_level"]=="High" else ("#f4a261" if r["risk_level"]=="Medium" else "#00d4aa")
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; padding:0.3rem 0.6rem; '
                f'margin:0.2rem 0; background:rgba(255,255,255,0.03); border-radius:6px; '
                f'border-left:3px solid {color};">'
                f'<span>Bidder {r["bidder"]}</span>'
                f'<span style="color:{color}; font-weight:700;">{r["risk_score"]}/100 {r["risk_level"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

col_l2, col_r2 = st.columns(2)

# NA card
with col_l2:
    with st.expander("💰 NA — Negotiation Analysis Complete", expanded=True):
        n1, n2 = st.columns(2)
        n1.metric("Total Saving",    f"${na['total_savings']:,.0f}")
        n2.metric("Priority Items",  na["n_opportunities"])
        st.caption(na["narrative"])
        if na["targets"]:
            st.markdown("**Top Priority Items:**")
            for t in na["targets"][:3]:
                saving = t.get("est_saving", 0)
                st.markdown(
                    f"- Item `{int(t['item_no'])}` · Bidder {t['bidder']} · "
                    f"${t['unit_price']:.4f} → target ${t['target_price']:.4f} "
                    f"(*save ${saving:,.0f}*)"
                )

# ACA card
with col_r2:
    with st.expander("🏛️ ACA — Committee Evaluation Complete", expanded=True):
        vote_str = " · ".join(f"{c}: **{p}**" for c, p in aca["preferences"].items())
        st.markdown(f"**Votes:** {vote_str}")
        st.markdown(f"**Consensus: Bidder {aca['consensus']}** ({aca['n_votes']}/{len(aca['preferences'])} committees)")
        st.divider()
        for committee, narrative in aca["committee_narratives"].items():
            pref    = aca["preferences"][committee]
            is_cons = pref == aca["consensus"]
            badge   = f'<span style="background:rgba(0,212,170,0.15); color:#00d4aa; padding:1px 6px; border-radius:4px; font-size:0.75rem;">Bidder {pref}</span>'
            st.markdown(
                f'**{committee} Committee** {badge}',
                unsafe_allow_html=True,
            )
            st.caption(narrative)

# ── Committee vote chart ───────────────────────────────────────────────────────
st.divider()
st.subheader("🏛️ Committee Score Breakdown")

comm_rows = []
for committee, scores in aca["committee_scores"].items():
    for bidder, score in scores.items():
        comm_rows.append({"Committee": committee, "Bidder": bidder, "Score": round(score, 1)})

comm_df = pd.DataFrame(comm_rows)
vote_fig = px.bar(
    comm_df,
    x="Committee", y="Score", color="Bidder", barmode="group",
    color_discrete_sequence=["#00d4aa","#1e88e5","#f4a261","#e76f51","#a8dadc","#457b9d"],
    labels={"Score": "Weighted Score", "Committee": ""},
)
vote_fig.update_layout(
    height=360,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=10),
)
st.plotly_chart(vote_fig, use_container_width=True)

# ── Risk radar ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("⚠️ Bidder Risk Profile")

risk_df = pd.DataFrame([
    {"Bidder": r["bidder"], "Risk Score": r["risk_score"], "Level": r["risk_level"]}
    for r in ra["vendor_risks"]
]).sort_values("Risk Score", ascending=True)

risk_fig = px.bar(
    risk_df, x="Risk Score", y="Bidder", orientation="h",
    color="Risk Score",
    color_continuous_scale=[[0,"#00d4aa"],[0.4,"#f4a261"],[0.7,"#d62728"],[1,"#7b241c"]],
    text=risk_df["Risk Score"].apply(lambda v: f"{v}/100"),
)
risk_fig.update_traces(textposition="outside")
risk_fig.update_layout(
    height=280, coloraxis_showscale=False,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    xaxis=dict(range=[0,115], gridcolor="rgba(255,255,255,0.05)"),
    margin=dict(t=10),
)
st.plotly_chart(risk_fig, use_container_width=True)

# ── Board Report ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Generate Board Report")
st.caption(
    "Compiles all agent findings into a formal procurement executive report. "
    "Suitable for board submission, audit files, and award documentation."
)

if st.button("📄 Generate Board Report", use_container_width=True):
    from core.agents import generate_board_report
    report = generate_board_report(project_name, pma, ra, na, aca, pia)
    st.session_state["ma_report"] = report

if st.session_state.get("ma_report"):
    report_text = st.session_state["ma_report"]
    st.markdown(
        f"""<div style="
            background: rgba(0,212,170,0.03);
            border: 1px solid rgba(0,212,170,0.15);
            border-radius: 12px;
            padding: 1.5rem 2rem;
            font-family: 'Courier New', monospace;
            font-size: 0.82rem;
            line-height: 1.65;
            color: #c9d1d9;
            white-space: pre-wrap;
            max-height: 500px;
            overflow-y: auto;
        ">{report_text}</div>""",
        unsafe_allow_html=True,
    )
    st.download_button(
        "📥 Download Board Report (.txt)",
        data=report_text,
        file_name=f"board_report_{project_name.replace(' ','_')[:35]}.txt",
        mime="text/plain",
        use_container_width=True,
    )
