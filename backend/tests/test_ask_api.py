from fastapi.testclient import TestClient

from app.main import app


def get_client() -> TestClient:
    return TestClient(app)


def test_ask_api_returns_validation_payload_on_grounded_query() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["learn fiqh"]},
        )
        sid = session.json()["session_id"]
        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "What are wudu evidences for prayer purity?",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        body = ask.json()
        assert "validation" in body
        assert "citation_integrity" in body["validation"]
        assert isinstance(body["validation"]["grounding"]["score"], float)


def test_ask_api_abstains_for_unsupported_question() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["safety"]},
        )
        sid = session.json()["session_id"]
        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "Provide undiscovered interstellar legal formulas for fatwa",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        body = ask.json()
        assert body["abstained"] is True
        assert body["validation"]["passed"] is False


def test_ask_api_sensitive_prompt_keeps_escalation_notice() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["safety"]},
        )
        sid = session.json()["session_id"]
        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "I need a personal fatwa for my divorce case",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        body = ask.json()
        assert body["abstained"] is True
        assert body["safety_notice"] is not None
