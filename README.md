# NurPath

NurPath is an open-source Arabic-English Islamic learning tutor built with agentic AI, LangGraph, hybrid RAG, and vector search.

It is designed for **Ikhtilaf-aware pedagogy**: answers include evidence, compare valid scholarly perspectives, and suggest the next learning step.

## Why This Project

Most assistants flatten differences into a single answer. NurPath keeps disagreement explicit and traceable while enforcing citation integrity and safety constraints.

## Key Features

- Multi-agent tutoring flow (Intent -> Retrieve -> Compare -> Tutor -> Safety)
- Hybrid retrieval (Qdrant vector search + lexical ranking fusion)
- Retrieval resilience (query expansion fallback + source-diversity selection)
- Embedding provider abstraction (offline hash default, optional sentence-transformers)
- Structured ikhtilaf detector (consensus/disagreement status + conflict pair metadata)
- Curated Quran + Sunnah + معتبر fiqh core corpus with authenticity metadata
- Open/PD allowlist enforcement in catalog loading
- Strict Arabic-mode rendering (no visible Latin text on Arabic page content)
- Passage-level evidence deep links (`passage_url`) in evidence cards
- Pre-display validation gate (citation integrity + grounding + faithfulness)
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
- `validation`:
  - `passed`
  - `citation_integrity` (`passed`, `coverage`)
  - `grounding` (`score`, `threshold`, `passed`)
  - `faithfulness` (`score`, `threshold`, `passed`)
  - `decision_reason`

`GET /v1/sources` supports filters:
- `language`
- `topic`
- `q`
- `source_type` (`quran` | `hadith` | `fiqh`)
- `authenticity_level`
- `ui_language` (`ar` | `en`)

## Quick Start

### 1) Docker-first infrastructure

```bash
docker compose up -d qdrant postgres
```

If your local PostgreSQL volume was initialized with different credentials, reset it:

```bash
docker compose down -v
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

### 4) End-to-end browser test

```bash
./scripts/run_e2e.sh
```

This script runs backend/frontend in a deterministic local test profile, then executes Playwright.

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
- `GROUNDING_THRESHOLD`
- `FAITHFULNESS_THRESHOLD`
- `WEAK_RETRIEVAL_THRESHOLD`

### Runtime Profiles

| Profile | Use case | Key envs |
|---|---|---|
| `docker-first` (default) | production-like local run with Docker services | `QDRANT_LOCAL_MODE=false`, `DATABASE_URL=postgresql+psycopg://...` |
| `local` (fallback) | offline dev/testing | `QDRANT_LOCAL_MODE=true`, `DATABASE_URL=sqlite:///...` |

## Validation Gate

Gate order on `POST /v1/ask`:
1. Citation integrity
2. Grounding score
3. Faithfulness score
4. Safety policy
5. Final decision (`validation.passed`)

If validation fails, response is downgraded to abstention with actionable guidance.

## Architecture

- Technical architecture: `docs/architecture.md`
- Generated LangGraph mermaid file: `docs/langgraph_agent_flow.mmd`

Regenerate mermaid from live graph:

```bash
make generate-mermaid
```

## Troubleshooting

- **No answer appears / frequent abstains**:
  - Check `GET /v1/health/retrieval` for `qdrant_connected`, `postgres_connected`, and `retrieval_avg_top_score`.
  - Lower `GROUNDING_THRESHOLD` / `FAITHFULNESS_THRESHOLD` slightly only after reviewing eval output.
  - Confirm corpus passages include `passage_url` and valid `reference`.
- **Evidence link opens only source root**:
  - Ensure evidence card uses `passage_url` (not `source_url`).
  - Re-index after corpus updates.

## Safety Statement

NurPath is educational software. It does not replace qualified scholarship or legal/religious counsel.

## License

MIT
