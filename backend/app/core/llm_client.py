import json
from typing import Any

from backend.app.core.config import get_settings


class LLMClientError(RuntimeError):
    """Raised when the configured LLM provider cannot be used."""


def _build_groq_client():
    settings = get_settings()
    if not settings.groq_api_key:
        raise LLMClientError("GROQ_API_KEY is not configured.")

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
    response = client.chat.completions.create(
        model=model or settings.groq_model_name,
        messages=messages,
        temperature=temperature,
    )
    content = response.choices[0].message.content
    if not content:
        raise LLMClientError("LLM returned an empty response.")
    return content


def parse_json_response(payload: str) -> dict[str, Any]:
    cleaned = payload.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned)
