import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from src.backend.logger import get_logger

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
logger = get_logger(__name__)

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

print(f"DEBUG: OpenAI API key configured: {OPENAI_API_KEY[:10]}...")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) 