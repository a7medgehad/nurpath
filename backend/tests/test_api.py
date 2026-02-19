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
        assert "ikhtilaf_analysis" in body
        assert "validation" in body
        assert isinstance(body["confidence"], float)
        assert len(body["evidence_cards"]) >= 1
        assert "source_type" in body["evidence_cards"][0]
        assert "authenticity_level" in body["evidence_cards"][0]
        assert body["evidence_cards"][0]["passage_url"].startswith("http")


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
        assert body["profile"] in {"docker-first", "local"}
        assert isinstance(body["qdrant_connected"], bool)
        assert isinstance(body["postgres_connected"], bool)
        assert body["citations_valid"] is True
        assert body["indexed_passages"] > 0
        assert "retrieval_avg_top_score" in body
        assert "validation_pass_count" in body
        assert "validation_abstain_count" in body
        assert any("Embedding provider=" in note for note in body["notes"])
        assert any("Source types indexed=" in note for note in body["notes"])


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

        quran_sources = client.get("/v1/sources?source_type=quran")
        assert quran_sources.status_code == 200
        assert quran_sources.json()["total"] >= 1

        sahih_sources = client.get("/v1/sources?authenticity_level=sahih")
        assert sahih_sources.status_code == 200
        assert sahih_sources.json()["total"] >= 1

        ar_ui = client.get("/v1/sources?ui_language=ar")
        assert ar_ui.status_code == 200
        items = ar_ui.json()["items"]
        assert len(items) >= 1
        assert any(item["title"] == item["title_ar"] for item in items)


def test_arabic_ask_returns_arabic_display_titles() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "ar", "level": "beginner", "goals": ["الفقه"]},
        )
        sid = session.json()["session_id"]
        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "ما حكم لمس المرأة في الوضوء؟",
                "preferred_language": "ar",
            },
        )
        assert ask.status_code == 200
        cards = ask.json()["evidence_cards"]
        assert len(cards) >= 1
        assert all(card["source_title_ar"] for card in cards)
        assert all(card["passage_url"] for card in cards)


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


def test_langgraph_mermaid_endpoint() -> None:
    with get_client() as client:
        r = client.get("/v1/architecture/langgraph-mermaid")
        assert r.status_code == 200
        mermaid = r.json()["mermaid"]
        assert "graph" in mermaid.lower()
        assert "intent" in mermaid.lower()
        assert "retrieve" in mermaid.lower()


def test_ikhtilaf_metadata_for_wudu_question() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["fiqh"]},
        )
        sid = session.json()["session_id"]

        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "What is the ruling for wudu when touching spouse?",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        payload = ask.json()
        analysis = payload["ikhtilaf_analysis"]
        assert analysis["status"] == "ikhtilaf"
        assert len(analysis["compared_schools"]) >= 2
        assert len(analysis["conflict_pairs"]) >= 1


def test_ikhtilaf_metadata_insufficient_for_non_comparative_topic() -> None:
    with get_client() as client:
        session = client.post(
            "/v1/sessions",
            json={"preferred_language": "en", "level": "beginner", "goals": ["aqidah"]},
        )
        sid = session.json()["session_id"]

        ask = client.post(
            "/v1/ask",
            json={
                "session_id": sid,
                "question": "What is ihsan in hadith jibril?",
                "preferred_language": "en",
            },
        )
        assert ask.status_code == 200
        payload = ask.json()
        analysis = payload["ikhtilaf_analysis"]
        assert analysis["status"] == "insufficient"
