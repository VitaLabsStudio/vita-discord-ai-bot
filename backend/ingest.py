"""
Ingestion module for event-driven, idempotent message and file ingestion.
"""
from typing import Any, Dict, List
from .processed_log import is_processed, mark_processed
import requests
import os
from .preprocess import clean_message
from .chunking import chunk_messages
from .chunk_store import save_chunks
from .schemas import ChunkMetadata

def download_attachments(attachments: List[str], download_dir: str = "tmp") -> List[str]:
    """Download attachments and return local file paths."""
    os.makedirs(download_dir, exist_ok=True)
    local_paths = []
    for url in attachments:
        filename = os.path.join(download_dir, url.split("/")[-1])
        try:
            r = requests.get(url)
            with open(filename, "wb") as f:
                f.write(r.content)
            local_paths.append(filename)
        except Exception:
            continue
    return local_paths

def ingest_message(message: Dict[str, Any]) -> bool:
    """
    Ingest a new Discord message if not already processed.
    Args:
        message: The message payload from Discord.
    Returns:
        True if ingested, False if already processed.
    """
    msg_id = message["id"]
    if is_processed(msg_id):
        return False
    # Download attachments if any
    attachments = message.get("attachments") or []
    if attachments:
        download_attachments(attachments)
    # Preprocess and clean message
    cleaned_text, pii_found = clean_message(message.get("content", ""))
    message["cleaned_text"] = cleaned_text
    # Chunking: for single message, chunk is just itself
    chunk = chunk_messages([message], window_minutes=10, max_group=1)[0]
    save_chunks([chunk])
    mark_processed(msg_id)
    return True 