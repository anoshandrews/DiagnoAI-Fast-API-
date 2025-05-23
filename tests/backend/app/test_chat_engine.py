import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.chat_engine import handle_user_prompt

@pytest.mark.asyncio
async def test_handle_user_prompt_success():
    chat_history = [{"role": "user", "content": "I have a headache and fever."}]
    expected_reply = "Can you tell me how long you've had the headache?"

    # Patch the Groq client used inside the chat_engine module
    with patch("app.services.chat_engine.groq_client") as mock_client:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = expected_reply
        mock_client.chat.completions.create.return_value = mock_response

        result = await handle_user_prompt(chat_history)
        assert result == expected_reply

@pytest.mark.asyncio
async def test_handle_user_prompt_failure():
    chat_history = [{"role": "user", "content": "I have chest pain."}]

    with patch("app.services.chat_engine.groq_client") as mock_client:
        mock_client.chat.completions.create.side_effect = Exception("LLM error")

        with pytest.raises(Exception, match="LLM error"):
            await handle_user_prompt(chat_history)