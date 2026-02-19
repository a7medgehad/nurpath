# NurPath Architecture

## High-Level Components

1. Frontend (Next.js)
2. Backend API (FastAPI)
3. Agent Orchestration (LangGraph)
4. Retrieval Layer (Qdrant + lexical fallback)
5. Metadata Store (SQLite/PostgreSQL)
6. Evaluation and Safety Gates

## Request Flow (`POST /v1/ask`)

1. Intent classification (aqidah, fiqh, akhlaq, history, language learning)
2. Hybrid retrieval (dense + lexical)
3. Opinion comparison extraction
4. Tutor response synthesis
5. Safety guard checks (abstain/escalate if needed)
6. Citation-span validation

## Data Contracts

- Every `evidence_card` contains source IDs and exact spans.
- `confidence < threshold` must produce abstain behavior.
- `opinion_comparison` is empty only when no reliable divergence exists.

## Deployment

- Local: Docker Compose for Qdrant/Postgres + direct app processes
- Cloud: containerized frontend and backend; managed free-tier vector and postgres where possible
