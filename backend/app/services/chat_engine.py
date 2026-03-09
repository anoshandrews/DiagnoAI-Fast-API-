from backend.app.core.llm_client import LLMClientError, generate_text
from backend.app.core.logging import logger
from backend.app.models.schemas import ChatMessage

SYSTEM_PROMPT = """You are DiagnoAI, an intake assistant for symptom collection.
Ask one focused follow-up question at a time.
Collect symptom details that help a clinician: onset, duration, severity, location,
relevant medical history, medications, and red-flag symptoms.
Do not diagnose, speculate about conditions, or recommend treatment.
If the user describes an emergency sign, tell them to seek urgent medical attention.
When enough information is gathered, say that the report is ready for clinician review."""


def _fallback_question(chat_history: list[ChatMessage]) -> str:
    if not chat_history:
        return "What symptoms are you experiencing today?"
    if len(chat_history) == 1:
        return "When did these symptoms start, and how severe are they right now?"
    return "What is the most important symptom detail you have not mentioned yet, such as duration, severity, or triggers?"


async def handle_user_prompt(chat_history: list[ChatMessage]) -> str:
    logger.info("Processing chat turn with %s prior messages.", len(chat_history))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(message.model_dump() for message in chat_history)
    try:
        return generate_text(messages=messages)
    except LLMClientError:
        logger.warning("LLM provider unavailable; using fallback prompt.")
        return _fallback_question(chat_history)
