# Feedback and error handling logic will be implemented here 

import os
import json
from typing import Dict, Any, List
from threading import Lock
from src.backend.logger import get_logger

FEEDBACK_LOG_PATH = "feedback_log.json"
DLQ_PATH = "dead_letter_queue.json"
_feedback_lock = Lock()
_dlq_lock = Lock()
FEEDBACK_LOG = "feedback.jsonl"
logger = get_logger(__name__)

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

def reprocess_dlq() -> List[Dict[str, Any]]:
    """Attempt to reprocess items in the dead-letter queue."""
    with _dlq_lock:
        if not os.path.exists(DLQ_PATH):
            return []
        with open(DLQ_PATH, "r") as f:
            try:
                queue = json.load(f)
            except Exception:
                return []
        # TODO: Implement reprocessing logic
        # For now, just clear the queue
        with open(DLQ_PATH, "w") as f:
            json.dump([], f)
        return queue 