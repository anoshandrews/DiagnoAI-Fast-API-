import streamlit as st
import requests
import sys
from pathlib import Path
from io import BytesIO
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from backend.app.services.report_generator import (
    summarize_symptom_chat,
    retrieve_medical_context,
    generate_medical_report,
    download_medical_report_pdf,
)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch


from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / 'backend'))  # add backend to path

# from app.services.image_captioning import run_inference

# ========== Streamlit page configuration ==========
st.set_page_config(
    page_title='DiagnoAI',
    page_icon='⚕️',
    layout='centered'
)

# ========== FastAPI Backend URL ==========
BACKEND_URL = "http://localhost:8000/api/v1/chat"  # Adjust if deployed elsewhere

# ========== Initialize session chat history ==========
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ========== Function to send chat to backend ==========
def send_message_to_backend(message):
    """Sends the user's message to the backend and returns the response."""
    logging.info(f"Sending message to backend: '{message}'")
    try:
        response = requests.post(
            BACKEND_URL,
            data={"user_text": message},
            files={}  # you can add image here if needed
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        reply = response.json().get("reply")  # Safely get the reply
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
    """Generate a report based on the chat history."""
    logging.info("Generating medical report.")
    try:
        symptom_summary = summarize_symptom_chat(st.session_state.chat_history)
        medical_context = retrieve_medical_context(symptom_summary)
        medical_report = generate_medical_report(symptom_summary, medical_context)
        logging.info("Medical report generated successfully.")
        return medical_report
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
    accept_file=True,                                      #for taking in images as well
    file_type=['jpg','png','jpeg'],
)

if user_input:
    user_text = user_input.get("text", "")
    user_image = user_input.get("files", [])

    if user_text:
        # Show user input
        st.chat_message("user").markdown(user_text)
        st.session_state.chat_history.append({"role": "user", "content": user_text})
        logging.info(f"User message: '{user_text}'")

        # Call backend API
        assistant_reply = send_message_to_backend(user_text)

        # Show assistant response
        st.chat_message("assistant").markdown(assistant_reply)
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})

    if user_image:
        for file in user_image:
            st.chat_message("user").markdown(f"Uploaded image: `{file.name}`")
            st.image(file)
            logging.info(f"User uploaded image: {file.name}")
            # Steps to be added to pass the image to CNN:Resnet-50