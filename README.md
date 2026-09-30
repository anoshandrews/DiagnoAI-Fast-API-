# ⚕️ DiagnoAI: Stateful LangGraph Clinical Intake Assistant

A lightweight, production-ready, showcase-oriented clinical symptom intake assistant built with **FastAPI**, **LangGraph**, and **Groq**. 

Engineered specifically to run on the **Free Tier of Vercel** (< 30 MB bundle size, zero PyTorch/Transformers dependencies) and persist multi-tenant patient records and agent states in **Supabase (PostgreSQL)**.

---

## 🌟 Key Architecture & Capabilities

### 1. Stateful LangGraph Clinical Intake Agent
Instead of a simple stateless prompt-response wrapper, DiagnoAI orchestrates a state machine using LangGraph:
* **Context Hydrator**: Loads patient baseline records (age, biological sex, allergies, active conditions, medications, and sensitive notes) entered by the clinician.
* **Triage & Safety Guardrail**: Evaluates acute red flags (crushing chest pain, FAST stroke symptoms, respiratory distress, anaphylaxis).
* **Emergency Escalation**: Halts routine intake immediately upon detecting critical red flags and provides directives to contact emergency services (911/ER).
* **Symptom Slot Extractor**: Uses structured entity extraction to map patient input to clinical **SOCRATES / OPQRST** dimensions (onset, duration, location, severity 1–10, quality, aggravating/relieving factors).
* **Adaptive Clinical Questioner**: Generates focused, empathetic follow-up questions one at a time, targeted at missing clinical dimensions without overwhelming the patient.
* **Clinician Handoff Synthesizer**: Generates a standardized SBAR/SOAP intake report for clinician review with diagnostic avenues and disclaimer.

### 2. Role-Based Access: Clinician Admin vs. Patient
* **Patient Portal**: The patient can ONLY enter symptoms and interact with the conversational agent (via text or voice). They cannot alter their medical baseline or EHR data.
* **Clinician Admin Portal**: Secure endpoint protected by `X-Clinician-Key`. Clinicians can:
  * Register and edit patient demographics, chronic conditions, medications, allergies, and confidential notes.
  * Access any patient by `patient_id`.
  * Inspect all historical intake sessions, transcripts, extracted symptom slots, and generated handoff summaries.

### 3. Audio & Voice Input via Groq Whisper Turbo
* Audio input endpoint (`/api/v1/voice/transcribe`) connects to `whisper-large-v3-turbo` on Groq Cloud.
* Transcribes audio recordings in **< 400ms** with **0 MB local weights**, avoiding heavy PyTorch dependencies.

### 4. Persistence: Supabase (PostgreSQL) vs SQLite
* **Why not SQLite?** Vercel serverless environments are stateless and ephemeral. Any local SQLite `.db` file is wiped on cold starts and cannot be shared across lambdas.
* **Why Supabase?** Provides managed PostgreSQL with native connection pooling (`Supavisor` on port 6543) designed for serverless functions, plus Row-Level Security (RLS) and a generous free tier.
* **Local Fallback**: If `SUPABASE_DB_URL` is omitted, DiagnoAI gracefully falls back to an in-memory thread-safe repository with pre-seeded demo records for local development.

### 5. Why Vector RAG is NOT Used for Patient History
* Individual patient medical records (demographics, active medications, allergies, chronic conditions) are compact (< 10 KB).
* Injecting structured medical baselines directly into the agent context provides **100% deterministic recall**.
* Semantic Vector RAG chunks text and risks missing critical clinical warnings (e.g. drug allergies or prior cardiac events) due to cosine-similarity thresholds.

---

## 📐 LangGraph Workflow

```text
[START]
   │
   ▼
[Hydrate Context Node] ──> (Loads Clinician Baseline from Supabase)
   │
   ▼
[Triage Guardrail Node]
   ├── [Red Flag Detected] ──> [Emergency Escalation Node] ──> [END (Alert 911/ER)]
   │
   └── [Safe / Gathering]
           │
           ▼
   [Symptom Extractor Node] ──> (Extracts OPQRST / Severity 1-10)
           │
           ├── [Slots Incomplete] ──> [Adaptive Questioner Node] ──> [END (Await Patient)]
           │
           └── [Intake Complete]  ──> [Handoff Synthesizer Node]  ──> [END (Report Ready)]
```

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/anoshandrews/DiagnoAI-Fast-API-.git
cd DiagnoAI-Fast-API-
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure Environment (`.env`)
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL_NAME=llama-3.3-70b-versatile
GROQ_WHISPER_MODEL=whisper-large-v3-turbo
CLINICIAN_SECRET_KEY=clinician-secret-key-123
# Optional: Supabase PostgreSQL connection string for cloud persistence
SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:6543/postgres?sslmode=require
```

### 3. Launch Backend
```bash
uvicorn backend.main:app --reload --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### 4. Launch Sleek Chainlit Showcase UI
```bash
chainlit run frontend/chainlit_app.py --port 8501
```
Open `http://localhost:8501` to access the modern chat interface with live LangGraph reasoning steps, Groq Whisper voice input, and clinician admin tools.

---

## ⚡ Deploying to Vercel (Free Tier)

This repository is optimized for Vercel Serverless Functions out of the box:
* `vercel.json`: Rewrites all traffic to `api/index.py`.
* `api/index.py`: Serverless ASGI entrypoint mounting `backend.main:app`.
* `requirements.txt`: Lightweight (< 30 MB uncompressed, zero torch).

### Deploy via Vercel CLI
```bash
npm install -g vercel
vercel
```
Set `GROQ_API_KEY` and `SUPABASE_DB_URL` in the Vercel Project Settings under **Environment Variables**.

---

## 🧪 Testing and Evaluations

Run the backend test suite:
```bash
pytest -p no:langsmith -p no:asyncio tests/backend/app/ -v
```

Run golden-case clinical evaluation:
```bash
python scripts/run_eval.py
```

---

## 📡 API Surface

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Healthcheck and service version | Public |
| `POST` | `/api/v1/chat` | Multi-turn LangGraph intake conversation | Patient / Public |
| `POST` | `/api/v1/voice/transcribe` | High-speed Groq Whisper audio transcription | Patient / Public |
| `POST` | `/api/v1/report` | On-demand handoff report generation | Public |
| `POST` | `/api/v1/clinician/patients/{id}` | Register or update patient EHR baseline | Clinician Admin |
| `GET` | `/api/v1/clinician/patients` | List all registered patients | Clinician Admin |
| `GET` | `/api/v1/clinician/patients/{id}` | Get patient record + confidential notes | Clinician Admin |
| `GET` | `/api/v1/clinician/patients/{id}/sessions` | List intake sessions and handoff reports | Clinician Admin |
| `GET` | `/api/v1/clinician/sessions/{session_id}` | View full transcript and extracted slots | Clinician Admin |
