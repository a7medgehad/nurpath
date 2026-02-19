# NurPath

NurPath is an open-source Arabic-English Islamic learning tutor built with agentic AI, LangGraph, hybrid RAG, and vector search.

It is designed for **Ikhtilaf-aware pedagogy**: answers include evidence, compare valid scholarly perspectives, and suggest the next learning step.

## Why This Project

Most assistants flatten differences into a single answer. NurPath keeps disagreement explicit and traceable while enforcing citation integrity and safety constraints.

## Key Features

- Multi-agent tutoring flow (Intent -> Retrieve -> Compare -> Tutor -> Safety)
- Hybrid retrieval (Qdrant vector search + lexical ranking fusion)
- Embedding provider abstraction (offline hash default, optional sentence-transformers)
- Structured ikhtilaf detector (consensus/disagreement status + conflict pair metadata)
- Citation-span validation guard
- Session roadmap + quiz generation + mastery updates
- Arabic/English UI with RTL/LTR support

## Repository Layout

- `backend/` FastAPI API, LangGraph orchestration, retrieval, and policy guards
- `frontend/` Next.js app for tutoring, source exploration, and quiz interaction
- `docs/` technical architecture and policies
- `data/` curated sample corpus + allowlist metadata
- `eval/` evaluation dataset and script
- `scripts/` smoke, E2E, and architecture generation helpers

## API Endpoints

- `POST /v1/sessions`
- `GET /v1/sessions/{session_id}`
- `POST /v1/ask`
- `POST /v1/quiz/generate`
- `POST /v1/quiz/grade`
- `GET /v1/sources`
- `GET /v1/sources/{id}`
- `GET /v1/health/retrieval`
- `GET /v1/architecture/langgraph-mermaid`

`POST /v1/ask` includes:
- `direct_answer`
- `evidence_cards[]`
- `opinion_comparison[]`
- `ikhtilaf_analysis` (`ikhtilaf` | `consensus` | `insufficient`)
- `confidence`
- `safety_notice`
- `abstained`

## Quick Start

### 1) Optional infrastructure

```bash
docker compose up -d qdrant postgres
```

### 2) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend expects backend at `http://localhost:8000`.

## Quality and Test Commands

### Backend

```bash
make backend-lint
make backend-cov
```

### Frontend

```bash
cd frontend && npm run lint && npm run typecheck && npm run build
```

### API smoke test

```bash
make smoke
```

### Full browser E2E test

```bash
make e2e
```

## Configuration

Environment variables are documented in `.env.example`.

Important retrieval-related keys:

- `QDRANT_URL`
- `QDRANT_COLLECTION`
- `QDRANT_LOCAL_MODE`
- `EMBEDDING_PROVIDER` (`hash` or `sentence_transformers`)
- `EMBEDDING_MODEL_NAME`
- `EMBEDDING_DIMENSION`

## Architecture

- Technical architecture: `docs/architecture.md`
- Generated LangGraph mermaid file: `docs/langgraph_agent_flow.mmd`

Regenerate mermaid from live graph:

```bash
make generate-mermaid
```

## Safety Statement

NurPath is educational software. It does not replace qualified scholarship or legal/religious counsel.

## License

MIT
