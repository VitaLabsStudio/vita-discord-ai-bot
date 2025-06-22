import pytest
from src.backend.api import filter_by_permissions

def test_filter_by_permissions():
    chunks = [
        {"chunk_text": "A", "roles": ["admin", "user"]},
        {"chunk_text": "B", "roles": ["user"]},
        {"chunk_text": "C", "roles": ["guest"]},
    ]
    allowed = filter_by_permissions(chunks, ["user"], None)
    assert len(allowed) == 2
    assert all("user" in c["roles"] for c in allowed)
