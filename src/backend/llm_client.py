import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

print(f"DEBUG: OpenAI API key configured: {OPENAI_API_KEY[:10]}...")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) 