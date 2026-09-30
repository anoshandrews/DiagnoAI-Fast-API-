from fastapi import APIRouter

from backend.app.api.v1.endpoints import chat, clinician, report, voice

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(clinician.router, prefix="/clinician", tags=["clinician"])
