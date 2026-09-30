import json
import os
import uuid
import httpx
import chainlit as cl

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
CLINICIAN_KEY = os.getenv("CLINICIAN_SECRET_KEY", "clinician-secret-key-123")


def format_slots_markdown(symptoms: dict) -> str:
    """Renders structured OPQRST / SOCRATES slots in a clean markdown table."""
    severity = f"{symptoms.get('severity_1_to_10')}/10" if symptoms.get("severity_1_to_10") else "Unrated"
    associated = ", ".join(symptoms.get("associated_symptoms", [])) or "None noted"
    
    return f"""### 🩺 Live Extracted Clinical Slots (SOCRATES / OPQRST)

| Dimension | Extracted Value |
| :--- | :--- |
| **Chief Complaint** | {symptoms.get('primary_complaint') or 'Pending...'} |
| **Onset** | {symptoms.get('onset') or 'Pending...'} |
| **Duration** | {symptoms.get('duration') or 'Pending...'} |
| **Location / Radiation** | {symptoms.get('location') or 'Pending...'} |
| **Reported Severity** | **{severity}** |
| **Character / Quality** | {symptoms.get('character') or 'Pending...'} |
| **Modifying Factors** | {symptoms.get('aggravating_relieving_factors') or 'Pending...'} |
| **Associated Symptoms** | {associated} |
"""


@cl.on_chat_start
async def on_chat_start():
    session_id = str(uuid.uuid4())
    patient_id = "default-patient"

    cl.user_session.set("session_id", session_id)
    cl.user_session.set("patient_id", patient_id)
    cl.user_session.set("symptoms", {})
    cl.user_session.set("intake_stage", "gathering")
    cl.user_session.set("red_flags", [])
    cl.user_session.set("report_markdown", None)

    # Initial Welcome message with quick action chips
    actions = [
        cl.Action(name="view_slots", payload={"action": "view_slots"}, label="📊 Live Clinical Slots"),
        cl.Action(name="view_baseline", payload={"action": "view_baseline"}, label="📋 Patient Baseline (EHR)"),
        cl.Action(name="clinician_portal", payload={"action": "clinician_portal"}, label="🩺 Clinician Admin"),
    ]

    welcome_content = (
        "## ⚕️ DiagnoAI Intake Assistant\n\n"
        "Hello! I am your clinical intake assistant powered by **Stateful LangGraph**.\n\n"
        "Please describe what symptoms you are experiencing today. You can:\n"
        "* **Type your symptoms** in the message bar below\n"
        "* **Upload or record an audio file** for instant transcription via **Groq Whisper Turbo**\n"
        "* Use the quick action buttons below at any time\n\n"
        "*(Note: Your clinician has pre-registered your baseline health history. "
        "I do not diagnose; I assemble your symptoms into a clinician handoff report.)*"
    )

    await cl.Message(content=welcome_content, actions=actions).send()


@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    patient_id = cl.user_session.get("patient_id")
    user_text = message.content.strip() if message.content else ""

    # 1. Handle Voice / Audio Attachments (Groq Whisper Turbo)
    if message.elements:
        for element in message.elements:
            if element.mime and any(audio_type in element.mime for audio_type in ["audio", "ogg", "wav", "mp4", "webm", "mpeg"]):
                async with cl.Step(name="🎙️ Groq Whisper Turbo", type="tool") as voice_step:
                    voice_step.output = f"Transcribing audio file: `{element.name}` via Groq Whisper Turbo..."
                    try:
                        async with httpx.AsyncClient() as client:
                            with open(element.path, "rb") as audio_fh:
                                files = {"file": (element.name, audio_fh.read(), element.mime)}
                                res = await client.post(f"{BACKEND_URL}/api/v1/voice/transcribe", files=files, timeout=25.0)
                            if res.status_code == 200:
                                transcribed_text = res.json().get("text", "")
                                voice_step.output = f"**Transcribed Text:**\n\"{transcribed_text}\""
                                user_text = transcribed_text
                            else:
                                voice_step.output = f"❌ Transcription error ({res.status_code}): {res.text}"
                    except Exception as e:
                        voice_step.output = f"❌ Audio transcription failed: {e}"

    if not user_text:
        await cl.Message(content="Please provide your symptoms in text or upload an audio recording.").send()
        return

    # Slash command shortcuts
    if user_text.lower() == "/slots":
        symptoms = cl.user_session.get("symptoms", {})
        await cl.Message(content=format_slots_markdown(symptoms)).send()
        return

    if user_text.lower() == "/admin":
        await handle_clinician_portal()
        return

    # 2. Stateful LangGraph Execution Steps
    async with cl.Step(name="1. Context Hydrator", type="tool") as step1:
        step1.output = f"Hydrating EHR Baseline for `{patient_id}` from Supabase/PostgreSQL repository..."

    async with cl.Step(name="2. Triage & Guardrail", type="tool") as step2:
        step2.output = "Screening message for acute cardiovascular, respiratory, or neurological red flags..."

    async with cl.Step(name="3. LangGraph Orchestration", type="llm") as step3:
        step3.output = "Executing stateful intake graph with thread checkpointing..."
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{BACKEND_URL}/api/v1/chat",
                    json={
                        "user_text": user_text,
                        "patient_id": patient_id,
                        "session_id": session_id,
                    },
                    timeout=35.0,
                )
                res.raise_for_status()
                data = res.json()
        except Exception as e:
            step3.output = f"❌ Backend communication failure: {e}"
            await cl.Message(content=f"❌ Error connecting to DiagnoAI engine: {e}").send()
            return

        reply = data.get("reply", "Could you share more details about your symptoms?")
        stage = data.get("intake_stage", "gathering")
        symptoms = data.get("extracted_symptoms", {})
        red_flags = data.get("red_flags", [])
        report_md = data.get("report_markdown")

        # Save to user session
        cl.user_session.set("symptoms", symptoms)
        cl.user_session.set("intake_stage", stage)
        cl.user_session.set("red_flags", red_flags)
        if report_md:
            cl.user_session.set("report_markdown", report_md)

        step3.output = f"Intake stage: **{stage.upper()}** | Extracted severity: {symptoms.get('severity_1_to_10') or 'Pending'}"

    # 3. Handle Stage Outcomes
    if stage == "red_flag":
        emergency_card = (
            "### 🚨 CRITICAL MEDICAL SAFETY ALERT\n\n"
            f"{reply}\n\n"
            "--- \n"
            "⚠️ *Please stop using this online tool and call 911 or visit the nearest Emergency Department immediately.*"
        )
        await cl.Message(content=emergency_card).send()
        return

    # Standard conversational response
    actions = [
        cl.Action(name="view_slots", payload={"action": "view_slots"}, label="📊 View Updated Slots"),
    ]
    if report_md:
        actions.append(cl.Action(name="view_report", payload={"action": "view_report"}, label="📄 View Handoff Report"))

    await cl.Message(content=reply, actions=actions).send()

    # If intake completed, present the full report
    if stage == "completed" and report_md:
        report_file = cl.File(
            name=f"clinician_handoff_{patient_id}.md",
            content=report_md.encode("utf-8"),
            display="inline",
        )
        await cl.Message(
            content="### 📋 Generated Clinician Handoff Report\nYour symptom intake is complete. The report below has been prepared for your physician:",
            elements=[report_file],
        ).send()


