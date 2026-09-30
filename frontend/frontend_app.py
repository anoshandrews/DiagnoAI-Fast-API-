import logging
import os
from io import BytesIO
import requests
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ========== Streamlit Configuration ==========
st.set_page_config(
    page_title="DiagnoAI - Stateful LangGraph Intake",
    page_icon="⚕️",
    layout="wide",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_CHAT_URL = f"{BACKEND_URL}/api/v1/chat"
BACKEND_REPORT_URL = f"{BACKEND_URL}/api/v1/report"
BACKEND_VOICE_URL = f"{BACKEND_URL}/api/v1/voice/transcribe"
BACKEND_CLINICIAN_URL = f"{BACKEND_URL}/api/v1/clinician"

# ========== Session State Initialization ==========
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
if "patient_id" not in st.session_state:
    st.session_state.patient_id = "default-patient"
if "extracted_symptoms" not in st.session_state:
    st.session_state.extracted_symptoms = {}
if "intake_stage" not in st.session_state:
    st.session_state.intake_stage = "gathering"
if "red_flags" not in st.session_state:
    st.session_state.red_flags = []
if "report_markdown" not in st.session_state:
    st.session_state.report_markdown = None
if "clinician_key" not in st.session_state:
    st.session_state.clinician_key = "clinician-secret-key-123"

# ========== PDF Helper ==========
def build_pdf_report(markdown_content: str) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()
    story = []
    for line in markdown_content.split("\n"):
        clean_line = line
        while "**" in clean_line:
            clean_line = clean_line.replace("**", "<b>", 1).replace("**", "</b>", 1)
        story.append(Paragraph(clean_line, styles["Normal"]))
        story.append(Spacer(1, 0.06 * inch))
    doc.build(story)
    buffer.seek(0)
    return buffer


# ========== Sidebar: Mode Selector & Patient Context ==========
st.sidebar.markdown("## ⚕️ DiagnoAI Portal")
portal_mode = st.sidebar.radio(
    "Select Interface Mode",
    ["Patient Symptom Intake", "Clinician Admin Dashboard"],
    index=0,
)

st.sidebar.divider()

if portal_mode == "Patient Symptom Intake":
    st.sidebar.markdown("### 👤 Patient Context")
    selected_patient = st.sidebar.text_input(
        "Current Patient ID",
        value=st.session_state.patient_id,
        help="Demographics and sensitive records are managed securely by your clinician.",
    )
    if selected_patient != st.session_state.patient_id:
        st.session_state.patient_id = selected_patient
        st.session_state.chat_history = []
        st.session_state.report_markdown = None
        st.rerun()

    st.sidebar.markdown(f"**Session ID**: `{st.session_state.session_id[:8]}...`")
    if st.sidebar.button("🔄 New Intake Session"):
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.session_state.extracted_symptoms = {}
        st.session_state.intake_stage = "gathering"
        st.session_state.red_flags = []
        st.session_state.report_markdown = None
        st.rerun()

    # Voice Input Section
    st.sidebar.divider()
    st.sidebar.markdown("### 🎙️ Groq Whisper Voice Input")
    st.sidebar.caption("Speak or upload audio (m4a, mp3, wav) transcribed instantly via Groq.")
    audio_file = st.sidebar.file_uploader(
        "Upload audio recording",
        type=["wav", "mp3", "m4a", "ogg", "webm"],
        key="audio_uploader",
    )
    if audio_file is not None and st.sidebar.button("Transcribe & Send to Agent"):
        with st.spinner("Transcribing audio via Groq Whisper Turbo..."):
            try:
                files = {"file": (audio_file.name, audio_file.getvalue(), audio_file.type or "audio/wav")}
                res = requests.post(BACKEND_VOICE_URL, files=files, timeout=25)
                res.raise_for_status()
                transcribed_text = res.json().get("text", "").strip()
                if transcribed_text:
                    st.sidebar.success(f"Transcribed: *\"{transcribed_text}\"*")
                    # Send directly to agent
                    st.session_state.chat_history.append({"role": "user", "content": transcribed_text})
                    with st.spinner("Agent analyzing symptoms..."):
                        chat_res = requests.post(
                            BACKEND_CHAT_URL,
                            json={
                                "user_text": transcribed_text,
                                "patient_id": st.session_state.patient_id,
                                "session_id": st.session_state.session_id,
                            },
                            timeout=30,
                        )
                        chat_res.raise_for_status()
                        payload = chat_res.json()
                        st.session_state.chat_history.append({"role": "assistant", "content": payload.get("reply", "")})
                        st.session_state.intake_stage = payload.get("intake_stage", "gathering")
                        st.session_state.extracted_symptoms = payload.get("extracted_symptoms", {})
                        st.session_state.red_flags = payload.get("red_flags", [])
                        if payload.get("report_markdown"):
                            st.session_state.report_markdown = payload.get("report_markdown")
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"Audio transcription error: {e}")

