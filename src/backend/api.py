# FastAPI backend logic will be implemented here 

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from src.backend.embedding import index, embed_chunks, store_embeddings, sanitize_metadata
from src.backend.llm_client import openai_client
from src.backend.permissions import filter_by_permissions
from src.backend.feedback import log_feedback, log_to_dlq
from dotenv import load_dotenv
from src.backend.utils import clean_text, redact_pii, chunk_messages, split_text_for_embedding
from src.backend.ingestion import is_processed, mark_processed, LOCKS_DIR
import aiohttp
from unstructured.partition.auto import partition
import io
import traceback
import pytesseract
from PIL import Image
import tempfile
import mimetypes
import json
import shutil
from src.backend.security import get_api_key
import pinecone
import openai
from src.backend.logger import get_logger
import spacy
from sentence_transformers import CrossEncoder
from src.backend import feedback as feedback_module
from fastapi.responses import JSONResponse
import datetime
from src.backend.file_processor import process_attachments

app = FastAPI(title="VITA Discord AI Knowledge Assistant Backend")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency check for tesseract and pdftotext
missing_deps = []
if shutil.which('tesseract') is None:
    missing_deps.append('tesseract')
if shutil.which('pdftotext') is None:
    missing_deps.append('pdftotext (poppler-utils)')
if missing_deps:
    print(f"[WARNING] Missing system dependencies: {', '.join(missing_deps)}. Some document or image ingestion may fail. Please install them and restart the backend.")

logger = get_logger(__name__)

class IngestRequest(BaseModel):
    message_id: str
    channel_id: str
    user_id: str
    content: str
    timestamp: str
    attachments: Optional[List[str]] = None
    thread_id: Optional[str] = None
    roles: Optional[List[str]] = None

class EmbedRequest(BaseModel):
    chunks: List[str]
    metadata: List[Dict[str, Any]]

class QueryRequest(BaseModel):
    user_id: str
    channel_id: str
    roles: List[str]
    question: str
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float

class FeedbackRequest(BaseModel):
    user_id: str
    query: str
    answer: str
    sources: list
    feedback: str

class ThreadIngestRequest(BaseModel):
    thread_id: str
    parent_message_id: Optional[str] = None
    messages: List[IngestRequest]

async def process_attachments(attachment_urls: List[str]) -> str:
    """Downloads, parses, and extracts text from file attachments. Supports more types and logs failures."""
    all_docs_text = []
    # Expanded supported types
    supported_mime_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.oasis.opendocument.text",
        "application/rtf",
        "text/html",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint"
    ]
    image_mime_types = ["image/jpeg", "image/png", "image/gif", "image/bmp", "image/tiff"]
    for url in attachment_urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        file_content = await resp.read()
                        file_name = url.split("/")[-1]
                        # Document types
                        if content_type in supported_mime_types:
                            try:
                                elements = partition(file=io.BytesIO(file_content), file_filename=file_name, content_type=content_type)
                                doc_text = "\n\n".join([str(el) for el in elements])
                                all_docs_text.append(f"\n\n--- Document Content: {file_name} ---\n\n{doc_text}")
                            except Exception as e:
                                log_to_dlq({"url": url, "file_name": file_name, "error": str(e), "type": "doc_parse"})
                                all_docs_text.append(f"\n\n--- Document Content: {file_name} ---\n\n[Failed to parse document: {e}]")
                        # Image types
                        elif content_type in image_mime_types:
                            try:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=file_name) as tmp:
                                    tmp.write(file_content)
                                    tmp.flush()
                                    img = Image.open(tmp.name)
                                    text = pytesseract.image_to_string(img)
                                    all_docs_text.append(f"\n\n--- Image OCR Content: {file_name} ---\n\n{text}")
                            except Exception as e:
                                log_to_dlq({"url": url, "file_name": file_name, "error": str(e), "type": "image_ocr"})
                                all_docs_text.append(f"\n\n--- Image OCR Content: {file_name} ---\n\n[Failed to OCR image: {e}]")
                        else:
                            # Unknown/unsupported type
                            log_to_dlq({"url": url, "file_name": file_name, "error": f"Unsupported content type: {content_type}", "type": "unsupported"})
                            all_docs_text.append(f"\n\n--- Attachment: {file_name} ---\n\n[Unsupported file type: {content_type}]")
                    else:
                        log_to_dlq({"url": url, "error": f"HTTP status {resp.status}", "type": "download"})
        except Exception as e:
            log_to_dlq({"url": url, "error": str(e), "type": "download_exception"})
            print(f"Failed to process attachment {url}: {e}")
    return "".join(all_docs_text)

