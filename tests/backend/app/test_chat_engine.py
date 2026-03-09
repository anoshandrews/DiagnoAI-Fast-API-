import asyncio

from backend.app.models.schemas import ChatMessage
from backend.app.services import chat_engine


def test_handle_user_prompt_uses_llm(monkeypatch):
    history = [ChatMessage(role="user", content="I have a headache.")]

    def fake_generate_text(*, messages, temperature=0.2, model=None):
        del temperature, model
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "I have a headache."
        return "How long have you had the headache?"

    monkeypatch.setattr(chat_engine, "generate_text", fake_generate_text)

    reply = asyncio.run(chat_engine.handle_user_prompt(history))
    assert reply == "How long have you had the headache?"


def test_handle_user_prompt_falls_back_without_llm(monkeypatch):
    history = [ChatMessage(role="user", content="I feel dizzy.")]

    def raise_error(*, messages, temperature=0.2, model=None):
        del messages, temperature, model
        raise chat_engine.LLMClientError("missing key")

    monkeypatch.setattr(chat_engine, "generate_text", raise_error)

    reply = asyncio.run(chat_engine.handle_user_prompt(history))
    assert "When did these symptoms start" in reply
