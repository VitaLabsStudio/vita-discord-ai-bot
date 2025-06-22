# Utility functions will be implemented here 

import re
import spacy
from typing import List, Dict, Any

nlp = spacy.blank("en")

EMOJI_PATTERN = re.compile(r"[\U00010000-\U0010ffff]+", flags=re.UNICODE)
PII_PATTERN = re.compile(r"\b(\d{3}[-.]?\d{2}[-.]?\d{4}|\d{16}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")


def clean_text(text: str) -> str:
    """Remove emojis, spam, and bot commands from text."""
    text = EMOJI_PATTERN.sub("", text)
    text = re.sub(r"\+1|^/\w+", "", text)  # Remove '+1' and bot commands
    text = re.sub(r"\s+", " ", text).strip()
    return text

def redact_pii(text: str) -> str:
    """Redact simple PII using regex."""
    return PII_PATTERN.sub("[REDACTED]", text)

def chunk_messages(messages: List[Dict[str, Any]], window: int = 5) -> List[Dict[str, Any]]:
    """Chunk messages by thread/user and time window."""
    if not messages:
        return []
    chunks = []
    current_chunk = []
    last_thread = messages[0].get("thread_id")
    last_user = messages[0].get("user_id")
    for msg in messages:
        if (msg.get("thread_id") != last_thread or msg.get("user_id") != last_user or len(current_chunk) >= window):
            if current_chunk:
                chunks.append({
                    "text": " ".join([m["content"] for m in current_chunk]),
                    "message_ids": [m["message_id"] for m in current_chunk],
                    "thread_id": last_thread if last_thread is not None else "",
                    "user_id": last_user if last_user is not None else "",
                    "channel_id": current_chunk[0]["channel_id"] if current_chunk[0]["channel_id"] is not None else ""
                })
            current_chunk = []
        current_chunk.append(msg)
        last_thread = msg.get("thread_id")
        last_user = msg.get("user_id")
    if current_chunk:
        chunks.append({
            "text": " ".join([m["content"] for m in current_chunk]),
            "message_ids": [m["message_id"] for m in current_chunk],
            "thread_id": last_thread if last_thread is not None else "",
            "user_id": last_user if last_user is not None else "",
            "channel_id": current_chunk[0]["channel_id"] if current_chunk[0]["channel_id"] is not None else ""
        })
    return chunks 

def split_text_for_embedding(text: str, max_length: int = 4000, overlap: int = 200) -> list:
    """Split text into chunks of at most max_length characters, with overlap."""
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + max_length, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_length:
            break
        start = end - overlap  # overlap for context
    return chunks 