from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_nurpath.db"
os.environ["QDRANT_LOCAL_MODE"] = "true"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["EMBEDDING_MODEL_NAME"] = "deterministic-hash"
os.environ["EMBEDDING_DIMENSION"] = "384"
os.environ["RERANKER_ENABLED"] = "true"
os.environ["RERANKER_PROVIDER"] = "token_overlap"
os.environ["RERANKER_MODEL_NAME"] = "token-overlap-reranker"


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    db = Path("test_nurpath.db")
    if db.exists():
        db.unlink()


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    db = Path("test_nurpath.db")
    if db.exists():
        db.unlink()
