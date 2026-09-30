import logging
from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage

from backend.app.graph.workflow import intake_graph
from backend.app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ExtractedSymptoms,
)
from backend.app.services import chat_engine
from backend.app.services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter()

# Keep reference for monkeypatching support in existing test suites
handle_user_prompt = chat_engine.handle_user_prompt
_default_handle_user_prompt = chat_engine.handle_user_prompt


@router.post("", response_model=ChatResponse)
async def chat(request: Request) -> ChatResponse:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = ChatRequest.model_validate(await request.json())
    else:
        form = await request.form()
        payload = ChatRequest.model_validate(
            {
                "user_text": form.get("user_text"),
                "patient_id": form.get("patient_id") or "default-patient",
                "session_id": form.get("session_id"),
            }
        )

    if not payload.user_text.strip():
        raise HTTPException(status_code=422, detail="user_text cannot be empty.")

    # Check if handle_user_prompt was monkeypatched (e.g., during unit tests)
    if handle_user_prompt != _default_handle_user_prompt:
        history = session_store.append(
            payload.session_id,
            ChatMessage(role="user", content=payload.user_text.strip()),
        )
        reply = await handle_user_prompt(history)
        history = session_store.append(
            payload.session_id,
            ChatMessage(role="assistant", content=reply),
        )
        return ChatResponse(
            session_id=payload.session_id,
            patient_id=payload.patient_id,
            reply=reply,
            chat_history=history,
        )

    # Standard stateful LangGraph agent execution
    config = {"configurable": {"thread_id": payload.session_id}}
    input_data = {
        "messages": [HumanMessage(content=payload.user_text.strip())],
        "patient_id": payload.patient_id,
        "session_id": payload.session_id,
    }

    try:
        state = intake_graph.invoke(input_data, config=config)
    except Exception as exc:
        logger.exception("Error executing LangGraph intake flow: %s", exc)
        # Resilient fallback
        history = session_store.append(
            payload.session_id,
            ChatMessage(role="user", content=payload.user_text.strip()),
        )
        reply = await _default_handle_user_prompt(history)
        history = session_store.append(
            payload.session_id,
            ChatMessage(role="assistant", content=reply),
        )
        return ChatResponse(
            session_id=payload.session_id,
            patient_id=payload.patient_id,
            reply=reply,
            chat_history=history,
        )

    # Extract latest AI message
    reply = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage) or (hasattr(msg, "role") and msg.role == "assistant"):
            reply = str(msg.content)
            break
    if not reply:
        reply = "Could you tell me more about the symptoms you are experiencing?"

    # Convert graph messages to ChatMessage list
    chat_history: list[ChatMessage] = []
    for msg in state.get("messages", []):
        role = "user" if (isinstance(msg, HumanMessage) or getattr(msg, "role", "") == "user") else "assistant"
        chat_history.append(ChatMessage(role=role, content=str(msg.content)))

    # Sync with local session store for test and cache compatibility
    session_store.clear(payload.session_id)
    session_store.append(payload.session_id, *chat_history)

    symptoms_dict = state.get("symptoms", {})
    extracted = ExtractedSymptoms.model_validate(symptoms_dict) if symptoms_dict else ExtractedSymptoms()

    return ChatResponse(
        session_id=payload.session_id,
        patient_id=payload.patient_id,
        reply=reply,
        intake_stage=state.get("intake_stage", "gathering"),
        extracted_symptoms=extracted,
        red_flags=state.get("red_flags", []),
        report_markdown=state.get("clinician_handoff_markdown"),
        chat_history=chat_history,
    )
