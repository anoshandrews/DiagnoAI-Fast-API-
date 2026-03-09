# DiagnoAI

DiagnoAI is a FastAPI-based symptom intake assistant that collects structured patient information and turns it into a clinician handoff summary. The current codebase has been reset toward a safer product scope: intake, escalation cues, and report generation rather than diagnosis.

## Current Status

- Typed FastAPI backend
- Per-session in-memory chat state for local development
- Structured report generation with deterministic fallback mode
- Route and service tests aligned to the current app layout
- Modernization roadmap in [documents/modernization_plan.md](documents/modernization_plan.md)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,frontend]"
cp .env.example .env
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API docs.

## Eval Workflow

Run the lightweight golden-case eval suite:

```bash
python scripts/run_eval.py
```

This writes a JSON report to `evals/results/latest.json`.

## Docker

Build and run the API container:

```bash
docker build -t diagnoai .
docker run --rm -p 8000:8000 --env-file .env diagnoai
```

## API Surface

- `GET /health`
- `POST /api/v1/chat`
- `POST /api/v1/report`

## Notes

- If `GROQ_API_KEY` is missing, chat and report generation fall back to deterministic local behavior.
- The old RAG and image-analysis prototype code is still in the repo as legacy material, but it is no longer part of the active API path.
- This repository previously contained committed credentials. Rotate all previously used keys before deploying anything.
