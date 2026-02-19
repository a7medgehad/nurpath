# NurPath

NurPath is an open-source Arabic-English Islamic learning tutor built with agentic AI, RAG, and vector search.

It focuses on an unmet need: **Ikhtilaf-aware pedagogy**. Instead of a single flattened answer, NurPath teaches with evidence, shows major scholarly positions, explains uncertainty, and recommends the next learning step.

## Core Principles

- Every generated claim must map to at least one citation span.
- Evidence is first-class: Arabic source text + bilingual explanation.
- Disagreement is represented, not hidden.
- Sensitive personal-fatwa questions trigger educational framing and scholar escalation guidance.

## Monorepo Structure

- `backend/` FastAPI API, multi-agent orchestration, retrieval, and citation validation
- `frontend/` Next.js bilingual web app (RTL/LTR aware)
- `docs/` architecture, data policy, and GitHub growth playbook
- `eval/` evaluation dataset and scripts
- `.github/` CI and collaboration templates

## APIs (MVP)

- `POST /v1/sessions`
- `GET /v1/sessions/{session_id}`
- `POST /v1/ask`
- `POST /v1/quiz/generate`
- `POST /v1/quiz/grade`
- `GET /v1/sources` (with optional `language`, `topic`, `q` filters)
- `GET /v1/sources/{id}`
- `GET /v1/health/retrieval`

## Quick Start

### 1) Infrastructure (Qdrant + Postgres)

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

The frontend expects backend at `http://localhost:8000`.

## Open-Source / Free Tooling

- FastAPI + Pydantic + SQLModel
- LangGraph for agent orchestration
- Qdrant for vector search
- PostgreSQL/SQLite metadata storage
- Next.js + Tailwind CSS
- Prometheus + OpenTelemetry ready instrumentation

## Evaluation Targets

- Citation integrity: no dangling citations
- Hallucination control: abstain on unsupported prompts
- Bilingual consistency: Arabic/English semantic parity
- Ikhtilaf fidelity: multiple valid positions where applicable

## Safety Statement

NurPath is educational software. It does not replace qualified scholarship or legal/religious counsel.

## License

MIT
