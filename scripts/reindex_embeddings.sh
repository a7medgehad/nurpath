#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
source backend/.venv/bin/activate
export PYTHONPATH="$ROOT_DIR/backend"

python - <<'PY'
from app.services.retrieval import HybridRetriever

retriever = HybridRetriever()
diag = retriever.diagnostics()
print(
    "Reindex complete:",
    {
        "profile": diag["profile"],
        "embedding_provider": diag["embedding_provider"],
        "embedding_model_name": diag["embedding_model_name"],
        "embedding_dimension": diag["embedding_dimension"],
        "qdrant_collection_vector_size": diag["qdrant_collection_vector_size"],
        "reindex_required": diag["reindex_required"],
    },
)
PY
