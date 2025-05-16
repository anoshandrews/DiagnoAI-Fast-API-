"""
Data schemas for request and response models.

These schemas define the shape of data used in API communication.
"""

from pydantic import BaseModel
from typing import Optional

class ChatResponse(BaseModel):
    reply: str
    image_analysis: Optional[str] = None