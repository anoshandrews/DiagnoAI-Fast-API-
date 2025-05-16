"""
LLM Client Setup.

This module initializes and manages the client for connecting to
external language model APIs (e.g., Groq or OpenAI), used for natural
language processing and AI chat functionalities.
"""

from groq import Groq
from app.core.config import GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY)