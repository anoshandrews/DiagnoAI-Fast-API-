from fastapi.testclient import TestClient

from backend.main import app
from backend.app.api.v1.endpoints import chat as chat_endpoint
from backend.app.models.schemas import ChatMessage


client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_route_returns_session_history(monkeypatch):
    async def fake_handle_user_prompt(history):
        assert history[-1].content == "I have a fever."
        return "How long have you had the fever?"

    chat_endpoint.session_store.clear("test-session")
    monkeypatch.setattr(chat_endpoint, "handle_user_prompt", fake_handle_user_prompt)

    response = client.post(
        "/api/v1/chat",
        json={"user_text": "I have a fever.", "session_id": "test-session"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "test-session"
    assert payload["reply"] == "How long have you had the fever?"
    assert len(payload["chat_history"]) == 2


def test_report_route_returns_structured_report(monkeypatch):
    from backend.app.api.v1.endpoints import report as report_endpoint
    from backend.app.models.schemas import MedicalReport

    def fake_generate_medical_report(chat_history):
        assert chat_history[0].content == "I have had chest discomfort for two days."
        return MedicalReport(
            patient_summary="Chest discomfort for two days.",
            symptom_timeline=["Started two days ago."],
            red_flags=["Escalate if pain worsens or breathing difficulty appears."],
            recommended_next_steps=["Review symptoms with a clinician today."],
            disclaimer="This is not a diagnosis.",
        )

    monkeypatch.setattr(report_endpoint, "generate_medical_report", fake_generate_medical_report)

    response = client.post(
        "/api/v1/report",
        json={
            "chat_history": [
                {"role": "user", "content": "I have had chest discomfort for two days."}
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report"]["patient_summary"] == "Chest discomfort for two days."
    assert "Clinician Handoff Summary" in body["markdown"]
