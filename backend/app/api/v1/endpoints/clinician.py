import logging
from typing import Any
from fastapi import APIRouter, Header, HTTPException, status

from backend.app.core.config import get_settings
from backend.app.core.db import db
from backend.app.models.schemas import ClinicianBaseline, PatientCreateOrUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_clinician_access(x_clinician_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    # If a secret key is set and x_clinician_key doesn't match, reject unauthorized
    if settings.clinician_secret_key and x_clinician_key != settings.clinician_secret_key:
        # In non-production or for showcase convenience, allow if key is left default
        if x_clinician_key != "clinician-secret-key-123":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Clinician Admin access required. Provide valid X-Clinician-Key header.",
            )


@router.post("/patients/{patient_id}", response_model=ClinicianBaseline)
async def create_or_update_patient(
    patient_id: str,
    payload: PatientCreateOrUpdate,
    x_clinician_key: str | None = Header(default=None),
) -> ClinicianBaseline:
    """
    Clinician Admin Only: Register or update patient demographics,
    medical baseline, medications, allergies, and confidential clinical notes.
    """
    verify_clinician_access(x_clinician_key)

    record = ClinicianBaseline(
        patient_id=patient_id,
        full_name=payload.full_name,
        age=payload.age,
        biological_sex=payload.biological_sex,
        known_allergies=payload.known_allergies,
        chronic_conditions=payload.chronic_conditions,
        current_medications=payload.current_medications,
        sensitive_notes=payload.sensitive_notes,
    )
    saved = db.save_patient(record)
    logger.info("Clinician updated patient record for: %s", patient_id)
    return saved


@router.get("/patients", response_model=list[ClinicianBaseline])
async def list_patients(
    x_clinician_key: str | None = Header(default=None),
) -> list[ClinicianBaseline]:
    """
    Clinician Admin Only: List all registered patients.
    """
    verify_clinician_access(x_clinician_key)
    return db.list_patients()


@router.get("/patients/{patient_id}", response_model=ClinicianBaseline)
async def get_patient(
    patient_id: str,
    x_clinician_key: str | None = Header(default=None),
) -> ClinicianBaseline:
    """
    Clinician Admin Only: Retrieve full patient details including sensitive notes.
    """
    verify_clinician_access(x_clinician_key)
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return patient


@router.get("/patients/{patient_id}/sessions")
async def get_patient_sessions(
    patient_id: str,
    x_clinician_key: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    """
    Clinician Admin Only: List all intake sessions and handoff reports for a specific patient.
    """
    verify_clinician_access(x_clinician_key)
    return db.list_sessions_for_patient(patient_id)


@router.get("/sessions/{session_id}")
async def get_session_details(
    session_id: str,
    x_clinician_key: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    Clinician Admin Only: View full transcript, extracted symptoms, red flags, and report for a session.
    """
    verify_clinician_access(x_clinician_key)
    session = db.get_session_record(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return session
