# DiagnoAI Evaluation Report (POC)
Date: 2026-03-15

## Scope
This evaluation covers the current FastAPI backend behavior for chat intake, report generation, and the status of Dynamic RAG. The intent is to provide a concise POC-level assessment for a mid-level AI/ML engineer.

## System Summary
- Chat flow: `POST /api/v1/chat` stores per-session history in memory and calls `handle_user_prompt()`.
- Report flow: `POST /api/v1/report` converts chat history into a structured `MedicalReport` plus a Markdown rendering.
- LLM provider: Groq client; fallback behavior when missing key or client failure.

## Model Behavior (Current)
- Chat: Uses a system prompt to ask one focused follow-up question at a time. No diagnosis or treatment advice.
- Report: Uses LLM to emit JSON for `MedicalReport`. If LLM fails or JSON invalid, it falls back to a deterministic report that includes red-flag guidance and a disclaimer.

## Dynamic RAG Status (Key Finding)
- Dynamic RAG is not active in the API path.
- `retrieve_medical_context()` is stubbed and returns a static message.
- `query_pubmed()` returns an empty list.
- `vectorstore_builder.py` is a standalone utility that is not called by any endpoint or service.
Implication: The current model outputs are not influenced by external knowledge or document retrieval.

## API and Evals (Observed)
- Golden-case evals are executed via `scripts/run_eval.py`.
- Latest recorded results: 18/18 checks passing across 3 cases in `evals/results/latest.json`.
- Checks validate: summary coverage, disclaimer presence, timeline, red flags, recommended steps, and urgent language where required.

## Gaps and Risks
- Retrieval pipeline is incomplete; no embeddings, indexing, or query-time retrieval integrated into chat or report flows.
- In-memory session store is not durable or scalable.
- LLM JSON parsing relies on best-effort cleanup and may fail on malformed outputs.

## Recommendations (POC Next Steps)
1. Implement a minimal retrieval pipeline: chunking, embeddings, and a vector store with metadata.
2. Wire retrieval into report generation, including citations or provenance fields.
3. Add tests and evals that assert retrieval usage and measure red-flag recall and factual grounding.
4. Replace in-memory session storage with Redis or a database for multi-instance deployments.