async def run_ingestion_task(req: IngestRequest):
    try:
        lock_path = os.path.join(LOCKS_DIR, f"{req.message_id}.lock")
        if os.path.exists(lock_path):
            return
        with open(lock_path, "w") as f:
            f.write("")
        if is_processed(req.message_id):
            return
        
        # Process attachments
        attachment_text = ""
        if req.attachments:
            attachment_text = await process_attachments(req.attachments)

        # Clean and redact message content
        cleaned = clean_text(req.content)
        redacted = redact_pii(cleaned)
        
        # Combine message content with attachment text
        full_content = redacted + attachment_text
        
        if not full_content.strip():
            return

        # Extract NER entities and add to metadata
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(redacted)
        entities = [ent.text for ent in doc.ents if ent.label_ in ("PERSON", "ORG", "PRODUCT", "DATE")]
        
        # Split into chunks for embedding
        text_chunks = split_text_for_embedding(full_content, max_length=4000, overlap=200)
        metadatas = []
        for chunk_text in text_chunks:
            meta = {
                "message_id": req.message_id,
                "thread_id": req.thread_id if req.thread_id is not None else "",
                "user_id": req.user_id if req.user_id is not None else "",
                "channel_id": req.channel_id if req.channel_id is not None else "",
                "chunk_text": chunk_text,
                "roles": req.roles or [],
                "timestamp": req.timestamp,
                "entities": entities,
            }
            sanitized_meta = sanitize_metadata(meta)
            print(f"[DEBUG] Metadata before upsert: {sanitized_meta}")
            metadatas.append(sanitized_meta)
        try:
            embeddings = await embed_chunks(text_chunks)
            await store_embeddings(embeddings, metadatas)
            mark_processed(req.message_id)
            return
        except Exception as e:
            log_to_dlq({
                "message_id": req.message_id,
                "error": str(e),
                "content_preview": full_content[:200],
                "type": "embedding_or_storage",
                "metadata": metadatas
            })
    except Exception as e:
        log_to_dlq({
            "original_request": req.dict(),
            "error_message": str(e),
            "failed_at_step": "ingestion",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    finally:
        if os.path.exists(lock_path):
            os.remove(lock_path)

@app.post("/ingest", dependencies=[Depends(get_api_key)])
async def ingest_message(req: IngestRequest, background_tasks: BackgroundTasks):
    if is_processed(req.message_id):
        return {"status": "already_processed", "message_id": req.message_id}
    background_tasks.add_task(run_ingestion_task, req)
    return {"status": "accepted", "detail": "Ingestion task has been queued."}

@app.post("/embed")
async def embed_chunks_endpoint(request: EmbedRequest) -> Dict[str, str]:
    """Embed and store message/file chunks."""
    # TODO: Call embedding logic
    return {"status": "embedding started", "num_chunks": str(len(request.chunks))}

cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank_chunks(query: str, chunks: list) -> list:
    pairs = [(query, chunk['chunk_text']) for chunk in chunks]
    scores = cross_encoder.predict(pairs)
    reranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [c for c, s in reranked]

@app.post("/query", response_model=QueryResponse)
async def query_knowledge(req: QueryRequest) -> QueryResponse:
    """Query the knowledge base (RAG pipeline)."""
    # 1. Embed the question
    embed_resp = await openai_client.embeddings.create(
        input=[req.question],
        model="text-embedding-ada-002"
    )
    question_emb = embed_resp.data[0].embedding
    # 2. Query Pinecone for top-k
    pinecone_results = index.query(
        vector=question_emb,
        top_k=25,  # fetch more for permission filtering
        include_metadata=True
    )
    # 3. Filter by permissions
    chunks = [m.metadata | {"score": m.score} for m in pinecone_results.matches]
    filtered = filter_by_permissions(chunks, req.roles, req.channel_id)
    filtered = sorted(filtered, key=lambda x: -x.get("score", 0))[:25]
    # 4. Guard clause for empty context
    if not filtered:
        return QueryResponse(
            answer="I couldn't find any relevant information in the knowledge base to answer that. The bot learns from channel messages, so try asking about a topic that has been discussed recently.",
            citations=[],
            confidence=0.0
        )
    # 5. Compose context
    context_parts = []
    for c in filtered:
        text = c.get("chunk_text") or c.get("text")
        if text:
            context_parts.append(text)
    context = "\n".join(context_parts)
    
    # 6. Generate answer
    prompt = f"Answer the user's question using only the context below. Cite sources by message ID.\n\nContext:\n{context}\n\nQuestion: {req.question}\nAnswer:"
    completion = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=512,
        temperature=0.2
    )
    answer = completion.choices[0].message.content.strip()
    # 7. Prepare citations
    citations = [
        {
            "message_id": c.get("message_id"),
            "channel_id": c.get("channel_id"),
            "url": f"https://discord.com/channels/{{server_id}}/{c.get('channel_id')}/{c.get('message_id')}"
        }
        for c in filtered
    ]
    confidence = float(filtered[0]["score"]) if filtered else 0.0

    reranked = rerank_chunks(req.question, filtered)
    top_chunks = reranked[:5]

    return QueryResponse(answer=answer, citations=citations, confidence=confidence)

@app.post("/feedback", dependencies=[Depends(get_api_key)])
async def feedback_endpoint(req: FeedbackRequest) -> Dict[str, str]:
    try:
        feedback_module.log_feedback(req.dict())
        return {"status": "ok"}
    except Exception as e:
        logger.exception(f"Feedback logging error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/delete")
async def delete_message(req: Dict[str, Any]) -> Dict[str, str]:
    """Delete a user's message from the knowledge base."""
    message_id = req.get("message_id")
    user_id = req.get("user_id")
    if not message_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing message_id or user_id.")
    # Remove from Pinecone
    index.delete(ids=[message_id])
    return {"status": "deleted", "message_id": message_id}

@app.post("/redact")
async def redact_message(req: Dict[str, Any]) -> Dict[str, str]:
    """Redact a user's message in the knowledge base."""
    message_id = req.get("message_id")
    user_id = req.get("user_id")
    if not message_id or not user_id:
        raise HTTPException(status_code=400, detail="Missing message_id or user_id.")
    # Redact in Pinecone (replace text with [REDACTED])
    # Fetch, update, and upsert
    fetch = index.fetch(ids=[message_id])
    vectors = fetch.vectors
    if message_id in vectors:
        meta = vectors[message_id].metadata
        values = vectors[message_id].values
        meta["chunk_text"] = "[REDACTED]"
        index.upsert(vectors=[{"id": message_id, "values": values, "metadata": meta}])
        return {"status": "redacted", "message_id": message_id}
    else:
        raise HTTPException(status_code=404, detail="Message not found.")

class BatchIngestRequest(BaseModel):
    messages: List[IngestRequest]

async def run_batch_ingestion_task(req: BatchIngestRequest):
    # Move all batch ingestion logic here (process each message, call run_ingestion_task for each)
    for msg in req.messages:
        await run_ingestion_task(msg)

@app.post("/batch_ingest", dependencies=[Depends(get_api_key)])
async def batch_ingest_messages(req: BatchIngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_batch_ingestion_task, req)
    return {"status": "accepted", "detail": "Batch ingestion task has been queued."}

async def run_thread_ingestion_task(req: ThreadIngestRequest):
    try:
        lock_path = os.path.join(LOCKS_DIR, f"{req.thread_id}.lock")
        if os.path.exists(lock_path):
            return
        with open(lock_path, "w") as f:
            f.write("")
        # Combine all messages into a single document, preserving author and timestamp
        doc_lines = []
        for m in req.messages:
            author = m.user_id
            ts = m.timestamp
            content = m.content
            doc_lines.append(f"{author} ({ts}): {content}")
        full_content = "\n".join(doc_lines)
        # Clean, redact, and chunk as usual
        cleaned = clean_text(full_content)
        redacted = redact_pii(cleaned)
        doc = spacy.load("en_core_web_sm")
        entities = [ent.text for ent in doc.ents if ent.label_ in ("PERSON", "ORG", "PRODUCT", "DATE")]
        chunks = split_text_for_embedding(redacted)
        # Build metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            metadatas.append({
                "thread_id": req.thread_id,
                "parent_message_id": req.parent_message_id or "",
                "is_thread": True,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "entities": entities,
            })
        embeddings = await embed_chunks(chunks)
        await store_embeddings(embeddings, metadatas)
        return
    except Exception as e:
        log_to_dlq({
            "original_request": req.dict(),
            "error_message": str(e),
            "failed_at_step": "thread_ingestion",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    finally:
        if os.path.exists(lock_path):
            os.remove(lock_path)

@app.post("/ingest_thread", dependencies=[Depends(get_api_key)])
async def ingest_thread(req: ThreadIngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_thread_ingestion_task, req)
    return JSONResponse(status_code=202, content={"message": "Thread ingestion task has been accepted and is being processed in the background."})

@app.post("/summarize", dependencies=[Depends(get_api_key)])
async def summarize_thread(req: ThreadIngestRequest) -> Dict[str, str]:
    try:
        doc_lines = []
        for m in req.messages:
            author = m.user_id
            ts = m.timestamp
            content = m.content
            doc_lines.append(f"{author} ({ts}): {content}")
        full_content = "\n".join(doc_lines)
        # Use LLM to summarize
        from src.backend.llm_client import get_llm_summary
        summary = await get_llm_summary(full_content)
        return {"summary": summary}
    except Exception as e:
        logger.exception(f"Summarize error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/health")
async def health_check():
    try:
        # Try to get Pinecone index stats
        from pinecone import Index
        idx = Index(PINECONE_INDEX)
        _ = idx.describe_index_stats()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable.") 