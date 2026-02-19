from fastapi.testclient import TestClient

from app.main import app


def get_client() -> TestClient:
    return TestClient(app)


def test_retrieval_health_reports_runtime_and_validation_counters() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["health"]},
        )
        sid = session.json()["session_id"]
        client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "What are key wudu evidences?",
                "preferred_language": "en",
            },
        )

        health = client.get("/v1/health/retrieval")
        assert health.status_code == 200
        payload = health.json()
        assert payload["profile"] in {"docker-first", "local"}
        assert isinstance(payload["qdrant_connected"], bool)
        assert isinstance(payload["postgres_connected"], bool)
        assert payload["embedding_provider"] in {"hash", "sentence_transformers"}
        assert isinstance(payload["embedding_model_name"], str)
        assert isinstance(payload["embedding_dimension"], int)
        assert isinstance(payload["reranker_enabled"], bool)
        assert isinstance(payload["reranker_provider"], str)
        assert isinstance(payload["reranker_model_name"], str)
        assert isinstance(payload["qdrant_collection_vector_size"], int)
        assert isinstance(payload["reindex_required"], bool)
        assert isinstance(payload["retrieval_avg_top_score"], float)
        assert "validation_pass_count" in payload
        assert "validation_abstain_count" in payload
