from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_clinician_create_and_get_patient():
    headers = {"X-Clinician-Key": "clinician-secret-key-123"}
    payload = {
        "full_name": "Marcus Aurelius",
        "age": 58,
        "biological_sex": "Male",
        "known_allergies": ["Aspirin"],
        "chronic_conditions": ["Gout", "Insomnia"],
        "current_medications": ["Allopurinol 100mg"],
        "sensitive_notes": "Patient experiences episodic health anxiety.",
    }

    # 1. Create / Update
    res = client.post(
        "/api/v1/clinician/patients/patient-emperor",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == "patient-emperor"
    assert data["full_name"] == "Marcus Aurelius"
    assert data["sensitive_notes"] == "Patient experiences episodic health anxiety."

    # 2. Retrieve
    res_get = client.get(
        "/api/v1/clinician/patients/patient-emperor",
        headers=headers,
    )
    assert res_get.status_code == 200
    assert res_get.json()["age"] == 58


def test_clinician_list_patients():
    headers = {"X-Clinician-Key": "clinician-secret-key-123"}
    res = client.get("/api/v1/clinician/patients", headers=headers)
    assert res.status_code == 200
    patients = res.json()
    assert isinstance(patients, list)
    assert any(p["patient_id"] == "default-patient" for p in patients)


def test_clinician_unauthorized_when_wrong_key():
    headers = {"X-Clinician-Key": "wrong-key-456"}
    res = client.get("/api/v1/clinician/patients", headers=headers)
    assert res.status_code == 401
