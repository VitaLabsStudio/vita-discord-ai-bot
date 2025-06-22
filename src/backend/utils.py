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