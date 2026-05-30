"""
Shared CSS theme for BidLite — dark navy with teal accents and a flowing
animated gradient background. Call inject_theme() at the top of every page.
"""

import streamlit as st

_CSS = """
<style>
/* ── Flowing animated background ───────────────────────────────────────── */
@keyframes gradientFlow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.stApp {
    background: linear-gradient(
        -45deg,
        #050e1a,
        #0a1628,
        #071c2e,
        #0d2137,
        #071520
    ) !important;
    background-size: 400% 400% !important;
    animation: gradientFlow 20s ease infinite !important;
}

/* Subtle particle-grid overlay */
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(circle at 20% 80%, rgba(0,212,170,0.04) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(30,136,229,0.04) 0%, transparent 50%),
        radial-gradient(circle at 50% 50%, rgba(0,212,170,0.02) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}

/* ── Global typography ──────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
    color: #e8eaf6 !important;
}

h1 { font-size: 2rem !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 1.35rem !important; font-weight: 600 !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; }
h1, h2, h3, h4 { color: #e8eaf6 !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(5, 14, 26, 0.92) !important;
    border-right: 1px solid rgba(0, 212, 170, 0.12) !important;
    backdrop-filter: blur(20px) !important;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(0,212,170,0.12) !important; }

/* ── KPI metric cards ───────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: linear-gradient(
        135deg,
        rgba(0, 212, 170, 0.08),
        rgba(30, 136, 229, 0.05)
    ) !important;
    border: 1px solid rgba(0, 212, 170, 0.22) !important;
    border-radius: 14px !important;
    padding: 1.1rem 1.3rem !important;
    backdrop-filter: blur(16px) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(0, 212, 170, 0.45) !important;
    box-shadow: 0 0 20px rgba(0, 212, 170, 0.12) !important;
}
[data-testid="stMetricValue"] {
    color: #00d4aa !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #7a8899 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #00d4aa 0%, #0099cc 100%) !important;
    color: #050e1a !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.18s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(0, 212, 170, 0.35) !important;
}

/* ── Dividers ───────────────────────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid rgba(0,212,170,0.12) !important; margin: 1.2rem 0 !important; }

/* ── Input / select / multiselect ──────────────────────────────────────── */
.stTextInput input,
.stTextArea textarea,
[data-baseweb="select"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(0,212,170,0.2) !important;
    border-radius: 9px !important;
    color: #e8eaf6 !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: rgba(0,212,170,0.55) !important;
    box-shadow: 0 0 0 2px rgba(0,212,170,0.12) !important;
}
[data-baseweb="select"] * { color: #e8eaf6 !important; }

/* ── Slider ─────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stThumbValue"] {
    color: #00d4aa !important;
}

/* ── DataFrames / tables ────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(0,212,170,0.12) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ── Alert / info boxes ─────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left: 3px solid rgba(0,212,170,0.6) !important;
}

/* ── Plotly charts — transparent background ─────────────────────────────── */
.js-plotly-plot .plotly, .js-plotly-plot .plotly .main-svg {
    background: transparent !important;
}

/* ── Caption & small text ───────────────────────────────────────────────── */
.stCaption, small { color: #5a6878 !important; }

/* ── Custom hero banner ─────────────────────────────────────────────────── */
.bl-hero {
    background: linear-gradient(
        135deg,
        rgba(0,212,170,0.08) 0%,
        rgba(30,136,229,0.06) 50%,
        rgba(0,212,170,0.04) 100%
    );
    border: 1px solid rgba(0,212,170,0.18);
    border-radius: 18px;
    padding: 2rem 2.4rem;
    margin-bottom: 1.6rem;
    backdrop-filter: blur(24px);
    position: relative;
    overflow: hidden;
}
.bl-hero::after {
    content: "";
    position: absolute;
    top: -40%; right: -10%;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(0,212,170,0.08), transparent 70%);
    pointer-events: none;
}
.bl-hero h1 { margin: 0 0 0.3rem 0 !important; }
.bl-hero .subtitle {
    color: #7a8899 !important;
    font-size: 0.9rem !important;
    margin: 0 !important;
}

/* ── Risk badge cards ───────────────────────────────────────────────────── */
.bl-risk-card {
    background: rgba(255, 80, 80, 0.07);
    border: 1px solid rgba(255,80,80,0.25);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.bl-warn-card {
    background: rgba(255, 193, 7, 0.07);
    border: 1px solid rgba(255,193,7,0.25);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
::-webkit-scrollbar-thumb { background: rgba(0,212,170,0.25); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,212,170,0.45); }

/* ── Tab bar ────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid rgba(0,212,170,0.15) !important;
    gap: 0.2rem !important;
}
[data-testid="stTabs"] [role="tab"] {
    color: #7a8899 !important;
    border-radius: 8px 8px 0 0 !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #00d4aa !important;
    border-bottom: 2px solid #00d4aa !important;
}

/* ── Radio / Checkbox ───────────────────────────────────────────────────── */
[data-testid="stRadio"] p { color: #c9d1d9 !important; }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
