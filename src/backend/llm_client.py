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

async def get_llm_summary(text: str) -> str:
    """Generate a summary of the given text using the LLM."""
    try:
        prompt = f"Summarize the following conversation in a concise, clear paragraph:\n\n{text}"
        response = await openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM summary error: {e}")
        return "Summary could not be generated." 