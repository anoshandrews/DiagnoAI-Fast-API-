from fastapi import APIRouter

from backend.app.models.schemas import ReportRequest, ReportResponse
from backend.app.services.report_generator import (
    generate_medical_report,
    render_medical_report_markdown,
)

router = APIRouter()


@router.post("", response_model=ReportResponse)
async def generate_report(payload: ReportRequest) -> ReportResponse:
    report = generate_medical_report(payload.chat_history)
    return ReportResponse(report=report, markdown=render_medical_report_markdown(report))
