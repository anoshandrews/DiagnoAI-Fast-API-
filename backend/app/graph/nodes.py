import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from backend.app.core.db import db
from backend.app.core.llm_client import LLMClientError, generate_text, parse_json_response
from backend.app.graph.state import AgentState
from backend.app.models.schemas import ClinicianBaseline, ExtractedSymptoms

logger = logging.getLogger(__name__)

RED_FLAG_PATTERNS = [
    r"chest (pain|pressure|tightness|heaviness)",
    r"radiat(ing|es) to (left arm|jaw|back|neck)",
    r"(shortness of breath|trouble breathing|cannot breathe|suffocating)",
    r"(sudden numbness|facial droop|arm weakness|slurred speech)",
    r"(coughing up blood|vomiting blood)",
    r"(severe allergic reaction|throat closing|swelling of (lips|tongue|throat))",
    r"(loss of consciousness|fainted|blacked out)",
]

TERMINATION_PHRASES = [
    "that's all",
    "thats all",
    "that is all",
    "nothing else",
    "i'm done",
    "im done",
    "create report",
    "ready for report",
    "generate report",
]


def _get_latest_user_message(state: AgentState) -> str:
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or (hasattr(msg, "role") and msg.role == "user"):
            return str(msg.content)
    return ""


def hydrate_context_node(state: AgentState) -> dict[str, Any]:
    """
    1. Loads patient demographics & sensitive baseline (clinician-entered only).
    2. Initializes symptoms state and increments turn count.
    """
    patient_id = state.get("patient_id") or "default-patient"
    session_id = state.get("session_id") or "default-session"

    baseline = db.get_patient(patient_id)
    if not baseline:
        # Fallback basic baseline if not yet registered in clinician DB
        baseline = ClinicianBaseline(
            patient_id=patient_id,
            full_name="Unregistered Patient",
            age=30,
            biological_sex="Unknown",
        )

    existing_symptoms = state.get("symptoms") or ExtractedSymptoms().model_dump()
    existing_red_flags = state.get("red_flags") or []
    turn_count = state.get("turn_count", 0) + 1

    return {
        "patient_id": patient_id,
        "session_id": session_id,
        "clinician_baseline": baseline.model_dump() if baseline else None,
        "symptoms": existing_symptoms,
        "red_flags": existing_red_flags,
        "turn_count": turn_count,
    }


def triage_guardrail_node(state: AgentState) -> dict[str, Any]:
    """
    2. Safety guardrail: evaluates the latest user message for acute red flags.
    Immediately alerts if life-threatening emergencies are detected.
    """
    user_text = _get_latest_user_message(state)
    detected_red_flags = list(state.get("red_flags", []))

    # Fast regex screening
    for pattern in RED_FLAG_PATTERNS:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            flag_desc = f"Acute symptom detected: '{match.group(0)}'"
            if flag_desc not in detected_red_flags:
                detected_red_flags.append(flag_desc)

    # Secondary LLM evaluation if available and not already flagged
    if not detected_red_flags and user_text.strip():
        system_prompt = (
            "You are a medical triage safety classifier. "
            "Determine if the user's message indicates an acute, life-threatening emergency "
            "(e.g., heart attack, acute stroke, respiratory arrest, severe anaphylaxis, acute hemorrhage). "
            "Respond ONLY with valid JSON: {\"is_emergency\": true/false, \"red_flags\": [list of strings]}"
        )
        try:
            raw = generate_text(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.0,
            )
            parsed = parse_json_response(raw)
            if parsed.get("is_emergency") and parsed.get("red_flags"):
                for rf in parsed["red_flags"]:
                    if rf not in detected_red_flags:
                        detected_red_flags.append(rf)
        except Exception:
            pass

    if detected_red_flags:
        logger.warning("Red flags detected in patient intake: %s", detected_red_flags)
        return {
            "red_flags": detected_red_flags,
            "intake_stage": "red_flag",
        }

    return {
        "red_flags": detected_red_flags,
        "intake_stage": state.get("intake_stage", "gathering"),
    }


