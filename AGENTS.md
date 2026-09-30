# AGENTS.md

## Repo Snapshot
- Project: DiagnoAI (FastAPI symptom intake assistant).
- Purpose: Collect structured symptom details and generate a clinician handoff report.
- Current status: Modernized safe-scope intake; retrieval/RAG is legacy and not active in API flow.

## Architecture (POC)
- FastAPI app entry: `backend/main.py`
- API router: `backend/app/api/v1/router.py`
- Chat endpoint: `backend/app/api/v1/endpoints/chat.py`
- Report endpoint: `backend/app/api/v1/endpoints/report.py`
- Chat orchestration: `backend/app/services/chat_engine.py`
- Report generation: `backend/app/services/report_generator.py`
- Session store: `backend/app/services/session_store.py` (in-memory)
- LLM client: `backend/app/core/llm_client.py` (Groq)
- Config: `backend/app/core/config.py`
- Schemas: `backend/app/models/schemas.py`
- Eval runner: `scripts/run_eval.py`

## API Surface
- `GET /health`
- `POST /api/v1/chat`
- `POST /api/v1/report`

## Runtime and Config
- Python with FastAPI.
- Environment variables: `GROQ_API_KEY`, `GROQ_MODEL_NAME`, `ALLOW_ORIGINS`.
- If `GROQ_API_KEY` is missing or Groq client fails, LLM calls fall back to deterministic behavior.

## Model and Behavior
- Chat: LLM-driven follow-up questions using `SYSTEM_PROMPT` in `chat_engine.py`.
- Report: LLM JSON output parsed into `MedicalReport` with fallback if LLM unavailable.
- Safety: Explicit “no diagnosis” instructions in prompt and report disclaimer.

## Retrieval / Dynamic RAG Status
- RAG is not active in the API flow.
- `report_generator.retrieve_medical_context()` is stubbed and returns a static message.
- `query_pubmed()` returns an empty list.
- `vectorstore_builder.py` is a standalone utility and not wired into endpoints.

## Tests and Evals
- Tests: `tests/backend/app/` cover chat and report routes, fallback paths, and eval runner behavior.
- Eval runner: `scripts/run_eval.py` uses `evals/fixtures/golden_cases.json` and writes `evals/results/latest.json`.

## Working Notes for Agents
- Assume local in-memory session state; no DB/Redis.
- RAG references in older docs are legacy. Confirm code path before assuming retrieval.
- If implementing retrieval, wire it into `report_generator.generate_medical_report()` or a new pipeline module and add tests + eval fixtures.
