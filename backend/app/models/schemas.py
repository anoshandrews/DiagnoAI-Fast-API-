from typing import Literal
from uuid import uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=5000)


class ClinicianBaseline(BaseModel):
    """
    Patient demographics and sensitive medical baseline.
    Restricted: ONLY entered and edited by the Clinician / Admin.
    """
    patient_id: str
    full_name: str
    age: int = Field(ge=0, le=130)
    biological_sex: Literal["Male", "Female", "Other", "Unknown"] = "Unknown"
    known_allergies: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    sensitive_notes: str | None = Field(
        default=None,
        description="Confidential clinical notes, psychiatric history, or substance history.",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PatientCreateOrUpdate(BaseModel):
    full_name: str
    age: int = Field(ge=0, le=130)
    biological_sex: Literal["Male", "Female", "Other", "Unknown"] = "Unknown"
    known_allergies: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    sensitive_notes: str | None = None


class ExtractedSymptoms(BaseModel):
    """Structured clinical symptom slots based on SOCRATES / OPQRST intake."""
    primary_complaint: str | None = None
    onset: str | None = None
    duration: str | None = None
    location: str | None = None
    severity_1_to_10: int | None = Field(default=None, ge=1, le=10)
    character: str | None = None
    aggravating_relieving_factors: str | None = None
    associated_symptoms: list[str] = Field(default_factory=list)


class MedicalReport(BaseModel):
    patient_summary: str
    symptom_timeline: list[str]
    red_flags: list[str]
    recommended_next_steps: list[str]
    disclaimer: str = (
        "This intake summary is generated for clinician handoff only and is NOT a medical diagnosis."
    )


class ChatRequest(BaseModel):
    user_text: str = Field(min_length=1, max_length=4000)
    patient_id: str = "default-patient"
    session_id: str | None = None

    @model_validator(mode="after")
    def set_session_id(self) -> "ChatRequest":
        if not self.session_id:
            self.session_id = str(uuid4())
        return self


class ChatResponse(BaseModel):
    session_id: str
    patient_id: str = "default-patient"
    reply: str
    intake_stage: Literal["gathering", "red_flag", "completed"] = "gathering"
    extracted_symptoms: ExtractedSymptoms = Field(default_factory=ExtractedSymptoms)
    red_flags: list[str] = Field(default_factory=list)
    report_markdown: str | None = None
    chat_history: list[ChatMessage]


class ReportRequest(BaseModel):
    chat_history: list[ChatMessage] = Field(min_length=1)
    patient_id: str | None = None


class ReportResponse(BaseModel):
    report: MedicalReport
    markdown: str


class TranscriptionResponse(BaseModel):
    text: str
    model: str


class SessionOverview(BaseModel):
    session_id: str
    patient_id: str
    intake_stage: str
    message_count: int
    has_red_flags: bool
    report_ready: bool
    created_at: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str = "0.3.0"
