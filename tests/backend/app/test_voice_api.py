from io import BytesIO
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_voice_transcribe_endpoint(monkeypatch):
    import backend.app.api.v1.endpoints.voice as voice_endpoint

    def fake_transcribe(file_bytes, filename="audio.wav", model=None):
        assert len(file_bytes) > 0
        return "I have had a mild headache since this morning."

    monkeypatch.setattr(voice_endpoint, "transcribe_audio", fake_transcribe)

    fake_file = BytesIO(b"fake audio data bytes 12345")
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("test_recording.wav", fake_file, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "I have had a mild headache since this morning."
    assert "whisper" in data["model"]


def test_voice_transcribe_empty_file_rejected():
    empty_file = BytesIO(b"")
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("empty.wav", empty_file, "audio/wav")},
    )
    assert response.status_code == 400
