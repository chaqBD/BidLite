"""
All Qdrant operations for BidLite.

Each bid line item is stored as a Qdrant point:
  - id:      random UUID (one point per bidder×item pair)
  - vector:  OpenAI text-embedding-3-small embedding (1536-d, cosine distance)
  - payload: full item metadata — item_no, description, spec_code, qty, unit,
             bidder, unit_price, total_price, definition

Payload index:
  A KEYWORD index is created on the "bidder" field so that MatchAny filters
  (used in bidder-filtered semantic searches) work without a 400 error in
  qdrant-client >= 1.14. The index is created idempotently on every
  collection access via _ensure_payload_index().

Qdrant is used in three distinct ways in BidLite:
  1. Semantic search     — query_points() with a natural-language embedding
  2. KNN regression      — query_points() with item embedding, scores as weights
  3. Anomaly context     — query_points() for nearest neighbours of anomalous items
"""

import uuid
import pandas as pd
from core.env import get_env
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    PayloadSchemaType,
)
from core.embedder import DIMS

COLLECTION = get_env("QDRANT_COLLECTION", "bidlite")


def get_client() -> QdrantClient:
    url = get_env("QDRANT_URL", "http://localhost:6333")
    api_key = get_env("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)


def _ensure_payload_index(client: QdrantClient) -> None:
    """Create KEYWORD index on 'bidder' so filtered queries work without error."""
    try:
        client.create_payload_index(
            collection_name=COLLECTION,
            field_name="bidder",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass  # Already exists or collection not yet ready


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=DIMS, distance=Distance.COSINE),
        )
    _ensure_payload_index(client)


def upsert_items(client: QdrantClient, df: pd.DataFrame, vectors: list[list[float]]) -> int:
    """Upsert bid items into Qdrant. Returns number of points written."""
    ensure_collection(client)
    points = []
    for i, (_, row) in enumerate(df.iterrows()):
        payload = row.to_dict()
        # Convert NaN to None so Qdrant accepts the payload
        payload = {k: (None if (isinstance(v, float) and v != v) else v)
                   for k, v in payload.items()}
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload=payload,
        ))
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def search_similar(client: QdrantClient, query_vector: list[float],
                   top_k: int = 10,
                   bidder_filter: list[str] | None = None) -> list[dict]:
    """Semantic search: return top-k most similar items."""
    # Ensures KEYWORD index on 'bidder' exists even on pre-existing collections
    _ensure_payload_index(client)
    filt = None
    if bidder_filter:
        filt = Filter(must=[
            FieldCondition(key="bidder", match=MatchAny(any=bidder_filter))
        ])
    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=filt,
        with_payload=True,
    )
    return [{"score": r.score, **r.payload} for r in results.points]


def get_all_items(client: QdrantClient) -> pd.DataFrame:
    """Scroll through all points and return as DataFrame."""
    records = []
    offset = None
    while True:
        result, offset = client.scroll(
            collection_name=COLLECTION,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        records.extend([r.payload for r in result])
        if offset is None:
            break
    return pd.DataFrame(records) if records else pd.DataFrame()


def collection_exists_and_populated(client: QdrantClient) -> bool:
    try:
        info = client.get_collection(COLLECTION)
        return info.points_count > 0
    except Exception:
        return False


def drop_collection(client: QdrantClient) -> None:
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
