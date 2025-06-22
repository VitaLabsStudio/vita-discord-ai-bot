import logging
import os
from dotenv import load_dotenv

load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_logger(name: str):
    return logging.getLogger(name) 