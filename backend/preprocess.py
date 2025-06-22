"""
Preprocessing and data cleaning for Discord messages and files.
"""
import re
import spacy
from typing import Tuple

nlp = spacy.blank("en")  # Use blank model for fast tokenization

EMOJI_PATTERN = re.compile(r":[a-zA-Z0-9_]+:|[\U00010000-\U0010ffff]")
PII_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+|\b\d{3}[-.]?\d{2}[-.]?\d{4}\b")


def clean_message(text: str) -> Tuple[str, bool]:
    """
    Clean a message using spaCy and regex. Redact PII and remove noise.
    Args:
        text: The original message text.
    Returns:
        Tuple of (cleaned_text, pii_found)
    """
    # Remove emojis and noise
    text = EMOJI_PATTERN.sub("", text)
    text = re.sub(r"\b(\+1|thanks|thank you|/\w+)\b", "", text, flags=re.I)
    # Redact PII
    pii_found = bool(PII_PATTERN.search(text))
    text = PII_PATTERN.sub("[REDACTED]", text)
    # Tokenize and remove extra whitespace
    doc = nlp(text)
    cleaned = " ".join([t.text for t in doc]).strip()
    return cleaned, pii_found 