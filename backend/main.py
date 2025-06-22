from fastapi import FastAPI
from .routes import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def read_root() -> dict:
    """Root endpoint for health check."""
    return {"status": "Backend is running"} 