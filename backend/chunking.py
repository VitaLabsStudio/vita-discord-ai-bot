"""
Chunking logic for Discord messages: group by thread and time window.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from .schemas import ChunkMetadata
import uuid

def chunk_messages(messages: List[Dict[str, Any]], window_minutes: int = 10, max_group: int = 10) -> List[ChunkMetadata]:
    """
    Chunk messages by thread and time window.
    Args:
        messages: List of message dicts (must include thread_id, timestamp, etc).
        window_minutes: Time window for grouping messages.
        max_group: Max messages per chunk.
    Returns:
        List of ChunkMetadata objects.
    """
    # Sort messages by thread and timestamp
    messages = sorted(messages, key=lambda m: (m.get('thread_id') or m['channel_id'], m['timestamp']))
    chunks = []
    current_chunk = []
    current_thread = None
    window_start = None
    for msg in messages:
        thread = msg.get('thread_id') or msg['channel_id']
        ts = datetime.fromisoformat(msg['timestamp'])
        if (current_thread != thread or
            window_start is None or
            ts - window_start > timedelta(minutes=window_minutes) or
            len(current_chunk) >= max_group):
            if current_chunk:
                chunks.append(_make_chunk(current_chunk))
            current_chunk = [msg]
            current_thread = thread
            window_start = ts
        else:
            current_chunk.append(msg)
    if current_chunk:
        chunks.append(_make_chunk(current_chunk))
    return chunks

def _make_chunk(messages: List[Dict[str, Any]]) -> ChunkMetadata:
    """Helper to create a ChunkMetadata from a group of messages."""
    chunk_id = str(uuid.uuid4())
    message_ids = [m['id'] for m in messages]
    channel_id = messages[0]['channel_id']
    thread_id = messages[0].get('thread_id')
    roles = list({role for m in messages for role in (m.get('roles') or [])})
    timestamp = messages[0]['timestamp']
    original_text = '\n'.join(m['content'] for m in messages)
    cleaned_text = '\n'.join(m.get('cleaned_text', m['content']) for m in messages)
    return ChunkMetadata(
        chunk_id=chunk_id,
        message_ids=message_ids,
        channel_id=channel_id,
        thread_id=thread_id,
        roles=roles,
        timestamp=timestamp,
        original_text=original_text,
        cleaned_text=cleaned_text
    ) 