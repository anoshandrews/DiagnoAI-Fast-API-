# AGENTS.md

## Repo Snapshot
- Project: DiagnoAI (Stateful LangGraph Symptom Intake Assistant).
- Purpose: Collect structured clinical symptom details (SOCRATES / OPQRST) and generate a clinician handoff report.
- Target Runtime: Free tier of Vercel Serverless Functions (< 30 MB bundle, zero PyTorch/Transformers).
- Database & Persistence: Supabase (PostgreSQL) with in-memory local fallback.

## Architecture
- FastAPI app entry: `backend/main.py`
- Vercel serverless entry: `api/index.py`
- API router: `backend/app/api/v1/router.py`
- Chat endpoint: `backend/app/api/v1/endpoints/chat.py` (wired to LangGraph)
- Voice endpoint: `backend/app/api/v1/endpoints/voice.py` (Groq Whisper Turbo)
- Clinician endpoint: `backend/app/api/v1/endpoints/clinician.py` (Admin CRUD & session review)
- Report endpoint: `backend/app/api/v1/endpoints/report.py`
- LangGraph Workflow: `backend/app/graph/workflow.py`
  - Nodes: `backend/app/graph/nodes.py` (context hydrator, triage guardrails, symptom slot extractor, adaptive questioner, handoff synthesizer)
  - State: `backend/app/graph/state.py` (`AgentState` with Pydantic schemas)
- Storage layer: `backend/app/core/db.py` (Dual-mode: Supabase PostgreSQL + in-memory dev fallback)
- LLM & Audio client: `backend/app/core/llm_client.py` (Groq LLM + Groq Whisper)
- Config: `backend/app/core/config.py`
- Schemas: `backend/app/models/schemas.py`
- Frontend: `frontend/chainlit_app.py` (Modern Chainlit UI: Patient Intake & Clinician Admin)
- Eval runner: `scripts/run_eval.py`

## API Surface
- `GET /health`
- `POST /api/v1/chat`
- `POST /api/v1/voice/transcribe`
- `POST /api/v1/report`
- `POST /api/v1/clinician/patients/{patient_id}`
- `GET /api/v1/clinician/patients`
- `GET /api/v1/clinician/patients/{patient_id}`
- `GET /api/v1/clinician/patients/{patient_id}/sessions`
- `GET /api/v1/clinician/sessions/{session_id}`

## Runtime and Config
- Python 3.11+ with FastAPI & LangGraph.
- Environment variables: `GROQ_API_KEY`, `GROQ_MODEL_NAME`, `GROQ_WHISPER_MODEL`, `CLINICIAN_SECRET_KEY`, `SUPABASE_DB_URL`, `ALLOW_ORIGINS`.
- Resilient fallbacks: deterministic slot extraction, emergency alerts, and question templates if `GROQ_API_KEY` is not present.

## Tests and Evals
- Run test suite: `pytest -p no:langsmith -p no:asyncio tests/backend/app/ -v`
- Run golden-case evals: `python scripts/run_eval.py`
