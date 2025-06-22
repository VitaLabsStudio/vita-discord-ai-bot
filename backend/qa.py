from typing import List, Dict, Any
from .embedder import embed_chunks
from .vector_store import query_chunks
from .schemas import ChunkMetadata

# Stub for Deepseek R1 call
def deepseek_r1_qa(context: str, question: str, citations: List[str]) -> Dict[str, Any]:
    """Stub for Deepseek R1 QA call. Returns a dummy answer."""
    return {
        "answer": f"[Stub] Answer to: {question}",
        "citations": citations,
        "confidence": 0.9
    }

def answer_question(question: str, user_roles: List[str], channel_id: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Retrieve relevant chunks and generate an answer using Deepseek R1.
    Args:
        question: User's question.
        user_roles: Roles of the querying user.
        channel_id: Channel context.
        top_k: Number of chunks to retrieve.
    Returns:
        Dict with answer, citations, and confidence.
    """
    # Embed the question
    question_emb = embed_chunks([ChunkMetadata(
        chunk_id="q", message_ids=[], channel_id=channel_id, thread_id=None, roles=user_roles, timestamp="", original_text=question, cleaned_text=question
    )])[0]
    # Retrieve relevant chunks
    chunks = query_chunks(question_emb, top_k, user_roles, channel_id)
    context = "\n".join(c["cleaned_text"] for c in chunks)
    citations = [c["chunk_id"] for c in chunks]
    # Call Deepseek R1 (stub)
    return deepseek_r1_qa(context, question, citations) 