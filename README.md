# ⚡ BidLite — Vector-Powered Procurement Intelligence

> Qdrant Hackathon 2026 submission by **Shakir**

BidLite turns Quote Comparison Sheets (QCS) into an interactive analytics platform powered by Qdrant vector search. It goes far beyond a chatbot — delivering semantic item matching, price anomaly detection, scope gap heatmaps, and multi-dimensional vendor scoring.

---

## Demo

| Page | What it does |
|---|---|
| **Home** | KPI dashboard — total bids, rankings, overall vendor scores |
| **Price Comparison** | Item-by-item grouped bar charts and spread heatmap |
| **Anomaly Detection** | Z-score outlier flagging + Qdrant nearest-neighbour context |
| **Scope Gaps** | Coverage heatmap — which bidder priced which item |
| **Semantic Search** | Natural language search across all bid items via Qdrant |
| **Vendor Profiles** | Radar chart, bubble chart, award recommendation |

---

## How Qdrant Powers This

1. **Semantic item matching** — each bid line item is embedded with `text-embedding-3-small` and stored in Qdrant. Searching "aluminium 500 kcmil cable" retrieves similar items even if the exact spec string differs across bid documents.
2. **Anomaly context** — when a price outlier is detected, BidLite queries Qdrant for the nearest neighbours to show whether the anomaly is consistent across semantically similar items.
3. **Cross-bid retrieval** — procurement teams can upload multiple QCS files; Qdrant enables finding matching items across projects for historical benchmarking.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/ChaqBD/BidLite.git
cd BidLite

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant

# 4. Set environment variables
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and QDRANT_URL

# 5. Run BidLite
streamlit run app.py
```

### Without Docker — use Qdrant Cloud
Set `QDRANT_URL` and `QDRANT_API_KEY` in `.env` to a Qdrant Cloud cluster URL.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for vector embeddings |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant instance URL |
| `QDRANT_API_KEY` | — | API key for Qdrant Cloud |
| `QDRANT_COLLECTION` | `bidlite` | Collection name |

---

## Project Structure

```
BidLite/
├── app.py                     # Home dashboard + data loader
├── pages/
│   ├── 1_Price_Comparison.py
│   ├── 2_Anomaly_Detection.py
│   ├── 3_Scope_Gaps.py
│   ├── 4_Semantic_Search.py
│   └── 5_Vendor_Profile.py
├── core/
│   ├── parser.py              # QCS Excel/PDF ingestion
│   ├── embedder.py            # OpenAI embedding wrapper
│   ├── vector_store.py        # Qdrant CRUD operations
│   └── analytics.py           # Analytics computations
├── requirements.txt
└── .env.example
```

---

## Sample Data

The app ships with real-world-shaped sample data from a 6-bidder cable procurement QCS (Project Bimbi — 25 line items, ~$14.6M–$16.1M bid range). No file upload required to explore all features.

---

## Built With

- [Qdrant](https://qdrant.tech) — vector database and semantic search
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings) — `text-embedding-3-small`
- [Streamlit](https://streamlit.io) — dashboard framework
- [Plotly](https://plotly.com) — interactive charts

---

*Author: Shakir · Qdrant Hackathon 2026 · "Think Outside the Bot"*
