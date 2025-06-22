# VITA Discord AI Knowledge Assistant

## Setup

1. **Python 3.10+ required**
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env` and fill in your API keys.

## Running

- Start the FastAPI backend:
  ```bash
  uvicorn src.backend.api:app --reload
  ```
- Start the Discord bot:
  ```bash
  python src/bot/discord_bot.py
  ```

## Environment Variables (.env)
- DISCORD_TOKEN
- PINECONE_API_KEY
- OPENAI_API_KEY
- (Optional) ASSEMBLYAI_API_KEY

## Project Structure
- `src/bot/discord_bot.py`: Discord bot logic
- `src/backend/api.py`: FastAPI backend
- `src/backend/ingestion.py`: Ingestion logic
- `src/backend/embedding.py`: Embedding logic
- `src/backend/permissions.py`: Permission handling
- `src/backend/decay.py`: Knowledge decay/maintenance
- `src/backend/feedback.py`: Feedback and error handling
- `src/backend/utils.py`: Utilities
- `main.py`: Entrypoint (optional) 