# =========================================================================
# Mode 1: Patient Symptom Intake
# =========================================================================
if portal_mode == "Patient Symptom Intake":
    col_main, col_info = st.columns([2.5, 1.2])

    with col_main:
        st.markdown(
            """
            <h1 style='background: linear-gradient(to right, #0072FF, #00C6FF); -webkit-background-clip: text; color: transparent;'>
                ⚕️ DiagnoAI Intake Assistant
            </h1>
            <p style='color: #666;'>Stateful LangGraph Medical Triage & Clinical Intake System</p>
            """,
            unsafe_allow_html=True,
        )

        # Stage Banner
        if st.session_state.intake_stage == "red_flag":
            st.error("⚠️ **Emergency Red Flag Alert Triggered**. Immediate medical attention recommended.")
        elif st.session_state.intake_stage == "completed":
            st.success("✅ **Intake Completed**: Clinician handoff report compiled and queued.")
        else:
            st.info("💬 **Intake In Progress**: Describe your symptoms naturally. The agent asks one targeted question at a time.")

        # Render Chat History
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat Input
        user_prompt = st.chat_input("Describe what you are experiencing today...")
        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("Evaluating clinical intake state..."):
                    try:
                        res = requests.post(
                            BACKEND_CHAT_URL,
                            json={
                                "user_text": user_prompt,
                                "patient_id": st.session_state.patient_id,
                                "session_id": st.session_state.session_id,
                            },
                            timeout=30,
                        )
                        res.raise_for_status()
                        payload = res.json()
                        reply = payload.get("reply", "No reply received.")
                        st.markdown(reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})

                        st.session_state.intake_stage = payload.get("intake_stage", "gathering")
                        st.session_state.extracted_symptoms = payload.get("extracted_symptoms", {})
                        st.session_state.red_flags = payload.get("red_flags", [])
                        if payload.get("report_markdown"):
                            st.session_state.report_markdown = payload.get("report_markdown")
                    except Exception as err:
                        error_msg = f"❌ Error communicating with intake agent: {err}"
                        st.error(error_msg)

    # Info & Live Agent State Column
    with col_info:
        st.markdown("### 🧠 Live Agent State")
        st.metric("Intake Status", st.session_state.intake_stage.replace("_", " ").title())

        if st.session_state.red_flags:
            st.markdown("#### 🚨 Flagged Red Flags")
            for flag in st.session_state.red_flags:
                st.warning(flag)

        st.markdown("#### 🩺 Extracted Clinical Slots")
        s = st.session_state.extracted_symptoms
        if s:
            st.markdown(f"**Chief Complaint**: {s.get('primary_complaint') or 'Pending...'}")
            st.markdown(f"**Onset**: {s.get('onset') or 'Pending...'}")
            st.markdown(f"**Duration**: {s.get('duration') or 'Pending...'}")
            st.markdown(f"**Location**: {s.get('location') or 'Pending...'}")
            st.markdown(f"**Severity**: {s.get('severity_1_to_10', 'Pending')}/10" if s.get("severity_1_to_10") else "**Severity**: Pending...")
            st.markdown(f"**Character**: {s.get('character') or 'Pending...'}")
            st.markdown(f"**Triggers / Relief**: {s.get('aggravating_relieving_factors') or 'Pending...'}")
            if s.get("associated_symptoms"):
                st.markdown(f"**Associated**: {', '.join(s.get('associated_symptoms', []))}")
        else:
            st.caption("Slots will populate as you converse with the intake agent.")

        st.divider()
        if st.session_state.report_markdown:
            st.markdown("### 📄 Clinician Handoff Report")
            with st.expander("Preview Handoff Summary", expanded=True):
                st.markdown(st.session_state.report_markdown)

            pdf_buffer = build_pdf_report(st.session_state.report_markdown)
            st.download_button(
                label="📥 Download Clinical Report (PDF)",
                data=pdf_buffer,
                file_name=f"clinical_intake_{st.session_state.patient_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# =========================================================================
# Mode 2: Clinician Admin Dashboard
# =========================================================================
else:
    st.markdown(
        """
        <h1 style='background: linear-gradient(to right, #11998e, #38ef7d); -webkit-background-clip: text; color: transparent;'>
            🩺 Clinician Admin Portal
        </h1>
        <p style='color: #666;'>Confidential Baseline Management & Patient Intake Record Review</p>
        """,
        unsafe_allow_html=True,
    )

    admin_key = st.text_input(
        "Clinician Authentication Key (X-Clinician-Key)",
        value=st.session_state.clinician_key,
        type="password",
    )
    st.session_state.clinician_key = admin_key
    headers = {"X-Clinician-Key": admin_key}

    tab_patients, tab_manage, tab_sessions = st.tabs([
        "📋 Registered Patients",
        "➕ Add / Edit Demographics & Sensitive History",
        "📂 Patient Sessions & Reports",
    ])

    with tab_patients:
        st.markdown("### Patient Directory")
        try:
            res = requests.get(f"{BACKEND_CLINICIAN_URL}/patients", headers=headers, timeout=10)
            if res.status_code == 200:
                patients = res.json()
                for p in patients:
                    with st.expander(f"👤 {p['full_name']} (ID: `{p['patient_id']}`) - Age: {p['age']}, {p['biological_sex']}"):
                        st.markdown(f"**Allergies**: {', '.join(p.get('known_allergies', [])) or 'None'}")
                        st.markdown(f"**Chronic Conditions**: {', '.join(p.get('chronic_conditions', [])) or 'None'}")
                        st.markdown(f"**Current Medications**: {', '.join(p.get('current_medications', [])) or 'None'}")
                        st.markdown(f"🔒 **Sensitive Clinician Notes**: *{p.get('sensitive_notes') or 'None recorded'}*")
                        st.caption(f"Last updated: {p.get('updated_at')}")
            else:
                st.error(f"Unauthorized or server error ({res.status_code}): {res.text}")
        except Exception as e:
            st.error(f"Failed to fetch patient directory: {e}")

    with tab_manage:
        st.markdown("### Register or Update Patient Baseline")
        st.caption("Patients cannot modify these fields. Only clinicians have administrative write access.")
        with st.form("patient_edit_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                pid = st.text_input("Patient ID", value="patient-001")
                name = st.text_input("Full Name", value="Alex Morgan")
            with c2:
                age = st.number_input("Age", min_value=0, max_value=120, value=38)
                sex = st.selectbox("Biological Sex", ["Female", "Male", "Other", "Unknown"], index=0)
            with c3:
                allergies_str = st.text_input("Known Allergies (comma-separated)", value="Penicillin, Sulfa")
                conditions_str = st.text_input("Chronic Conditions (comma-separated)", value="Hypertension")

            meds_str = st.text_input("Current Medications (comma-separated)", value="Lisinopril 10mg daily")
            sensitive_notes = st.text_area(
                "🔒 Confidential Sensitive Notes (Clinician eyes only)",
                value="History of mild post-partum depression. Family history of early myocardial infarction.",
            )

            submitted = st.form_submit_button("💾 Save Patient Record")
            if submitted:
                payload = {
                    "full_name": name,
                    "age": int(age),
                    "biological_sex": sex,
                    "known_allergies": [x.strip() for x in allergies_str.split(",") if x.strip()],
                    "chronic_conditions": [x.strip() for x in conditions_str.split(",") if x.strip()],
                    "current_medications": [x.strip() for x in meds_str.split(",") if x.strip()],
                    "sensitive_notes": sensitive_notes.strip() or None,
                }
                try:
                    save_res = requests.post(
                        f"{BACKEND_CLINICIAN_URL}/patients/{pid}",
                        json=payload,
                        headers=headers,
                        timeout=10,
                    )
                    if save_res.status_code == 200:
                        st.success(f"✅ Successfully saved baseline for patient `{pid}`!")
                    else:
                        st.error(f"Failed to save: {save_res.text}")
                except Exception as e:
                    st.error(f"Save error: {e}")

    with tab_sessions:
        st.markdown("### View Patient Intake Sessions")
        selected_pid = st.text_input("Enter Patient ID to inspect", value=st.session_state.patient_id)
        if st.button("🔍 Fetch Patient Intake Sessions"):
            try:
                s_res = requests.get(
                    f"{BACKEND_CLINICIAN_URL}/patients/{selected_pid}/sessions",
                    headers=headers,
                    timeout=10,
                )
                if s_res.status_code == 200:
                    sessions = s_res.json()
                    if not sessions:
                        st.info(f"No intake sessions recorded yet for patient `{selected_pid}`.")
                    else:
                        for s_data in sessions:
                            with st.expander(f"📁 Session `{s_data['session_id'][:8]}...` | Stage: {s_data.get('intake_stage')} | Updated: {s_data.get('updated_at')}"):
                                st.markdown("#### 🚨 Flagged Red Flags")
                                st.write(s_data.get("red_flags") or "None")

                                st.markdown("#### 🩺 Extracted Symptoms")
                                st.json(s_data.get("extracted_symptoms") or {})

                                if s_data.get("report_markdown"):
                                    st.markdown("#### 📄 Clinician Handoff Report")
                                    st.markdown(s_data["report_markdown"])

                                st.markdown("#### 💬 Full Conversation Transcript")
                                for m in s_data.get("messages", []):
                                    st.markdown(f"**{m.get('role', 'unknown').capitalize()}**: {m.get('content')}")
                else:
                    st.error(f"Error ({s_res.status_code}): {s_res.text}")
            except Exception as e:
                st.error(f"Failed to fetch sessions: {e}")