def emergency_escalation_node(state: AgentState) -> dict[str, Any]:
    """
    Emergency intervention node. Stops standard questioning and instructs immediate care.
    """
    red_flags = state.get("red_flags", [])
    flag_list_str = ", ".join(red_flags) if red_flags else "severe symptoms"

    alert_message = (
        f"⚠️ **URGENT MEDICAL SAFETY ALERT**\n\n"
        f"Based on what you just described ({flag_list_str}), this could indicate an acute medical emergency.\n\n"
        f"**Actions to take right now:**\n"
        f"1. **Call 911 (or your local emergency response number) immediately.**\n"
        f"2. Go to the nearest Emergency Department.\n"
        f"3. Do NOT wait for an online intake review or physician appointment.\n\n"
        f"Your safety is paramount. Please seek in-person emergency medical care immediately."
    )

    return {
        "messages": [AIMessage(content=alert_message)],
        "intake_stage": "red_flag",
    }


def symptom_extractor_node(state: AgentState) -> dict[str, Any]:
    """
    3. Analyzes conversation history and extracts SOCRATES / OPQRST clinical slots.
    """
    user_text = _get_latest_user_message(state)
    current_symptoms = dict(state.get("symptoms", {}))
    user_lower = user_text.lower()

    # Check for user termination intent
    user_wants_to_stop = any(phrase in user_lower for phrase in TERMINATION_PHRASES)

    system_prompt = (
        "You are an expert clinical intake entity extractor. "
        "Extract structured symptom details from the patient's statement according to OPQRST/SOCRATES.\n"
        "Return ONLY valid JSON with keys:\n"
        "{\n"
        '  "primary_complaint": string or null,\n'
        '  "onset": string or null,\n'
        '  "duration": string or null,\n'
        '  "location": string or null,\n'
        '  "severity_1_to_10": integer (1-10) or null,\n'
        '  "character": string (e.g. sharp, throbbing, dull) or null,\n'
        '  "aggravating_relieving_factors": string or null,\n'
        '  "associated_symptoms": list of strings\n'
        "}"
    )

    try:
        raw_json = generate_text(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Existing data: {json.dumps(current_symptoms)}\nPatient message: {user_text}"},
            ],
            temperature=0.1,
        )
        extracted = parse_json_response(raw_json)
        for key, val in extracted.items():
            if val is not None and val != "":
                if key == "associated_symptoms" and isinstance(val, list):
                    existing_list = current_symptoms.get("associated_symptoms", [])
                    merged = list(set(existing_list + val))
                    current_symptoms["associated_symptoms"] = merged
                else:
                    current_symptoms[key] = val
    except Exception as exc:
        logger.warning("LLM slot extraction fallback: %s", exc)
        # Deterministic fallback extraction
        if not current_symptoms.get("primary_complaint"):
            current_symptoms["primary_complaint"] = user_text[:120]
        # Check for numbers 1-10 for severity
        match_sev = re.search(r"\b([1-9]|10)\s*(out of 10|/10)?\b", user_lower)
        if match_sev:
            try:
                current_symptoms["severity_1_to_10"] = int(match_sev.group(1))
            except ValueError:
                pass

    # Check completeness
    has_complaint = bool(current_symptoms.get("primary_complaint"))
    has_timing = bool(current_symptoms.get("onset") or current_symptoms.get("duration"))
    has_detail = bool(current_symptoms.get("severity_1_to_10") or current_symptoms.get("location"))

    is_complete = user_wants_to_stop or (has_complaint and has_timing and has_detail and state.get("turn_count", 0) >= 3)

    return {
        "symptoms": current_symptoms,
        "intake_stage": "completed" if is_complete else "gathering",
    }


