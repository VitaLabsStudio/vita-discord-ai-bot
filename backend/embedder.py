import os
import openai
from typing import List
from .schemas import ChunkMetadata

openai.api_key = os.getenv("OPENAI_API_KEY")

EMBED_MODEL = "text-embedding-3-small"


def embed_chunks(chunks: List[ChunkMetadata]) -> List[List[float]]:
    """
    Generate embeddings for a list of chunk texts using OpenAI.
    Args:
        chunks: List of ChunkMetadata.
    Returns:
        List of embedding vectors.
    """
    texts = [c.cleaned_text or c.original_text for c in chunks]
    embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        resp = openai.embeddings.create(input=batch, model=EMBED_MODEL)
        batch_embeds = [d["embedding"] for d in resp["data"]]
        embeddings.extend(batch_embeds)
    return embeddings 