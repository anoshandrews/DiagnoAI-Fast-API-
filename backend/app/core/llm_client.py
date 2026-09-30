import json
import logging
from typing import Any

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Raised when the configured LLM provider cannot be used."""


def _build_groq_client():
    settings = get_settings()
    if not settings.groq_api_key or settings.groq_api_key in ("replace-me", "your_groq_api_key_here", "test_key", ""):
        raise LLMClientError("GROQ_API_KEY is not configured or using placeholder.")

    try:
        from groq import Groq
    except ModuleNotFoundError as exc:
        raise LLMClientError("groq package is not installed.") from exc

    return Groq(api_key=settings.groq_api_key)



def generate_text(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    settings = get_settings()
    client = _build_groq_client()
    try:
        response = client.chat.completions.create(
            model=model or settings.groq_model_name,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("LLM returned an empty response.")
        return content
    except Exception as exc:
        if isinstance(exc, LLMClientError):
            raise
        raise LLMClientError(f"Groq API error: {exc}") from exc


def transcribe_audio(
    file_bytes: bytes,
    filename: str = "audio.wav",
    model: str | None = None,
) -> str:
    """
    Transcribes user audio using Groq Whisper (whisper-large-v3-turbo).
    Ultra-low latency transcription with zero local PyTorch dependencies.
    """
    settings = get_settings()
    client = _build_groq_client()
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, file_bytes),
            model=model or settings.groq_whisper_model,
            response_format="text",
        )
        if isinstance(transcription, str):
            return transcription.strip()
        return getattr(transcription, "text", str(transcription)).strip()
    except Exception as exc:
        raise LLMClientError(f"Groq Whisper transcription failed: {exc}") from exc


def parse_json_response(payload: str) -> dict[str, Any]:
    cleaned = payload.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned.strip())