def adaptive_questioner_node(state: AgentState) -> dict[str, Any]:
    """
    4. Generates the next focused, empathetic clinical follow-up question.
    Only asks 1 question at a time, targeted at missing clinical slots.
    Incorporates known clinician baseline (allergies, chronic conditions).
    """
    raw_baseline = state.get("clinician_baseline")
    baseline: ClinicianBaseline | None = (
        ClinicianBaseline.model_validate(raw_baseline)
        if isinstance(raw_baseline, dict)
        else raw_baseline
    )
    symptoms = state.get("symptoms", {})

    baseline_summary = "None known"
    if baseline:
        baseline_summary = (
            f"Age {baseline.age}, {baseline.biological_sex}. "
            f"Conditions: {', '.join(baseline.chronic_conditions) or 'None'}. "
            f"Meds: {', '.join(baseline.current_medications) or 'None'}. "
            f"Allergies: {', '.join(baseline.known_allergies) or 'None'}."
        )

    system_prompt = (
        "You are DiagnoAI, a thoughtful medical symptom intake agent for clinician handoff.\n"
        "Guidelines:\n"
        "1. Ask EXACTLY ONE clear, focused follow-up question.\n"
        "2. Do NOT diagnose, speculate on diseases, or offer treatment.\n"
        "3. Empathize briefly, then ask for the most clinically valuable missing detail.\n"
        "4. Missing detail priorities: Onset/Duration -> Severity (1-10) -> Location/Radiation -> Triggers/Relief.\n"
        f"Patient baseline record: {baseline_summary}\n"
        f"Symptoms gathered so far: {json.dumps(symptoms)}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in state.get("messages", []):
        role = "user" if isinstance(m, HumanMessage) or getattr(m, "role", "") == "user" else "assistant"
        messages.append({"role": role, "content": str(m.content)})

    try:
        reply = generate_text(messages=messages, temperature=0.3)
    except Exception as exc:
        logger.warning("LLM question generator fallback: %s", exc)
        # Deterministic targeted questions
        if not symptoms.get("onset") and not symptoms.get("duration"):
            reply = "When did you first notice these symptoms, and have they been constant or coming and going?"
        elif not symptoms.get("severity_1_to_10"):
            reply = "On a scale from 1 to 10 (where 1 is very mild and 10 is the worst pain imaginable), how would you rate this right now?"
        elif not symptoms.get("location"):
            reply = "Where exactly do you feel this discomfort, and does it spread or radiate anywhere else?"
        elif not symptoms.get("aggravating_relieving_factors"):
            reply = "Does anything specific make the feeling better or worse, such as movement, rest, or food?"
        else:
            reply = "Is there any other symptom or detail you would like the doctor to know?"

    return {
        "messages": [AIMessage(content=reply)],
    }


def handoff_synthesizer_node(state: AgentState) -> dict[str, Any]:
    """
    5. Assembles the structured clinician handoff report (SOAP/SBAR format).
    """
    raw_baseline = state.get("clinician_baseline")
    baseline: ClinicianBaseline | None = (
        ClinicianBaseline.model_validate(raw_baseline)
        if isinstance(raw_baseline, dict)
        else raw_baseline
    )
    symptoms = state.get("symptoms", {})
    red_flags = state.get("red_flags", [])
    patient_id = state.get("patient_id", "default-patient")
    session_id = state.get("session_id", "default-session")

    patient_name = baseline.full_name if baseline else "Patient"
    age = baseline.age if baseline else "Unknown"
    sex = baseline.biological_sex if baseline else "Unknown"
    allergies = ", ".join(baseline.known_allergies) if baseline and baseline.known_allergies else "NKDA (None reported)"
    conditions = ", ".join(baseline.chronic_conditions) if baseline and baseline.chronic_conditions else "None recorded"
    meds = ", ".join(baseline.current_medications) if baseline and baseline.current_medications else "None recorded"
    sensitive_notes = baseline.sensitive_notes if baseline and baseline.sensitive_notes else "None recorded"

    complaint = symptoms.get("primary_complaint", "Unspecified symptom complaint")
    onset = symptoms.get("onset", "Not specified")
    duration = symptoms.get("duration", "Not specified")
    location = symptoms.get("location", "Not specified")
    severity = f"{symptoms.get('severity_1_to_10')}/10" if symptoms.get("severity_1_to_10") else "Unrated"
    character = symptoms.get("character", "Not specified")
    triggers = symptoms.get("aggravating_relieving_factors", "None noted")
    associated = ", ".join(symptoms.get("associated_symptoms", [])) or "None reported"

    system_prompt = (
        "You are an expert clinical summarizer. Generate a high-yield SBAR / SOAP clinician handoff report.\n"
        "Ensure clear sections, clinical terminology, and highlight differential considerations for the physician.\n"
        "Do not invent facts not in the intake data."
    )

    user_prompt = f"""
Patient Baseline (Clinician Record):
- ID: {patient_id}
- Demographics: {patient_name}, {age} y/o, {sex}
- Chronic Conditions: {conditions}
- Current Medications: {meds}
- Known Allergies: {allergies}
- Sensitive Clinician Notes: {sensitive_notes}

Current Symptom Intake:
- Primary Complaint: {complaint}
- Onset & Duration: {onset} (Duration: {duration})
- Location & Character: {location} ({character})
- Severity: {severity}
- Aggravating/Relieving Factors: {triggers}
- Associated Symptoms: {associated}
- Detected Red Flags: {', '.join(red_flags) or 'None'}
"""

    report_markdown = ""
    try:
        report_markdown = generate_text(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        logger.warning("LLM report synthesizer fallback: %s", exc)
        # Deterministic high-yield clinical report
        report_markdown = f"""## 📋 Clinician Handoff Intake Report

### 1. Patient Demographics & Baseline (EHR)
* **Patient ID**: `{patient_id}`
* **Name / Age / Sex**: {patient_name}, {age} years, {sex}
* **Allergies**: {allergies}
* **Active Conditions**: {conditions}
* **Current Medications**: {meds}
* **Clinician Sensitive Notes**: {sensitive_notes}

### 2. Chief Complaint & History of Present Illness (HPI)
* **Chief Complaint**: {complaint}
* **Onset & Duration**: Started {onset}; ongoing for {duration}.
* **Location & Quality**: Located at {location}; described as {character}.
* **Reported Severity**: {severity}
* **Modifying Factors**: {triggers}
* **Associated Symptoms**: {associated}

### 3. Triage & Red-Flag Assessment
* **Red Flags**: {', '.join(red_flags) if red_flags else 'No acute life-threatening red flags flagged during conversation.'}

### 4. Recommended Clinician Actions
* Conduct targeted physical examination of {location}.
* Correlate symptoms against patient's active medical history ({conditions}).
* Confirm patient medication compliance with {meds}.

---
*Disclaimer: This intake report was compiled by DiagnoAI for clinician review. It does NOT provide a diagnosis.*
"""

    closing_message = (
        "Thank you. I have collected all necessary intake details regarding your symptoms.\n\n"
        "Your structured handoff summary has been generated and queued for your clinician's review. "
        "The clinician will examine this information alongside your medical baseline at your consultation."
    )

    # Persist session record to database
    serializable_messages = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": str(m.content)}
        for m in state.get("messages", [])
    ]
    db.save_session_record(
        session_id=session_id,
        patient_id=patient_id,
        intake_stage="completed",
        extracted_symptoms=symptoms,
        red_flags=red_flags,
        report_markdown=report_markdown,
        messages=serializable_messages,
    )

    return {
        "messages": [AIMessage(content=closing_message)],
        "clinician_handoff_markdown": report_markdown,
        "intake_stage": "completed",
    }
