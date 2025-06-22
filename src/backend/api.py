# FastAPI backend logic will be implemented here 

from fastapi import FastAPI, HTTPException, Request
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
from src.backend.ingestion import is_processed, mark_processed
import aiohttp
from unstructured.partition.auto import partition
import io
import traceback
import pytesseract
from PIL import Image
import tempfile
import mimetypes
import json

app = FastAPI(title="VITA Discord AI Knowledge Assistant Backend")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    message_id: str
    feedback: str  # 'up', 'down', 'flag', etc.
    comment: Optional[str] = None

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

@app.post("/ingest")
async def ingest_message(req: IngestRequest) -> Dict[str, str]:
    """Ingest a new Discord message or file."""
    if is_processed(req.message_id):
        return {"status": "already_processed", "message_id": req.message_id}
    
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
        return {"status": "skipped_empty", "message_id": req.message_id}

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
            "timestamp": req.timestamp
        }
        sanitized_meta = sanitize_metadata(meta)
        print(f"[DEBUG] Metadata before upsert: {sanitized_meta}")
        metadatas.append(sanitized_meta)
    try:
        embeddings = await embed_chunks(text_chunks)
        await store_embeddings(embeddings, metadatas)
        mark_processed(req.message_id)
        return {"status": "ingested", "message_id": req.message_id}
    except Exception as e:
        log_to_dlq({
            "message_id": req.message_id,
            "error": str(e),
            "content_preview": full_content[:200],
            "type": "embedding_or_storage",
            "metadata": metadatas
        })
        return {"status": "error", "message_id": req.message_id, "error": str(e)}

@app.post("/embed")
async def embed_chunks_endpoint(request: EmbedRequest) -> Dict[str, str]:
    """Embed and store message/file chunks."""
    # TODO: Call embedding logic
    return {"status": "embedding started", "num_chunks": str(len(request.chunks))}

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
        top_k=req.top_k * 2,  # fetch more for permission filtering
        include_metadata=True
    )
    # 3. Filter by permissions
    chunks = [m.metadata | {"score": m.score} for m in pinecone_results.matches]
    filtered = filter_by_permissions(chunks, req.roles, req.channel_id)
    filtered = sorted(filtered, key=lambda x: -x.get("score", 0))[:req.top_k]
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
    return QueryResponse(answer=answer, citations=citations, confidence=confidence)

@app.post("/feedback")
async def feedback(req: FeedbackRequest) -> Dict[str, str]:
    """Log user feedback on answers."""
    log_feedback(req.dict())
    return {"status": "logged"}

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

@app.post("/batch_ingest")
async def batch_ingest_messages(req: BatchIngestRequest) -> Dict[str, Any]:
    """Ingests a batch of historical messages."""
    processed_count = 0
    failed_count = 0
    failed_messages = []
    already_processed_count = 0

    for msg in req.messages:
        if is_processed(msg.message_id):
            already_processed_count += 1
            continue
        try:
            # Process attachments for each message
            attachment_text = ""
            if msg.attachments:
                attachment_text = await process_attachments(msg.attachments)
            cleaned = clean_text(msg.content)
            redacted = redact_pii(cleaned)
            full_content = redacted + attachment_text
            if not full_content.strip():
                continue
            # Split into chunks for embedding
            text_chunks = split_text_for_embedding(full_content, max_length=4000, overlap=200)
            all_metadatas = []
            for chunk_text in text_chunks:
                meta = {
                    "message_id": msg.message_id,
                    "thread_id": msg.thread_id if msg.thread_id is not None else "",
                    "user_id": msg.user_id if msg.user_id is not None else "",
                    "channel_id": msg.channel_id if msg.channel_id is not None else "",
                    "chunk_text": chunk_text,
                    "roles": msg.roles or [],
                    "timestamp": msg.timestamp
                }
                sanitized_meta = sanitize_metadata(meta)
                print(f"[DEBUG] Metadata before upsert: {sanitized_meta}")
                all_metadatas.append(sanitized_meta)
            try:
                embeddings = await embed_chunks(text_chunks)
                await store_embeddings(embeddings, all_metadatas)
                mark_processed(msg.message_id)
                processed_count += 1
            except Exception as embed_error:
                failed_count += 1
                log_to_dlq({
                    "message_id": msg.message_id,
                    "error": str(embed_error),
                    "content_preview": full_content[:200],
                    "type": "embedding_or_storage",
                    "metadata": all_metadatas
                })
                failed_messages.append({"message_id": msg.message_id, "error": str(embed_error)})
        except Exception as e:
            failed_count += 1
            log_to_dlq({
                "message_id": msg.message_id,
                "error": str(e),
                "content_preview": msg.content[:200],
                "type": "ingest_exception"
            })
            failed_messages.append({"message_id": msg.message_id, "error": str(e)})

    return {
        "status": "completed",
        "processed": processed_count,
        "failed": failed_count,
        "already_processed": already_processed_count,
        "failed_messages": failed_messages
    } 