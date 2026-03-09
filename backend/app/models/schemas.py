from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    user_text: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None

    @model_validator(mode="after")
    def set_session_id(self) -> "ChatRequest":
        if not self.session_id:
            self.session_id = str(uuid4())
        return self


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    chat_history: list[ChatMessage]


class MedicalReport(BaseModel):
    patient_summary: str
    symptom_timeline: list[str]
    red_flags: list[str]
    recommended_next_steps: list[str]
    disclaimer: str


class ReportRequest(BaseModel):
    chat_history: list[ChatMessage] = Field(min_length=1)


class ReportResponse(BaseModel):
    report: MedicalReport
    markdown: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
