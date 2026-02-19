from functools import lru_cache

from app.agents.pipeline import NurPathAgentPipeline
from app.services.citation import CitationValidator
from app.services.learning import SessionManager
from app.services.quiz import QuizService
from app.services.retrieval import HybridRetriever


@lru_cache
def get_sessions() -> SessionManager:
    return SessionManager()


@lru_cache
def get_retriever() -> HybridRetriever:
    return HybridRetriever()


@lru_cache
def get_pipeline() -> NurPathAgentPipeline:
    return NurPathAgentPipeline(retriever=get_retriever(), sessions=get_sessions())


@lru_cache
def get_quiz_service() -> QuizService:
    return QuizService(sessions=get_sessions())


@lru_cache
def get_citation_validator() -> CitationValidator:
    return CitationValidator()
