import logging
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.core.config import get_settings
from backend.app.core.llm_client import LLMClientError, transcribe_audio
from backend.app.models.schemas import TranscriptionResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_speech(
    file: UploadFile = File(...),
) -> TranscriptionResponse:
    """
    Transcribes patient audio recording using Groq's high-speed Whisper Large v3 Turbo.
    Zero local machine learning dependencies; lightweight and fast.
    """
    settings = get_settings()
    filename = file.filename or "recording.wav"

    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        text = transcribe_audio(
            file_bytes=audio_bytes,
            filename=filename,
            model=settings.groq_whisper_model,
        )

        return TranscriptionResponse(text=text, model=settings.groq_whisper_model)
    except HTTPException:
        raise
    except LLMClientError as exc:
        logger.error("Audio transcription error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during audio transcription: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to transcribe audio.")
