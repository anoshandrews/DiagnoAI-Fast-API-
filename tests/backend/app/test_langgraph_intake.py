from langchain_core.messages import HumanMessage

from backend.app.core.db import db
from backend.app.graph.nodes import (
    emergency_escalation_node,
    handoff_synthesizer_node,
    hydrate_context_node,
    symptom_extractor_node,
    triage_guardrail_node,
)
from backend.app.graph.workflow import intake_graph
from backend.app.models.schemas import ClinicianBaseline


def test_hydrate_context_loads_clinician_baseline():
    patient = ClinicianBaseline(
        patient_id="test-p123",
        full_name="Alice Smith",
        age=34,
        biological_sex="Female",
        known_allergies=["Sulfa"],
        chronic_conditions=["Migraine"],
        current_medications=["Sumatriptan"],
        sensitive_notes="Sensitive psychiatric note",
    )
    db.save_patient(patient)

    state = {
        "patient_id": "test-p123",
        "session_id": "sess-abc",
        "messages": [HumanMessage(content="Hello doctor")],
    }
    result = hydrate_context_node(state)

    assert result["clinician_baseline"]["patient_id"] == "test-p123"
    assert result["clinician_baseline"]["full_name"] == "Alice Smith"
    assert result["turn_count"] == 1
    assert "symptoms" in result


def test_triage_guardrail_detects_emergency_red_flags():
    state = {
        "patient_id": "test-p123",
        "messages": [HumanMessage(content="I have severe crushing chest pain radiating to my left arm")],
        "red_flags": [],
    }
    result = triage_guardrail_node(state)

    assert result["intake_stage"] == "red_flag"
    assert len(result["red_flags"]) >= 1
    assert "chest pain" in result["red_flags"][0].lower() or "left arm" in result["red_flags"][0].lower()


def test_emergency_escalation_node_provides_urgent_directive():
    state = {
        "red_flags": ["Acute chest pain radiating to left arm"],
        "intake_stage": "red_flag",
    }
    result = emergency_escalation_node(state)

    assert result["intake_stage"] == "red_flag"
    message_content = result["messages"][0].content
    assert "911" in message_content
    assert "Emergency Department" in message_content


def test_symptom_extractor_parses_severity_and_slots():
    state = {
        "messages": [HumanMessage(content="I have a headache since yesterday, severity is 7 out of 10 in my temples")],
        "symptoms": {},
    }
    result = symptom_extractor_node(state)

    symptoms = result["symptoms"]
    assert symptoms.get("severity_1_to_10") == 7
    assert symptoms.get("primary_complaint") is not None


def test_handoff_synthesizer_produces_clinician_report():
    patient = ClinicianBaseline(
        patient_id="synth-patient",
        full_name="Bob Jones",
        age=52,
        biological_sex="Male",
        known_allergies=["Latex"],
        chronic_conditions=["Type 2 Diabetes"],
        current_medications=["Metformin 500mg"],
        sensitive_notes="History of alcohol use disorder in remission.",
    )
    db.save_patient(patient)

    state = {
        "patient_id": "synth-patient",
        "session_id": "sess-synth",
        "clinician_baseline": patient,
        "symptoms": {
            "primary_complaint": "Persistent productive cough",
            "onset": "4 days ago",
            "duration": "4 days",
            "location": "Upper chest",
            "severity_1_to_10": 5,
            "character": "Hacking with greenish phlegm",
            "aggravating_relieving_factors": "Worse lying down",
            "associated_symptoms": ["Mild fever", "Fatigue"],
        },
        "red_flags": [],
        "messages": [HumanMessage(content="Persistent productive cough")],
    }

    result = handoff_synthesizer_node(state)

    assert result["intake_stage"] == "completed"
    assert "clinician_handoff_markdown" in result
    report = result["clinician_handoff_markdown"]
    assert "Bob Jones" in report
    assert "Persistent productive cough" in report
    assert "Metformin 500mg" in report


def test_langgraph_full_workflow_execution():
    config = {"configurable": {"thread_id": "integration-sess-1"}}
    input_data = {
        "patient_id": "default-patient",
        "session_id": "integration-sess-1",
        "messages": [HumanMessage(content="I have a sore throat and fever for two days, severity is 4 out of 10.")],
    }

    state = intake_graph.invoke(input_data, config=config)

    assert state["patient_id"] == "default-patient"
    assert len(state["messages"]) >= 2
    assert state["intake_stage"] in ["gathering", "completed", "red_flag"]
