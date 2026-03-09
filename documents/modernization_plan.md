# DiagnoAI Modernization Plan

## Goal
Turn the repo from a 2025 prototype into a 2026-quality side project with a clean backend, safe product framing, reproducible setup, and measurable model quality.

## Phase 0: Security and Repo Hygiene
- Rotate every committed API key immediately.
- Remove tracked secrets, logs, bytecode, model binaries, and vectorstore artifacts from git history.
- Add `.env.example`, `.gitignore`, and dependency metadata in `pyproject.toml`.

## Phase 1: Backend Stabilization
- Keep FastAPI as the backend boundary.
- Use typed request and response models everywhere.
- Replace shared global chat state with per-session storage.
- Add health checks, predictable error handling, and route tests.

## Phase 2: AI Layer Upgrade
- Keep the assistant focused on symptom intake and clinician handoff.
- Use structured outputs instead of free-form reports.
- Add red-flag escalation logic and disclaimer-safe report generation.
- Reintroduce retrieval only after establishing a reliable baseline without it.

## Phase 3: Retrieval and Evals
- Build a document ingestion pipeline with chunking, metadata, and reproducible indexing.
- Add golden conversations and report-eval fixtures from the existing CSV assets.
- Track completeness, safety, red-flag recall, and report-format validity.
- Keep a lightweight CLI eval runner in-repo so model changes are measurable before deploys.

## Phase 4: Product and Deployment
- Decide between a polished Streamlit client or a Next.js frontend.
- Add Docker, CI, and deployment configuration.
- Add observability for prompt version, model version, latency, and failures.
- Add CI gates for tests plus golden-case evals.

## Recommended End State
- FastAPI backend
- Typed config with Pydantic settings
- Structured LLM outputs
- Session persistence in Redis or Postgres
- Postgres plus `pgvector` or Qdrant if retrieval proves useful
- CI with tests and linting
- Public demo with a narrow, safe scope
