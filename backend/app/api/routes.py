from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    get_citation_validator,
    get_pipeline,
    get_quiz_service,
    get_retriever,
    get_sessions,
)
from app.schemas import (
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
    validator: CitationValidator = Depends(get_citation_validator),
):
    if not sessions.exists(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    response = pipeline.run(
        session_id=req.session_id,
        question=req.question,
        preferred_language=req.preferred_language,
    )

    citations_ok = validator.validate_response(response)
    if not citations_ok:
        response.abstained = True
        response.safety_notice = "Citation integrity failed. Response downgraded to abstention."
        response.direct_answer = (
            "Unable to provide a reliable answer right now due to citation integrity constraints."
        )

    return response


@router.post("/quiz/generate", response_model=QuizGenerateResponse)
def generate_quiz(req: QuizGenerateRequest, quiz: QuizService = Depends(get_quiz_service)):
    return quiz.generate(objective_id=req.objective_id, num_questions=req.num_questions)


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
):
    items = filter_sources(language=language, topic=topic, q=q)
    return SourceListResponse(items=items, total=len(items))


@router.get("/health/retrieval", response_model=RetrievalHealthResponse)
def retrieval_health(
    retriever: HybridRetriever = Depends(get_retriever),
    validator: CitationValidator = Depends(get_citation_validator),
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

    return RetrievalHealthResponse(
        ok=True,
        citations_valid=validator.validate_response(faux),
        indexed_passages=count_passages_in_db(),
        notes=["Hybrid retriever active", "Citation validator active"],
    )
