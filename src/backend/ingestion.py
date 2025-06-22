# Ingestion logic will be implemented here 

import os
import json
from typing import Set, Dict, Any, List
from threading import Lock
import tempfile

PROCESSED_LOG_PATH = "processed_messages.json"
_log_lock = Lock()
LOCKS_DIR = "locks"
os.makedirs(LOCKS_DIR, exist_ok=True)

def load_processed_ids() -> Set[str]:
    """Load processed message/file IDs from local log."""
    if not os.path.exists(PROCESSED_LOG_PATH):
        return set()
    with open(PROCESSED_LOG_PATH, "r") as f:
        try:
            return set(json.load(f))
        except Exception:
            return set()

def save_processed_ids(ids: Set[str]) -> None:
    """Save processed message/file IDs to local log."""
    with _log_lock:
        with open(PROCESSED_LOG_PATH, "w") as f:
            json.dump(list(ids), f)

def is_processed(message_id: str) -> bool:
    """Check if a message/file ID has already been processed, using a lock file to prevent race conditions."""
    lock_path = os.path.join(LOCKS_DIR, f"{message_id}.lock")
    if os.path.exists(lock_path):
        return True
    processed = load_processed_ids()
    return message_id in processed

def mark_processed(message_id: str) -> None:
    """Mark a message/file ID as processed and remove its lock file."""
    processed = load_processed_ids()
    processed.add(message_id)
    save_processed_ids(processed)
    lock_path = os.path.join(LOCKS_DIR, f"{message_id}.lock")
    if os.path.exists(lock_path):
        os.remove(lock_path)

def batch_ingest_historical(messages: List[Dict[str, Any]]) -> List[str]:
    """Batch ingest historical messages, skipping already processed ones."""
    processed_ids = load_processed_ids()
    new_ids = []
    for msg in messages:
        msg_id = msg.get("message_id")
        if msg_id and msg_id not in processed_ids:
            # TODO: Process message (clean, chunk, etc.)
            processed_ids.add(msg_id)
            new_ids.append(msg_id)
    save_processed_ids(processed_ids)
    return new_ids 