from fastapi.testclient import TestClient

from app.main import app


def get_client() -> TestClient:
    return TestClient(app)


def test_session_and_ask_flow() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["learn wudu"]},
        )
        assert session.status_code == 200
        sid = session.json()["session_id"]

        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "What are differences in wudu touching?",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        body = ask.json()
        assert "direct_answer" in body
        assert "evidence_cards" in body
        assert isinstance(body["confidence"], float)


def test_get_session() -> None:
    with get_client() as client:
        created = client.post(
            "/v1/sessions",
            json={"preferred_language": "ar", "level": "intermediate", "goals": ["fiqh"]},
        )
        sid = created.json()["session_id"]
        fetched = client.get(f"/v1/sessions/{sid}")
        assert fetched.status_code == 200
        assert fetched.json()["session_id"] == sid
        assert len(fetched.json()["roadmap"]) > 0


def test_abstain_when_no_grounded_evidence() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["safety check"]},
        )
        sid = session.json()["session_id"]

        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "Explain quantum warp-drive equations for my private legal fatwa case",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        body = ask.json()
        assert body["abstained"] is True
        assert body["safety_notice"] is not None


def test_retrieval_health() -> None:
    with get_client() as client:
        r = client.get("/v1/health/retrieval")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["citations_valid"] is True
        assert body["indexed_passages"] > 0


def test_source_lookup() -> None:
    with get_client() as client:
        r = client.get("/v1/sources/src_quran_49_13")
        assert r.status_code == 200
        assert r.json()["id"] == "src_quran_49_13"


def test_source_list_filtering() -> None:
    with get_client() as client:
        all_sources = client.get("/v1/sources")
        assert all_sources.status_code == 200
        assert all_sources.json()["total"] >= 1

        fiqh_sources = client.get("/v1/sources?topic=fiqh")
        assert fiqh_sources.status_code == 200
        assert fiqh_sources.json()["total"] >= 1

        ar_sources = client.get("/v1/sources?language=ar")
        assert ar_sources.status_code == 200
        assert ar_sources.json()["total"] >= 1


def test_quiz_updates_mastery() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["quiz"]},
        )
        sid = session.json()["session_id"]
        objective_id = session.json()["roadmap"][0]["id"]

        quiz = client.post(
            "/v1/quiz/generate",
            json={"session_id": sid, "objective_id": objective_id, "num_questions": 2},
        )
        assert quiz.status_code == 200
        questions = quiz.json()["questions"]
        answers = {q["id"]: "evidence scholar difference citation" for q in questions}

        grade = client.post(
            "/v1/quiz/grade",
            json={"session_id": sid, "objective_id": objective_id, "answers": answers},
        )
        assert grade.status_code == 200
        assert grade.json()["score"] >= 0.5
        assert grade.json()["updated_mastery"][objective_id] > 0.0
