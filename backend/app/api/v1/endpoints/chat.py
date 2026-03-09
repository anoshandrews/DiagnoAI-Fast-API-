from fastapi import APIRouter, HTTPException, Request

from backend.app.models.schemas import ChatMessage, ChatRequest, ChatResponse
from backend.app.services.chat_engine import handle_user_prompt
from backend.app.services.session_store import session_store

router = APIRouter()


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
                "session_id": form.get("session_id"),
            }
        )

    if not payload.user_text.strip():
        raise HTTPException(status_code=422, detail="user_text cannot be empty.")

    history = session_store.append(
        payload.session_id,
        ChatMessage(role="user", content=payload.user_text.strip()),
    )
    reply = await handle_user_prompt(history)
    history = session_store.append(
        payload.session_id,
        ChatMessage(role="assistant", content=reply),
    )
    return ChatResponse(session_id=payload.session_id, reply=reply, chat_history=history)
