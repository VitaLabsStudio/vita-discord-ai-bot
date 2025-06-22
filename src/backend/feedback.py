# Feedback and error handling logic will be implemented here 

import os
import json
from typing import Dict, Any, List
from threading import Lock
from src.backend.logger import get_logger
import aiohttp
import asyncio
from dotenv import load_dotenv

FEEDBACK_LOG_PATH = "feedback_log.json"
DLQ_PATH = "dead_letter_queue.json"
_feedback_lock = Lock()
_dlq_lock = Lock()
FEEDBACK_LOG = "feedback.jsonl"
logger = get_logger(__name__)

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY", "your_secret_api_key_here")

def log_feedback(feedback: Dict[str, Any]) -> None:
    """Log user feedback (thumbs up/down, flags, etc)."""
    try:
        with open(FEEDBACK_LOG, "a") as f:
            f.write(json.dumps(feedback) + "\n")
        logger.info(f"Logged feedback: {feedback}")
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")

def log_to_dlq(item: Dict[str, Any]) -> None:
    """Log failed ingestion/embedding to dead-letter queue."""
    with _dlq_lock:
        queue = []
        if os.path.exists(DLQ_PATH):
            with open(DLQ_PATH, "r") as f:
                try:
                    queue = json.load(f)
                except Exception:
                    queue = []
        queue.append(item)
        with open(DLQ_PATH, "w") as f:
            json.dump(queue, f)

async def reprocess_dlq():
    with open("dlq.json", "r") as f:
        lines = f.readlines()
    async with aiohttp.ClientSession() as session:
        for line in lines:
            entry = json.loads(line)
            req = entry.get("original_request")
            if not req:
                continue
            if "messages" in req:
                endpoint = "/ingest_thread"
            else:
                endpoint = "/ingest"
            async with session.post(BACKEND_URL + endpoint, json=req, headers={"X-API-Key": BACKEND_API_KEY}) as resp:
                print(f"Reprocessed {endpoint}: {resp.status}")

if __name__ == "__main__":
    asyncio.run(reprocess_dlq()) 