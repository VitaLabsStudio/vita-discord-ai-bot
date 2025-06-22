from pydantic import BaseModel
from typing import List, Optional

class DiscordMessage(BaseModel):
    id: str
    content: str
    author_id: str
    channel_id: str
    thread_id: Optional[str]
    timestamp: str
    attachments: Optional[List[str]] = None
    roles: Optional[List[str]] = None

class ChunkMetadata(BaseModel):
    chunk_id: str
    message_ids: List[str]
    channel_id: str
    thread_id: Optional[str]
    roles: List[str]
    timestamp: str
    original_text: str
    cleaned_text: Optional[str] = None 