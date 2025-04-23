from fastapi import APIRouter, UploadFile, File, Form
from app.models.schemas import ChatResponse
from app.services.chat_engine import handle_user_prompt
from app.services.image_processor import process_image

router = APIRouter()

# Simplified in-memory session (mock session state)
SESSION_STATE = {
    "chat_history": []
}

@router.post("/chat", response_model=ChatResponse)
async def chat(
    user_text: str = Form(...),
    image: UploadFile = File(None)
):
    """
    Handles chat interaction with the DiagnoAI assistant.

    This endpoint accepts user-submitted text and an optional image (e.g., an X-ray or medical scan).
    It appends the user's text to a shared session state and generates an AI response using a language model.
    If an image is provided, it processes the image (e.g., for medical classification) and returns analysis results.

    Args:
        user_text (str): User's message or symptom description, sent via a form.
        image (UploadFile, optional): An optional medical image file (JPG, PNG, etc.) for diagnostic analysis.

    Returns:
        ChatResponse: A JSON response containing the assistant's text reply and optional image analysis.
    """
    reply = ""
    image_info = None

    if user_text:
        SESSION_STATE["chat_history"].append({"role": "user", "content": user_text})
        reply = await handle_user_prompt(SESSION_STATE["chat_history"])
        SESSION_STATE["chat_history"].append({"role": "assistant", "content": reply})

    if image:
        image_info = await process_image(image)

    return ChatResponse(reply=reply, image_analysis=image_info)