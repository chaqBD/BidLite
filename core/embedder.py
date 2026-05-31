"""
Generates vector embeddings for bid line items using OpenAI's
text-embedding-3-small model. Each item is encoded as a rich text
string that captures spec, material type, and conductor size so that
semantically similar items (across different description formats)
cluster close together in vector space.
"""

from typing import Optional
import openai
from core.env import get_env

_client: Optional[openai.OpenAI] = None
MODEL = "text-embedding-3-small"
DIMS = 1536


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        api_key = get_env("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment / .env file")
        _client = openai.OpenAI(api_key=api_key)
    return _client


def item_to_text(row: dict) -> str:
    """
    Convert a bid line item dict into a rich natural-language string
    suitable for embedding. Including spec_code helps match items that
    share a spec even when description wording differs across bidders.
    """
    parts = [
        f"Electrical cable: {row.get('description', '')}",
        f"Spec code: {row.get('spec_code', '')}",
        f"Unit: {row.get('unit', '')}",
        f"Quantity: {row.get('qty', '')}",
    ]
    return ". ".join(p for p in parts if p.split(": ", 1)[-1])


def embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed a list of strings, batching to stay within API limits."""
    client = _get_client()
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=MODEL, input=batch)
        all_vectors.extend([r.embedding for r in response.data])
    return all_vectors


def embed_single(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
