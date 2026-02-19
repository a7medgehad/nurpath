from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.api.deps import (
    get_answer_validator,
    get_citation_validator,
    get_pipeline,
    get_quiz_service,
    get_retriever,
    get_sessions,
)
from app.core.db import get_db_session
from app.schemas import (
    ArchitectureDiagramResponse,
    AskRequest,
    AskResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizGradeRequest,
    QuizGradeResponse,
    RetrievalHealthResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SourceDocument,
    SourceListResponse,
)
from app.services.catalog import count_passages_in_db, filter_sources, load_catalog
from app.services.citation import CitationValidator
from app.services.learning import SessionManager
from app.services.quiz import QuizService
from app.services.retrieval import HybridRetriever
from app.services.validation import AnswerValidationService

router = APIRouter(prefix="/v1", tags=["nurpath"])


@router.post("/sessions", response_model=SessionCreateResponse)
def create_session(req: SessionCreateRequest, sessions: SessionManager = Depends(get_sessions)):
    return sessions.create(req)


@router.get("/sessions/{session_id}", response_model=SessionCreateResponse)
def get_session(session_id: str, sessions: SessionManager = Depends(get_sessions)):
    if not sessions.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionCreateResponse(
        session_id=session_id,
        roadmap=sessions.get_roadmap(session_id),
        lesson_path=sessions.get_lesson_path(session_id),
    )


@router.post("/ask", response_model=AskResponse)
def ask_question(
    req: AskRequest,
    sessions: SessionManager = Depends(get_sessions),
    pipeline=Depends(get_pipeline),
    validator: AnswerValidationService = Depends(get_answer_validator),
):
    if not sessions.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    response = pipeline.run(
        session_id=req.session_id,
        question=req.question,
        preferred_language=req.preferred_language,
    )

    return validator.apply(response=response, preferred_language=req.preferred_language)


@router.post("/quiz/generate", response_model=QuizGenerateResponse)
def generate_quiz(req: QuizGenerateRequest, quiz: QuizService = Depends(get_quiz_service)):
    return quiz.generate(
        objective_id=req.objective_id,
        num_questions=req.num_questions,
        preferred_language=req.preferred_language,
    )


@router.post("/quiz/grade", response_model=QuizGradeResponse)
def grade_quiz(
    req: QuizGradeRequest,
    sessions: SessionManager = Depends(get_sessions),
    quiz: QuizService = Depends(get_quiz_service),
):
    if not sessions.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    return quiz.grade(session_id=req.session_id, objective_id=req.objective_id, answers=req.answers)


@router.get("/sources/{source_id}", response_model=SourceDocument)
def get_source(source_id: str):
    catalog = load_catalog()
    source = catalog.sources.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.get("/sources", response_model=SourceListResponse)
def list_sources(
    language: str | None = None,
    topic: str | None = None,
    q: str | None = None,
    source_type: str | None = None,
    authenticity_level: str | None = None,
    ui_language: str = "en",
):
    items = filter_sources(
        language=language,
        topic=topic,
        q=q,
        source_type=source_type,
        authenticity_level=authenticity_level,
    )
    response_items = items
    if ui_language == "ar":
        response_items = [
            item.model_copy(
                update={
                    "title": item.title_ar,
                    "author": item.author_ar,
                    "citation_policy": item.citation_policy_ar,
                }
            )
            for item in items
        ]
    return SourceListResponse(items=response_items, total=len(response_items))


@router.get("/health/retrieval", response_model=RetrievalHealthResponse)
def retrieval_health(
    retriever: HybridRetriever = Depends(get_retriever),
    validator: CitationValidator = Depends(get_citation_validator),
    answer_validator: AnswerValidationService = Depends(get_answer_validator),
):
    test = retriever.retrieve("What are key points in wudu differences?")
    faux = AskResponse(
        direct_answer="health check",
        evidence_cards=test.evidence_cards,
        opinion_comparison=[],
        confidence=0.7,
        next_lesson=None,
        safety_notice=None,
        abstained=False,
    )

    diagnostics = retriever.diagnostics()
    postgres_connected = False
    try:
        with get_db_session() as db:
            db.exec(text("SELECT 1")).first()
        postgres_connected = True
    except Exception:
        postgres_connected = False

    stats = answer_validator.stats_snapshot()
    qdrant_connected = bool(diagnostics["qdrant_connected"])
    ok = qdrant_connected and postgres_connected
    return RetrievalHealthResponse(
        ok=ok,
        profile=str(diagnostics["profile"]),
        qdrant_connected=qdrant_connected,
        postgres_connected=postgres_connected,
        embedding_provider=str(diagnostics["embedding_provider"]),
        embedding_model_name=str(diagnostics["embedding_model_name"]),
        embedding_dimension=int(diagnostics["embedding_dimension"]),
        qdrant_collection_vector_size=int(diagnostics["qdrant_collection_vector_size"]),
        reindex_required=bool(diagnostics["reindex_required"]),
        citations_valid=validator.validate_response(faux),
        indexed_passages=count_passages_in_db(),
        retrieval_avg_top_score=float(diagnostics["retrieval_avg_top_score"]),
        validation_pass_count=stats.pass_count,
        validation_abstain_count=stats.abstain_count,
        notes=[
            "Hybrid retriever active (vector + lexical)",
            f"Embedding provider={diagnostics['embedding_provider']}",
            f"Embedding model={diagnostics['embedding_model_name']}",
            f"Embedding dim={diagnostics['embedding_dimension']}",
            f"Retrieval observations={diagnostics['retrieval_observations']}",
            f"Expansion fallback uses={diagnostics['expansion_uses']}",
            f"Sources count={len(retriever.catalog.sources)}",
            "Source types indexed="
            + ", ".join(
                sorted({source.source_type for source in retriever.catalog.sources.values()})
            ),
            "Authenticity levels indexed="
            + ", ".join(
                sorted(
                    {
                        source.authenticity_level
                        for source in retriever.catalog.sources.values()
                    }
                )
            ),
            "Citation validator active",
            "Answer validation gate active",
        ],
    )


@router.get("/architecture/langgraph-mermaid", response_model=ArchitectureDiagramResponse)
def langgraph_mermaid(pipeline=Depends(get_pipeline)):
    return ArchitectureDiagramResponse(mermaid=pipeline.mermaid())
