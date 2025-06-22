import json
from typing import List
from pathlib import Path
from .schemas import ChunkMetadata

CHUNK_STORE_PATH = Path("chunks.json")

def save_chunks(chunks: List[ChunkMetadata]) -> None:
    """Save a list of ChunkMetadata to the local store."""
    data = [c.model_dump() for c in chunks]
    if CHUNK_STORE_PATH.exists():
        with open(CHUNK_STORE_PATH, "r") as f:
            existing = json.load(f)
        data = existing + data
    with open(CHUNK_STORE_PATH, "w") as f:
        json.dump(data, f)

def load_chunks() -> List[ChunkMetadata]:
    """Load all chunks from the local store."""
    if not CHUNK_STORE_PATH.exists():
        return []
    with open(CHUNK_STORE_PATH, "r") as f:
        data = json.load(f)
    return [ChunkMetadata(**c) for c in data] 