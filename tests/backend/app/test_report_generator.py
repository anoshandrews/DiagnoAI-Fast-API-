from backend.app.models.schemas import ChatMessage
from backend.app.services import report_generator


def test_generate_medical_report_falls_back_when_llm_missing(monkeypatch):
    def raise_error(*, messages, temperature=0.2, model=None):
        del messages, temperature, model
        raise report_generator.LLMClientError("missing key")

    monkeypatch.setattr(report_generator, "generate_text", raise_error)

    report = report_generator.generate_medical_report(
        [ChatMessage(role="user", content="Sore throat and cough for three days.")]
    )

    assert "Sore throat and cough" in report.patient_summary
    assert report.disclaimer.startswith("This handoff summary is not a diagnosis")
