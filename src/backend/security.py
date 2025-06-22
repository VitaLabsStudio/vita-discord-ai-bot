import os
from fastapi import Header, HTTPException, status, Depends
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BACKEND_API_KEY", "your_secret_api_key_here")

def get_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key."
        )
    return x_api_key 