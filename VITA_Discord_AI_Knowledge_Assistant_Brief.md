# VITA Discord AI Knowledge Assistant — Step-by-Step Build Plan (2025, Current Version)

---

## 1. PROJECT INITIALIZATION

1. **Create a new Python project with a virtual environment.**

2. **Install these dependencies in `requirements.txt`:**

   ```
   discord.py
   fastapi
   uvicorn
   openai
   pinecone
   python-dotenv
   sentence-transformers
   unstructured
   spaCy
   pytesseract
   Pillow
   # (plus all sub-dependencies for unstructured: poppler, tesseract, etc.)
   ```

   *(Add AssemblyAI or Whisper if you plan to implement voice in Phase 2)*

3. **Set up your `.env` file** with:

   * DISCORD_TOKEN
   * PINECONE_API_KEY (or Qdrant details)
   * OPENAI_API_KEY (for embeddings)
   * (optional) ASSEMBLYAI_API_KEY

---

## 2. DISCORD BOT & BACKEND SETUP

1. **Initialize a Discord bot with `discord.py`.**
2. **Set up a FastAPI backend to handle ingestion, embedding, and query endpoints.**
3. **Connect the Discord bot to the FastAPI backend via async HTTP calls.**
4. **Grant the bot permissions to read all messages, files, and thread data.**
5. **Use a persistent aiohttp.ClientSession in the bot for efficient HTTP.**

---

## 3. EVENT-DRIVEN, IDEMPOTENT INGESTION

1. **On each new message or file event:**

   * Check message/file ID against a local "processed" database or log.
   * Only process if not already handled.
   * For each file: auto-download and store temporarily.

2. **Batch ingest historical data (cold start):**

   * Use cursor pagination to fetch and process old messages in all channels/threads.
   * `/ingest_history` command triggers batch ingestion via the backend.

---

## 4. PREPROCESSING & DATA CLEANING

1. **For every message, file, or thread:**

   * Use `spaCy` + regex for fast noise removal (emojis, spam, "+1", bot commands, etc).
   * Detect and redact PII using regex; only invoke LLM if complex entity recognition is needed.
   * Chunk messages by thread and by time window (e.g., group 5–10 messages from the same thread/user or 10-minute windows).
   * Store original message/thread IDs, channel, and roles as metadata for each chunk.
   * **All metadata fields (including thread_id) are always strings (never None/null).**

---

## 5. ATTACHMENT & DOCUMENT INGESTION

1. **Support for all major document and image types:**

   * PDF, DOCX, TXT, CSV, PPTX, XLSX, ODT, RTF, HTML, DOC, XLS, PPT, etc.
   * Images (JPEG, PNG, GIF, BMP, TIFF) are OCR'd using pytesseract + Pillow.
   * All other file types are logged as unsupported, with a placeholder in Pinecone.

2. **All failures (unsupported types, download errors, parsing/OCR errors) are logged to a dead letter queue (`dead_letter_queue.json`).**

---

## 6. EMBEDDING & STORAGE

1. **Batch all new message/file chunks for embeddings** (collect up to 100 before embedding if possible).
2. **Generate embeddings using `text-embedding-ada-002` (1536-dim) from OpenAI** (or `BAAI/bge` if self-hosted).
3. **Split large messages/documents into 4000-character chunks (with overlap) to avoid context length errors.**
4. **Store each chunk and its metadata in Pinecone:**

   * Include: embedding, chunk text, message/thread ID, channel, allowed roles, timestamp.
   * **All metadata is sanitized to ensure Pinecone compatibility (no None/null values).**

---

## 7. PERMISSION HANDLING

1. **At ingestion:**

   * Tag each chunk with the allowed channel(s) and role(s) from Discord at time of posting.
2. **At retrieval:**

   * Only retrieve and return chunks where the querying user has the necessary role/channel access.

---

## 8. KNOWLEDGE DECAY & MAINTENANCE

1. **Schedule daily/weekly jobs to:**

   * Archive or auto-summarize chunks that are old, rarely accessed, or have low "freshness" (based on time, feedback, or engagement).
   * Clean up deleted/edited messages—remove or update corresponding chunks.
2. **Implement simple `/delete` or `/redact` commands** for users to remove their own data.
3. **Add feedback loop:** Users can "👍/👎" bot answers or flag as outdated to affect chunk freshness.

---

## 9. QUERY & QA PIPELINE (RAG)

1. **On `/ask` command in Discord:**

   * Backend receives user question and user/channel/role info.
   * Retrieve top-k relevant chunks from vector DB, filtered by permissions.
   * Use LLM (e.g., Deepseek R1 or OpenAI) to generate answer, passing:
     * Retrieved context
     * Citations to original messages/files
     * Instructions to cite sources and only use permitted info.
   * Bot posts answer with citations, confidence score, and feedback options.

---

## 10. FAILURE HANDLING & COST CONTROLS

1. **Log all ingestion or embedding failures to a dead-letter queue (`dead_letter_queue.json`).**
2. **Create a reprocessing script to retry failed jobs regularly (`reprocess_dlq` in `feedback.py`).**
3. **Monitor API usage for embeddings and LLMs; set up basic budget alarms.**
4. **(Optional) Add a fallback to a cheaper LLM if Deepseek R1/API limit is hit.**

---

## 11. PHASE 2+ (ADVANCED/OPTIONAL)

1. **Voice/meeting processing:**

   * Only process explicitly joined meetings (not always-on).
   * Batch audio-to-text and store with minimal speaker attribution.
2. **Split voice/file processing into separate modules or services if load increases.**
3. **Implement content moderation layer if needed for public-facing bots.**
4. **Scale architecture by introducing microservices or queues only if you reach high user/load thresholds.**

---

## 12. SUMMARY CHECKLIST

* [ ] Set up Discord bot and FastAPI backend.
* [ ] Implement event-driven, idempotent ingestion with batch processing for history.
* [ ] Use spaCy/regex for fast cleaning and PII redaction (LLM only if necessary).
* [ ] Batch embeddings with OpenAI or other specialized model.
* [ ] Store chunks with message/thread/channel/role metadata (all as strings).
* [ ] Permission filtering at both ingestion and retrieval.
* [ ] Schedule regular archival/decay/compaction jobs.
* [ ] Feedback, error handling, and basic cost monitoring.
* [ ] Voice/meeting and other advanced features deferred to Phase 2.
* [ ] All ingestion failures are logged and can be reprocessed from the DLQ.
* [ ] All document/image types are supported; unsupported types are logged and skipped gracefully.

---

### INSTRUCTIONS TO CURSOR

* Build each section in order.
* Use Python 3.10+ and type hints throughout.
* Document every function and endpoint.
* Prioritize speed, idempotency, and cost-efficiency.
* Use batched and event-driven operations wherever possible.
* Test ingestion, query, and decay logic with dummy Discord data before going live.
* **Always sanitize metadata before upserting to Pinecone.**
* **Log all failures to the dead letter queue for later reprocessing.**

---

**Paste this directly into Cursor to bootstrap your build. If you want, ask me for sample starter code, endpoint specs, or more detailed module breakdowns!** 