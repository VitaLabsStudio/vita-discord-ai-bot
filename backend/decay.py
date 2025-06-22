from typing import List
from .schemas import ChunkMetadata
from .chunk_store import load_chunks, save_chunks
from datetime import datetime, timedelta

ARCHIVE_AGE_DAYS = 30


def archive_old_chunks() -> int:
    """
    Archive or summarize chunks older than ARCHIVE_AGE_DAYS.
    Returns:
        Number of archived chunks.
    """
    now = datetime.utcnow()
    chunks = load_chunks()
    to_archive = [c for c in chunks if (now - datetime.fromisoformat(c.timestamp)).days > ARCHIVE_AGE_DAYS]
    # Stub: just mark as archived
    for c in to_archive:
        c.cleaned_text = "[ARCHIVED] " + (c.cleaned_text or c.original_text)
    save_chunks(chunks)
    return len(to_archive)

def remove_chunk_by_message_id(msg_id: str) -> bool:
    """
    Remove a chunk if a message is deleted/edited.
    Returns:
        True if removed, False otherwise.
    """
    chunks = load_chunks()
    new_chunks = [c for c in chunks if msg_id not in c.message_ids]
    if len(new_chunks) < len(chunks):
        save_chunks(new_chunks)
        return True
    return False

def feedback_chunk(chunk_id: str, feedback: str) -> None:
    """
    Record feedback (like/dislike/flag) for a chunk. Stub for now.
    """
    # TODO: Implement feedback logic
    pass 