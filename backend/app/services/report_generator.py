import json
from io import BytesIO

from pydantic import ValidationError

from backend.app.core.llm_client import LLMClientError, generate_text, parse_json_response
from backend.app.core.logging import logger
from backend.app.models.schemas import ChatMessage, MedicalReport


def summarize_symptom_chat(chat_history: list[ChatMessage]) -> str:
    user_inputs = [msg.content.strip() for msg in chat_history if msg.role == "user"]
    return " ".join(user_inputs).strip() or "No symptom details were provided."


def download_medical_report_pdf(content: str, filename: str = "medical_report.pdf") -> BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()
    story = []

    # Add support for Markdown-style bold (**text**)
    for line in content.split('\n'):
        while '**' in line:
            line = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
        para = Paragraph(line, styles["Normal"])
        story.append(para)
        story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    buffer.seek(0)

    return buffer

def retrieve_medical_context(symptom_summary: str, top_k: int = 3) -> str:
    del top_k
    if not symptom_summary:
        return "No symptom summary available."
    return (
        "Context retrieval is not enabled in the modernized local mode. "
        "Use the structured symptom summary as the primary clinician handoff."
    )


def query_pubmed(query: str, max_results: int = 5) -> list[dict[str, str]]:
    del max_results
    try:
        logger.info("PubMed lookup requested for query: %s", query)
        return []
    except Exception:
        logger.exception("Unexpected PubMed lookup failure.")
        return []

def embed_and_store(raw_docs: list, vectorstore) -> list:
    del vectorstore
    return raw_docs


def _fallback_report(chat_history: list[ChatMessage]) -> MedicalReport:
    summary = summarize_symptom_chat(chat_history)
    return MedicalReport(
        patient_summary=summary,
        symptom_timeline=["Timeline not fully structured yet; review raw chat history."],
        red_flags=["No automated red-flag detection available in fallback mode."],
        recommended_next_steps=[
            "Review the symptom timeline with a clinician.",
            "Confirm medication history, allergies, and relevant conditions.",
            "Escalate urgently if chest pain, breathing trouble, fainting, or confusion are present.",
        ],
        disclaimer="This handoff summary is not a diagnosis and should be reviewed by a qualified clinician.",
    )


def generate_medical_report(chat_history: list[ChatMessage]) -> MedicalReport:
    summary = summarize_symptom_chat(chat_history)
    prompt = f"""
You create safe clinician handoff reports from symptom intake conversations.
Do not diagnose and do not invent clinical facts.
Return valid JSON with keys:
patient_summary, symptom_timeline, red_flags, recommended_next_steps, disclaimer.

Conversation summary:
{summary}
""".strip()

    messages = [
        {
            "role": "system",
            "content": "You are a careful medical intake summarizer. Output JSON only.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        payload = generate_text(messages=messages, temperature=0.1)
        parsed = parse_json_response(payload)
        return MedicalReport.model_validate(parsed)
    except (LLMClientError, json.JSONDecodeError, ValidationError, ValueError):
        logger.warning("Falling back to deterministic report generation.")
        return _fallback_report(chat_history)


def render_medical_report_markdown(report: MedicalReport) -> str:
    lines = [
        "## Clinician Handoff Summary",
        "",
        f"**Patient Summary**: {report.patient_summary}",
        "",
        "**Symptom Timeline**",
    ]
    lines.extend(f"- {item}" for item in report.symptom_timeline)
    lines.append("")
    lines.append("**Red Flags**")
    lines.extend(f"- {item}" for item in report.red_flags)
    lines.append("")
    lines.append("**Recommended Next Steps**")
    lines.extend(f"- {item}" for item in report.recommended_next_steps)
    lines.append("")
    lines.append(f"**Disclaimer**: {report.disclaimer}")
    return "\n".join(lines)
