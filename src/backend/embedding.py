# Embedding logic will be implemented here 

import os
from typing import List, Dict, Any
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from openai import AsyncOpenAI
import json

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "discord-knowledge")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Ensure we have the required API keys
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY environment variable is required")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

print(f"DEBUG: Using Pinecone index: {PINECONE_INDEX}")
print(f"DEBUG: Pinecone cloud: {PINECONE_CLOUD}")
print(f"DEBUG: Pinecone region: {PINECONE_REGION}")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Pinecone index setup (1536 dimensions for OpenAI ada-002)
pinecone = Pinecone(api_key=PINECONE_API_KEY)
index = pinecone.Index(PINECONE_INDEX)

async def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of text chunks using OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            input=chunks,
            model="text-embedding-ada-002"
        )
        return [d.embedding for d in response.data]
    except Exception as e:
        print(f"DEBUG: Embedding error: {e}")
        raise e

def sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all metadata values are valid for Pinecone (no None/nulls)."""
    sanitized = {}
    for k, v in meta.items():
        if v is None:
            sanitized[k] = ""
        elif isinstance(v, list):
            sanitized[k] = [str(x) if x is not None else "" for x in v]
        elif isinstance(v, (str, int, float, bool)):
            sanitized[k] = v
        else:
            sanitized[k] = str(v)
    return sanitized

async def store_embeddings(embeddings: List[List[float]], metadatas: List[Dict[str, Any]]) -> None:
    """Store embeddings and metadata in Pinecone."""
    vectors = []
    for emb, meta in zip(embeddings, metadatas):
        sanitized_meta = sanitize_metadata(meta)
        # Extra validation: ensure all values are valid Pinecone types
        for k, v in sanitized_meta.items():
            if v is None:
                sanitized_meta[k] = ""
            elif isinstance(v, list):
                sanitized_meta[k] = [str(x) if x is not None else "" for x in v]
            elif not isinstance(v, (str, int, float, bool)):
                sanitized_meta[k] = str(v)
        print(f"DEBUG: Upserting vector metadata: {json.dumps(sanitized_meta)}")
        vectors.append({
            "id": sanitized_meta["message_id"],
            "values": emb,
            "metadata": sanitized_meta
        })
    index.upsert(vectors=vectors) 