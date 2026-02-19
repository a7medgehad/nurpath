from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UserLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class TopicIntent(str, Enum):
    aqidah = "aqidah"
    fiqh = "fiqh"
    akhlaq = "akhlaq"
    history = "history"
    language_learning = "language_learning"


class SourceDocument(BaseModel):
    id: str
    title: str
    author: str
    era: str
    language: str
    license: str
    url: str
    citation_policy: str


class SourceListResponse(BaseModel):
    items: List[SourceDocument] = Field(default_factory=list)
    total: int


class Passage(BaseModel):
    id: str
    source_document_id: str
    arabic_text: str
    english_text: str
    topic_tags: List[str] = Field(default_factory=list)


class EvidenceCard(BaseModel):
    source_id: str
    source_title: str
    passage_id: str
    arabic_quote: str
    english_quote: str
    citation_span: str
    relevance_score: float
    source_url: str


class OpinionComparisonItem(BaseModel):
    school_or_scholar: str
    stance_summary: str
    evidence_passage_ids: List[str] = Field(default_factory=list)


class LearningObjective(BaseModel):
    id: str
    title: str
    difficulty: str
    prerequisites: List[str] = Field(default_factory=list)
    expected_outcomes: List[str] = Field(default_factory=list)


class LessonPath(BaseModel):
    session_id: str
    objective_ids: List[str] = Field(default_factory=list)
    mastery_state: Dict[str, float] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    preferred_language: str = Field(default="ar", pattern=r"^(ar|en)$")
    level: UserLevel = UserLevel.beginner
    goals: List[str] = Field(default_factory=list)
    madhhab_preference: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    roadmap: List[LearningObjective] = Field(default_factory=list)
    lesson_path: LessonPath


class AskRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=4)
    preferred_language: str = Field(default="ar", pattern=r"^(ar|en)$")


class AskResponse(BaseModel):
    direct_answer: str
    evidence_cards: List[EvidenceCard] = Field(default_factory=list)
    opinion_comparison: List[OpinionComparisonItem] = Field(default_factory=list)
    confidence: float
    next_lesson: Optional[LearningObjective] = None
    safety_notice: Optional[str] = None
    abstained: bool = False


class QuizGenerateRequest(BaseModel):
    session_id: str
    objective_id: str
    num_questions: int = Field(default=3, ge=1, le=10)


class QuizQuestion(BaseModel):
    id: str
    prompt: str
    expected_keywords: List[str] = Field(default_factory=list)


class QuizGenerateResponse(BaseModel):
    objective_id: str
    questions: List[QuizQuestion] = Field(default_factory=list)


class QuizGradeRequest(BaseModel):
    session_id: str
    objective_id: str
    answers: Dict[str, str]


class QuizGradeResponse(BaseModel):
    objective_id: str
    score: float
    feedback: Dict[str, str]
    updated_mastery: Dict[str, float]


class RetrievalHealthResponse(BaseModel):
    ok: bool
    citations_valid: bool
    indexed_passages: int
    notes: List[str] = Field(default_factory=list)


class ArchitectureDiagramResponse(BaseModel):
    mermaid: str
