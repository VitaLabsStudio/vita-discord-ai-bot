import logging
from typing import Any

logging.basicConfig(filename="monitor.log", level=logging.INFO)

BUDGET_LIMIT = 100.0  # Example budget in USD
usage = 0.0

def log_api_usage(cost: float) -> None:
    """Log API usage and check against budget."""
    global usage
    usage += cost
    logging.info(f"API usage: ${usage:.2f}")
    if usage > BUDGET_LIMIT:
        logging.warning("Budget limit exceeded!")

def log_failure(event: str, details: Any) -> None:
    """Log a failure event to the monitor log."""
    logging.error(f"Failure: {event} | Details: {details}") 