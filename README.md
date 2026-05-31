# ⚡ BidLite — Vector-Powered Procurement Intelligence

> **Qdrant Hackathon 2026** submission by **Shakir**  
> *"Think Outside the Bot"*

BidLite transforms a Quote Comparison Sheet (QCS) into a full procurement intelligence platform. It uses Qdrant not just as a search engine but as a **prediction engine**, **memory store**, and **multi-agent coordination layer** — delivering capabilities no spreadsheet or chatbot can match.

---

## 🔴 Live Demo

**[https://bidlite-pmsfq22xipn75rn7kwswus.streamlit.app](https://bidlite-pmsfq22xipn75rn7kwswus.streamlit.app)**

Use the sidebar to load **Sample Data (Project Bimbi)** — no upload required.

---

## 🎯 What BidLite Does

Upload a QCS Excel or PDF with bids from multiple vendors. BidLite instantly delivers:

| Page | Feature | Novel? |
|---|---|---|
| **Home** | KPI dashboard — bid rankings, vendor scores, risk flags | |
| **Price Comparison** | Item-by-item grouped bar + spread heatmap | |
| **Anomaly Detection** | Z-score outlier flagging + negotiation savings estimator | |
| **Scope Gaps** | Coverage heatmap — who priced what | |
| **Semantic Search** | Natural-language search via Qdrant vectors | ✅ Qdrant |
| **Vendor Profiles** | Radar chart, bubble chart, multi-criteria scoring | |
| **AI Award Memo** | GPT-4o-mini drafts a formal procurement recommendation memo | ✅ LLM |
| **Prediction** | Ridge regression + **Qdrant KNN regression** price forecast | ✅ Qdrant + ML |
| **Multi-Agent** | 5 AI agents collaborate — PMA, RA, NA, ACA, PIA | ✅ Agents |

---

## 🔵 How Qdrant Powers BidLite (5 Distinct Uses)

### 1. Semantic Item Search
Every bid line item is embedded with `text-embedding-3-small` and stored in Qdrant. A query like *"aluminium 500 kcmil armoured cable"* retrieves physically similar items even when exact spec strings differ across bidders or projects.

### 2. Anomaly Nearest-Neighbour Context
When a price outlier is detected (z-score > threshold), BidLite queries Qdrant for the K nearest semantic neighbours to show whether the anomaly is consistent across similar items — or isolated to one item/bidder.

### 3. Qdrant KNN Regression (Novel — Qdrant as ML Engine)
For each line item, BidLite queries Qdrant for K=15 nearest neighbours. The **similarity scores become regression weights** — producing a vector-similarity-weighted average "fair market price". This is fundamentally different from traditional search: Qdrant is running a K-nearest-neighbours regression, not retrieval.

```
For each item:
  embed(description) → query Qdrant → top-15 neighbours
  predicted_price = Σ(score_i × price_i) / Σ(score_i)
```

The ensemble of Ridge regression + Qdrant KNN produces confidence estimates: when both models agree, the prediction is reliable; when they diverge, the item is flagged as uncertain.

### 4. Procurement Memory Agent (Multi-Agent System)
The PMA agent uses Qdrant to simulate a historical procurement database — retrieving semantically similar historical tenders to benchmark the current project. In production, this scales to thousands of historical QCS files across an organisation.

### 5. Payload Index for Filtered Queries
A `KEYWORD` payload index on the `bidder` field enables bidder-filtered semantic searches (`MatchAny` filter), allowing analysts to restrict Qdrant results to specific vendors during comparison.

---

## 🤖 Multi-Agent System

Five specialised AI agents collaborate on a complete procurement review:

```
User uploads QCS
        ↓
PIA starts analysis
        ↓
    Calls PMA  →  Qdrant historical retrieval → avg award $14.2M, 7 similar projects
        ↓
    Calls RA   →  Risk scoring per vendor → Bidder E: 84/100 (High)
        ↓
    Calls NA   →  Savings quantification → $235,775 across 7 items
        ↓
    Calls ACA  →  Committee simulation:
                    Finance    → Bidder A  (price focus)
                    Engineering→ Bidder C  (scope/risk focus — dissents)
                    Procurement→ Bidder A  (multi-criteria)
                    Executive  → Bidder A  (strategic)
                    Consensus  → Bidder A (3-1 vote, 88% confidence)
        ↓
PIA final recommendation + Board Report (downloadable)
```

The **Award Committee Agent** is the wow factor: it simulates four real procurement committees with different weighted priorities, producing a realistic multi-stakeholder consensus with minority dissent — exactly how real procurement committees work.

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/ChaqBD/BidLite.git
cd BidLite

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Edit .env — add your keys (see Environment Variables below)

# 4. Run
streamlit run app.py
```

### Qdrant options
| Option | Setup |
|---|---|
| **Qdrant Cloud (recommended)** | Create free cluster at [cloud.qdrant.io](https://cloud.qdrant.io), copy URL + API key to `.env` |
| **Local Docker** | `docker run -p 6333:6333 qdrant/qdrant` then set `QDRANT_URL=http://localhost:6333` |

---

## ☁️ Deploy to Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Select repo `ChaqBD/BidLite`, branch `master`, file `app.py`
3. In **Advanced Settings → Secrets**, paste:

```toml
OPENAI_API_KEY    = "sk-proj-..."
QDRANT_URL        = "https://your-cluster.cloud.qdrant.io"
QDRANT_API_KEY    = "eyJhbG..."
QDRANT_COLLECTION = "bidlite"
```

4. Click **Deploy** — public URL ready in ~2 minutes.

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | Embeddings (`text-embedding-3-small`) + GPT-4o-mini |
| `QDRANT_URL` | Yes | `http://localhost:6333` | Qdrant instance URL |
| `QDRANT_API_KEY` | Cloud only | — | Qdrant Cloud API key |
| `QDRANT_COLLECTION` | No | `bidlite` | Collection name |

---

## 📁 Project Structure

```
BidLite/
│
├── app.py                        # Home dashboard — KPIs, risk flags, bid ranking
│
├── pages/
│   ├── 1_Price_Comparison.py     # Item-by-item price comparison + spread heatmap
│   ├── 2_Anomaly_Detection.py    # Z-score anomaly detection + negotiation savings
│   ├── 3_Scope_Gaps.py           # Scope gap / coverage heatmap
│   ├── 4_Semantic_Search.py      # Natural language search via Qdrant
│   ├── 5_Vendor_Profile.py       # Radar chart + multi-criteria award recommendation
│   ├── 6_AI_Memo.py              # GPT-4o-mini award recommendation memo + download
│   ├── 7_Prediction.py           # Ridge + Qdrant KNN ensemble price prediction
│   └── 8_Multi_Agent.py          # Multi-agent procurement review (PMA/RA/NA/ACA/PIA)
│
├── core/
│   ├── agents.py                 # Five-agent system: PMA, RA, NA, ACA, PIA
│   ├── ai_insight.py             # GPT commentary on ML prediction results
│   ├── ai_memo.py                # GPT award recommendation memo generator
│   ├── analytics.py              # Price comparison, anomaly detection, vendor scoring
│   ├── embedder.py               # OpenAI text-embedding-3-small wrapper + batching
│   ├── env.py                    # Secrets helper — works with .env and Streamlit Cloud
│   ├── parser.py                 # QCS Excel/PDF ingestion and normalisation
│   ├── predictor.py              # Ridge regression + Qdrant KNN price prediction
│   ├── theme.py                  # Animated dark navy CSS theme (injected per page)
│   └── vector_store.py           # Qdrant CRUD, payload indexing, KNN search
│
├── test_data/
│   ├── project_alpha_qcs.xlsx    # Anonymised QCS (25 items, 6 bidders, same figures)
│   ├── generate_test_data.py     # Reproducible generator script
│   └── README.md                 # Anonymisation map and format documentation
│
├── .streamlit/
│   ├── config.toml               # Dark navy theme base configuration
│   └── secrets.toml.example      # Secrets template for Streamlit Cloud deployment
│
├── .env.example                  # Local environment template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 📊 Sample Data

`test_data/project_alpha_qcs.xlsx` — an anonymised QCS derived from a real 6-bidder LV cable procurement:

- **25 line items** — single-core, multi-core, armoured, and earth cables
- **6 anonymous bidders** (Vendor Alpha → Vendor Zeta)
- **Bid range**: ~$14.4M – $16.0M
- **Anonymisation**: NEC/AWG names converted to IEC metric (mm²); internal spec codes replaced with generic `EL-LV-XX-XXXX`; quantities and unit prices unchanged

Upload via sidebar **"Upload QCS File"** to test the full parsing pipeline.

---

## 🏗️ Architecture

```
QCS file (Excel / PDF)
        │
        ▼
  core/parser.py          ← normalise to tidy DataFrame
        │
        ├─► core/analytics.py    ← price comparison, anomaly, scoring
        │
        ├─► core/embedder.py     ← OpenAI text-embedding-3-small
        │          │
        │          ▼
        │    core/vector_store.py ← Qdrant upsert / search / index
        │
        ├─► core/predictor.py    ← Ridge + Qdrant KNN regression
        │
        ├─► core/agents.py       ← Multi-agent pipeline
        │          │
        │          ├── PMA (Qdrant memory)
        │          ├── RA  (risk scoring)
        │          ├── NA  (negotiation)
        │          ├── ACA (committee simulation)
        │          └── PIA (orchestrator)
        │
        └─► core/ai_memo.py      ← GPT award memo
            core/ai_insight.py   ← GPT prediction commentary
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Vector database | [Qdrant](https://qdrant.tech) — semantic search, KNN regression, payload indexing |
| Embeddings | [OpenAI](https://platform.openai.com) `text-embedding-3-small` (1536-d) |
| LLM | [OpenAI](https://platform.openai.com) `gpt-4o-mini` — memos, agent narratives |
| ML | [scikit-learn](https://scikit-learn.org) — Ridge regression, LOO cross-validation |
| Dashboard | [Streamlit](https://streamlit.io) — multipage app with dark navy theme |
| Charts | [Plotly](https://plotly.com) — interactive bar, scatter, heatmap, radar |
| Data | [pandas](https://pandas.pydata.org) / [NumPy](https://numpy.org) |
| Excel/PDF | [openpyxl](https://openpyxl.readthedocs.io) / [pdfplumber](https://github.com/jsvine/pdfplumber) |

---

## ✅ Hackathon Eligibility

| Requirement | Status |
|---|---|
| Uses Qdrant as material part of the project | ✅ 5 distinct Qdrant use cases |
| Public GitHub repository | ✅ [ChaqBD/BidLite](https://github.com/ChaqBD/BidLite) |
| README with install + run instructions | ✅ This file |
| Third-party dependencies documented | ✅ `requirements.txt` + table above |
| Demo video ≤ 3 minutes | 🎬 Record at the live URL above |

---

## 👤 Author

**Shakir** · Qdrant Hackathon 2026  
*BidLite — "Think Outside the Bot"*
