"""
Batch ingestion for historical Discord data (cold start).
"""
from typing import List, Dict, Any
from .ingest import ingest_message
from .preprocess import clean_message
from .chunking import chunk_messages
from .chunk_store import save_chunks

def batch_ingest(messages: List[Dict[str, Any]]) -> int:
    """
    Batch ingest a list of Discord messages.
    Args:
        messages: List of message payloads.
    Returns:
        Number of messages successfully ingested.
    """
    # Preprocess and filter out already processed
    to_process = []
    for msg in messages:
        if not ingest_message(msg):
            continue
        cleaned_text, _ = clean_message(msg.get("content", ""))
        msg["cleaned_text"] = cleaned_text
        to_process.append(msg)
    # Chunk in batch
    chunks = chunk_messages(to_process)
    save_chunks(chunks)
    return len(chunks) 