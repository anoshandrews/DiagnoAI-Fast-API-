import streamlit as st
import requests
import logging
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ========== Streamlit page configuration ==========
st.set_page_config(
    page_title='DiagnoAI',
    page_icon='⚕️',
    layout='centered'
)

# ========== FastAPI Backend URL ==========
BACKEND_CHAT_URL = "http://localhost:8000/api/v1/chat"
BACKEND_REPORT_URL = "http://localhost:8000/api/v1/report"

# ========== Initialize session chat history ==========
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = "streamlit-session"

# ========== Function to send chat to backend ==========
def send_message_to_backend(message):
    logging.info(f"Sending message to backend: '{message}'")
    try:
        response = requests.post(
            BACKEND_CHAT_URL,
            json={"user_text": message, "session_id": st.session_state.session_id},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        reply = payload.get("reply")
        st.session_state.session_id = payload.get("session_id", st.session_state.session_id)
        logging.info(f"Backend response: '{reply}'")
        return reply if reply is not None else "No response from backend."
    except requests.exceptions.RequestException as e:
        error_message = f"❌ Failed to connect to backend: {e}"
        logging.error(error_message)
        st.error(error_message)
        return f"❌ Failed to connect to backend: {e}"
    except ValueError:
        error_message = "❌ Invalid JSON response from backend."
        logging.error(error_message)
        st.error(error_message)
        return error_message

# ========== Function to generate report ==========
def generate_report():
    logging.info("Generating medical report.")
    try:
        response = requests.post(
            BACKEND_REPORT_URL,
            json={"chat_history": st.session_state.chat_history},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        logging.info("Medical report generated successfully.")
        return payload.get("markdown", "No report content returned.")
    except Exception as e:
        error_message = f"❌ Error generating report: {e}"
        logging.error(error_message)
        st.error(error_message)
        return "Failed to generate report."


# ========== Title Layout ==========
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(
        """
        <h1 style='
            background: linear-gradient(to right, #FF3C38, #FFB347);
            -webkit-background-clip: text;
            color: transparent;
            font-size: 6em;
            text-align: center;
            padding-bottom: 0.5em;
        '>⚕️DiagnoAI</h1>
        """,
        unsafe_allow_html=True
    )
with col2:
    st.write('')
    st.write('')
    st.write('')
    st.write('')
    if col2.button("Create Report", key='report_button'):
        try:
            with st.spinner("Generating report..."):
                report_content = generate_report()
                if report_content:
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=A4,
                                             rightMargin=72, leftMargin=72,
                                             topMargin=72, bottomMargin=72)

                    styles = getSampleStyleSheet()
                    story = []

                    for line in report_content.split('\n'):
                        while '**' in line:
                            line = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
                        para = Paragraph(line, styles["Normal"])
                        story.append(para)
                        story.append(Spacer(1, 0.08 * inch))

                    doc.build(story)
                    buffer.seek(0)

                    st.download_button(
                        label="📄Download Report",
                        data=buffer,
                        file_name="diagnostic_report.pdf",
                        mime="application/pdf"
                    )
                    st.success("✅ Report generated and ready to download!")
        except Exception as e:
            error_message = f"❌ Error during report creation/download: {e}"
            logging.error(error_message)
            st.error(error_message)


for message in st.session_state.chat_history:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# ========== Chat input ==========
user_input = st.chat_input(
    "Tell me about your symptoms...",
    key='user_prompt',
)

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    logging.info(f"User message: '{user_input}'")

    assistant_reply = send_message_to_backend(user_input)

    st.chat_message("assistant").markdown(assistant_reply)
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})
