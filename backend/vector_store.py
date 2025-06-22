import os
import pinecone
from typing import List, Dict, Any
from .schemas import ChunkMetadata

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pinecone.init(api_key=PINECONE_API_KEY, environment="us-east1-gcp")
INDEX_NAME = "vita-discord-ai"

if INDEX_NAME not in pinecone.list_indexes():
    pinecone.create_index(INDEX_NAME, dimension=1536, metric="cosine")
index = pinecone.Index(INDEX_NAME)

def upsert_chunks(chunks: List[ChunkMetadata], embeddings: List[List[float]]) -> None:
    """
    Upsert chunk embeddings and metadata into Pinecone.
    Args:
        chunks: List of ChunkMetadata.
        embeddings: List of embedding vectors.
    """
    vectors = []
    for chunk, emb in zip(chunks, embeddings):
        meta = chunk.model_dump()
        vectors.append((chunk.chunk_id, emb, meta))
    index.upsert(vectors)

def query_chunks(query_emb: List[float], top_k: int, user_roles: List[str], channel_id: str) -> List[Dict[str, Any]]:
    """
    Query Pinecone for top-k relevant chunks, filtered by permissions.
    Args:
        query_emb: Embedding vector for the query.
        top_k: Number of results.
        user_roles: Roles of the querying user.
        channel_id: Channel context.
    Returns:
        List of chunk metadata dicts.
    """
    filter_ = {
        "$or": [
            {"roles": {"$in": user_roles}},
            {"channel_id": channel_id}
        ]
    }
    res = index.query(vector=query_emb, top_k=top_k, include_metadata=True, filter=filter_)
    return [m["metadata"] for m in res["matches"]] 