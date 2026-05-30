"""
All Qdrant operations for BidLite.

Each bid line item is stored as a point with:
  - vector: OpenAI text-embedding-3-small (1536-d)
  - payload: full item metadata for filtering and display
"""

import os
import uuid
import pandas as pd
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)
from core.embedder import DIMS

load_dotenv()

COLLECTION = os.getenv("QDRANT_COLLECTION", "bidlite")


def get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=DIMS, distance=Distance.COSINE),
        )


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