@cl.action_callback("view_slots")
async def on_view_slots(action: cl.Action):
    symptoms = cl.user_session.get("symptoms", {})
    await cl.Message(content=format_slots_markdown(symptoms)).send()


@cl.action_callback("view_baseline")
async def on_view_baseline(action: cl.Action):
    patient_id = cl.user_session.get("patient_id", "default-patient")
    headers = {"X-Clinician-Key": CLINICIAN_KEY}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{BACKEND_URL}/api/v1/clinician/patients/{patient_id}", headers=headers, timeout=10.0)
            if res.status_code == 200:
                p = res.json()
                baseline_md = f"""### 📋 Patient EHR Baseline (Clinician Managed)

* **Patient ID**: `{p['patient_id']}`
* **Name**: {p['full_name']}
* **Age / Sex**: {p['age']} years | {p['biological_sex']}
* **Known Allergies**: {', '.join(p.get('known_allergies', [])) or 'NKDA (None reported)'}
* **Chronic Conditions**: {', '.join(p.get('chronic_conditions', [])) or 'None recorded'}
* **Current Medications**: {', '.join(p.get('current_medications', [])) or 'None recorded'}
* 🔒 **Clinician Sensitive Notes**: *{p.get('sensitive_notes') or 'None recorded'}*
"""
                await cl.Message(content=baseline_md).send()
            else:
                await cl.Message(content=f"⚠️ Could not load baseline ({res.status_code}): {res.text}").send()
    except Exception as e:
        await cl.Message(content=f"⚠️ Error querying patient baseline: {e}").send()


@cl.action_callback("view_report")
async def on_view_report(action: cl.Action):
    report_md = cl.user_session.get("report_markdown")
    if report_md:
        await cl.Message(content=report_md).send()
    else:
        await cl.Message(content="No clinician handoff report has been compiled yet. Complete the intake dialogue first.").send()


@cl.action_callback("clinician_portal")
async def on_clinician_portal(action: cl.Action):
    await handle_clinician_portal()


async def handle_clinician_portal():
    headers = {"X-Clinician-Key": CLINICIAN_KEY}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{BACKEND_URL}/api/v1/clinician/patients", headers=headers, timeout=10.0)
            if res.status_code == 200:
                patients = res.json()
                rows = []
                for p in patients:
                    rows.append(
                        f"| `{p['patient_id']}` | **{p['full_name']}** | {p['age']} | {p['biological_sex']} | {', '.join(p.get('known_allergies', [])) or 'None'} | {', '.join(p.get('chronic_conditions', [])) or 'None'} |"
                    )
                table_body = "\n".join(rows) if rows else "| None | - | - | - | - | - |"

                admin_md = f"""### 🩺 Clinician Admin Directory

| Patient ID | Name | Age | Sex | Allergies | Chronic Conditions |
| :--- | :--- | :--- | :--- | :--- | :--- |
{table_body}

---
*Clinicians can register patients or inspect intake sessions directly via REST endpoints or Swagger at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*
"""
                await cl.Message(content=admin_md).send()
            else:
                await cl.Message(content=f"⚠️ Clinician Admin error: {res.text}").send()
    except Exception as e:
        await cl.Message(content=f"⚠️ Failed to connect to clinician admin API: {e}").send()
