import json
from typing import Dict, Any, List
from pathlib import Path

DLQ_PATH = Path("dead_letter.json")

def log_dead_letter(event: Dict[str, Any]) -> None:
    """Log a failed event to the dead-letter queue."""
    if DLQ_PATH.exists():
        with open(DLQ_PATH, "r") as f:
            data = json.load(f)
    else:
        data = []
    data.append(event)
    with open(DLQ_PATH, "w") as f:
        json.dump(data, f)

def reprocess_dead_letters(process_func) -> int:
    """Attempt to reprocess all dead-letter events using the provided function."""
    if not DLQ_PATH.exists():
        return 0
    with open(DLQ_PATH, "r") as f:
        data = json.load(f)
    success = 0
    remaining = []
    for event in data:
        try:
            if process_func(event):
                success += 1
            else:
                remaining.append(event)
        except Exception:
            remaining.append(event)
    with open(DLQ_PATH, "w") as f:
        json.dump(remaining, f)
    return success 