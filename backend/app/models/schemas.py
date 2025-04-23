from pydantic import BaseModel
from typing import Optional

class ChatResponse(BaseModel):
    reply: str
    image_analysis: Optional[str] = None