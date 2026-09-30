from typing import Annotated, Literal, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from backend.app.models.schemas import ClinicianBaseline, ExtractedSymptoms


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    patient_id: str
    session_id: str
    clinician_baseline: ClinicianBaseline | None
    symptoms: dict[str, Any]
    red_flags: list[str]
    intake_stage: Literal["gathering", "red_flag", "completed"]
    clinician_handoff_markdown: str | None
    turn_count: int
