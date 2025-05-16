import pytest
from unittest.mock import patch
from backend.app.services.medical_assistant import summarize_symptom_chat

@patch("backend.app.services.medical_assistant.client")
def test_summarize_symptom_chat(mock_client):
    chat = [{"role": "user", "content": "I've had a headache for two days, it's quite severe."}]
    mock_client.chat.completions.create.return_value.choices = [
        type("obj", (object,), {"message": type("obj", (object,), {"content": "Summary: Severe headache for 2 days"})})
    ]
    
    summary = summarize_symptom_chat(chat)
    assert "Severe headache" in summary

from unittest.mock import patch, MagicMock
from backend.app.services.medical_assistant import retrieve_medical_context

@patch("backend.app.services.medical_assistant.load_or_generate_vectorstore")
def test_retrieve_medical_context_local(mock_load):
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [type("Doc", (object,), {"page_content": "Medical info"})()]
    mock_load.return_value = mock_vectorstore

    context = retrieve_medical_context("headache and fever")
    assert "Medical info" in context

from unittest.mock import patch
from backend.app.services.medical_assistant import query_pubmed

@patch("backend.app.services.medical_assistant.Entrez.esearch")
@patch("backend.app.services.medical_assistant.Entrez.read", return_value={"IdList": []})
def test_query_pubmed_no_results(mock_read, mock_search):
    result = query_pubmed("randomunknownsymptom987")
    assert result == []

from unittest.mock import patch, MagicMock
from backend.app.services.medical_assistant import infer_image_description

@patch("backend.app.services.medical_assistant.Image.open")
@patch("backend.app.services.medical_assistant.blip_processor")
@patch("backend.app.services.medical_assistant.blip_model")
def test_infer_image_description(mock_model, mock_processor, mock_image_open):
    mock_processor.return_value = {"some": "input"}
    mock_model.generate.return_value = torch.tensor([[1, 2, 3]])
    mock_processor.decode.return_value = "This looks like a mild rash."

    result = infer_image_description("dummy_path.jpg")
    assert "mild rash" in result

from unittest.mock import patch
from backend.app.services.medical_assistant import generate_medical_report

@patch("backend.app.services.medical_assistant.client")
def test_generate_medical_report(mock_client):
    mock_client.chat.completions.create.return_value.choices = [
        type("obj", (object,), {"message": type("obj", (object,), {"content": "Report: Visit a doctor."})})
    ]
    report = generate_medical_report("Headache", "Related to migraine")
    assert "Visit a doctor" in report