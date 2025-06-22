import json
from typing import Set
from pathlib import Path

LOG_PATH = Path("processed_log.json")

def load_processed_ids() -> Set[str]:
    """Load processed message/file IDs from the log file."""
    if LOG_PATH.exists():
        with open(LOG_PATH, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_ids(ids: Set[str]) -> None:
    """Save processed message/file IDs to the log file."""
    with open(LOG_PATH, "w") as f:
        json.dump(list(ids), f)

def is_processed(msg_id: str) -> bool:
    """Check if a message/file ID has already been processed."""
    ids = load_processed_ids()
    return msg_id in ids

def mark_processed(msg_id: str) -> None:
    """Mark a message/file ID as processed."""
    ids = load_processed_ids()
    ids.add(msg_id)
    save_processed_ids(ids) 