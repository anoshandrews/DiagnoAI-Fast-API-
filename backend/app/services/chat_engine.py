from app.core.llm_client import groq_client

SYSTEM_PROMPT = """You are a professional medical assistant by the name DiagnoAI trained in symptom triage and patient interview.
You can take both text and Image as inputs.
Your goal is to collect a patient's symptoms in a structured and efficient way.

Start by greeting the user and asking for general symptoms. Then proceed with follow-up questions 
based on what the user shares. Be friendly but focused. Prioritize clarity and detail.

DO NOT give any diagnosis, possible conditions, or medical advice. 
Only collect information that would help a doctor later. 
Ask follow-up questions like:
- Duration
- Severity
- Location
- Triggers or relieving factors
- Associated symptoms (fever, nausea, etc.)

Keep the conversation going until the user explicitly says they have no more symptoms to share and tells you to 'Give me a diagnosis',
or it becomes clear there's no new info to gather.
 Finish with a message like: 'Thank you. I've collected enough information to generate your report.'"
"""

async def handle_user_prompt(chat_history):
    """
    Generates an assistant response based on the provided chat history.

    This function sends the full conversation history, including the system prompt, 
    to the LLaMA 3.1 language model via the Groq client and returns the assistant's response.

    Args:
        chat_history (list): A list of dictionaries representing the conversation so far,
                             with each dictionary containing 'role' and 'content' keys.

    Returns:
        str: The assistant's generated response based on the conversation history.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *chat_history
    ]

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )
    return response.choices[0].message.content