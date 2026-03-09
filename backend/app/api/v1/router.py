from fastapi import APIRouter

from backend.app.api.v1.endpoints import chat, report

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
