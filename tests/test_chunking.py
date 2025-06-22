import pytest
from src.backend.utils import split_text_for_embedding

def test_split_text_for_embedding():
    text = "A" * 9500
    chunks = split_text_for_embedding(text, max_length=4000, overlap=200)
    assert len(chunks) == 3
    assert all(len(chunk) <= 4000 for chunk in chunks)
    assert chunks[0][-200:] == chunks[1][:200]
    assert chunks[1][-200:] == chunks[2][:200]
