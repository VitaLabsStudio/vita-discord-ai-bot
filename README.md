# VITA Discord AI Knowledge Assistant

## Setup

1. **Clone the repository**
2. **Create and activate a virtual environment**
3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
4. **Copy `.env.example` to `.env` and fill in all required values**
5. **Run the application**
   ```sh
   python src/main.py
   ```

## Features
- Discord bot and FastAPI backend run together from a single command
- All configuration is centralized in `.env`
- API is secured with an API key (set `BACKEND_API_KEY` in `.env`)
- Structured logging with configurable log level
- Robust error handling and user-friendly Discord bot responses

## Security
- The backend requires an `X-API-Key` header for all requests
- The Discord bot is configured to use this key for all backend calls

## Logging
- Log level is set via `LOG_LEVEL` in `.env`
- Logs are structured and include timestamps, levels, and module names

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