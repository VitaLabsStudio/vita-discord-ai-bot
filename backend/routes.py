from fastapi import APIRouter, Body
from .schemas import DiscordMessage
from .ingest import ingest_message
from .batch_ingest import batch_ingest
from typing import List
from .qa import answer_question
from .decay import archive_old_chunks, remove_chunk_by_message_id, feedback_chunk

router = APIRouter()

@router.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}

@router.post("/ingest")
def ingest(msg: DiscordMessage) -> dict:
    """Ingest a Discord message if not already processed."""
    result = ingest_message(msg.dict())
    return {"ingested": result}

@router.post("/batch_ingest")
def batch_ingest_endpoint(msgs: List[DiscordMessage]) -> dict:
    """Batch ingest historical Discord messages."""
    count = batch_ingest([m.dict() for m in msgs])
    return {"ingested_count": count}

@router.post("/ask")
def ask_endpoint(
    question: str = Body(...),
    user_roles: List[str] = Body(...),
    channel_id: str = Body(...),
    top_k: int = Body(5)
) -> dict:
    """Answer a user question using the QA pipeline (RAG)."""
    return answer_question(question, user_roles, channel_id, top_k)

@router.post("/archive")
def archive_endpoint() -> dict:
    """Archive or summarize old chunks."""
    count = archive_old_chunks()
    return {"archived": count}

@router.post("/delete")
def delete_endpoint(msg_id: str = Body(...)) -> dict:
    """Delete a user's message and its chunk."""
    removed = remove_chunk_by_message_id(msg_id)
    return {"removed": removed}

@router.post("/feedback")
def feedback_endpoint(chunk_id: str = Body(...), feedback: str = Body(...)) -> dict:
    """Record feedback for a chunk."""
    feedback_chunk(chunk_id, feedback)
    return {"status": "ok"} 