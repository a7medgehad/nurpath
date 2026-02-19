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
    title_ar: str
    author: str
    author_ar: str
    era: str
    language: str
    license: str
    url: str
    citation_policy: str
    citation_policy_ar: str
    source_type: str
    authenticity_level: str


class ReferenceData(BaseModel):
    surah: Optional[str] = None
    ayah: Optional[str] = None
    collection: Optional[str] = None
    book: Optional[str] = None
    hadith_number: Optional[str] = None
    grading_authority: Optional[str] = None
    volume: Optional[str] = None
    page: Optional[str] = None
    madhhab: Optional[str] = None
    display_ar: Optional[str] = None


class SourceListResponse(BaseModel):
    items: List[SourceDocument] = Field(default_factory=list)
    total: int


class Passage(BaseModel):
    id: str
    source_document_id: str
    arabic_text: str
    english_text: str
    passage_url: str
    topic_tags: List[str] = Field(default_factory=list)
    reference: Optional[ReferenceData] = None


class EvidenceCard(BaseModel):
    source_id: str
    source_title: str
    source_title_ar: str
    passage_id: str
    arabic_quote: str
    english_quote: str
    citation_span: str
    relevance_score: float
    source_url: str
    passage_url: str
    source_type: str
    authenticity_level: str
    reference: Optional[ReferenceData] = None


class OpinionComparisonItem(BaseModel):
    school_or_scholar: str
    stance_summary: str
    stance_type: str = "unclear"
    evidence_passage_ids: List[str] = Field(default_factory=list)


class ConflictPair(BaseModel):
    school_a: str
    school_b: str
    issue_topic: str
    evidence_passage_ids: List[str] = Field(default_factory=list)


class IkhtilafAnalysis(BaseModel):
    status: str
    summary: str
    compared_schools: List[str] = Field(default_factory=list)
    shared_topic_tags: List[str] = Field(default_factory=list)
    conflict_pairs: List[ConflictPair] = Field(default_factory=list)


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


class CitationIntegrityResult(BaseModel):
    passed: bool = False
    coverage: float = 0.0


class ScoreGateResult(BaseModel):
    score: float = 0.0
    threshold: float = 0.0
    passed: bool = False


class ValidationResult(BaseModel):
    passed: bool = False
    citation_integrity: CitationIntegrityResult = Field(default_factory=CitationIntegrityResult)
    grounding: ScoreGateResult = Field(default_factory=ScoreGateResult)
    faithfulness: ScoreGateResult = Field(default_factory=ScoreGateResult)
    decision_reason: str = "not_evaluated"


class AskRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=4)
    preferred_language: str = Field(default="ar", pattern=r"^(ar|en)$")


class AskResponse(BaseModel):
    direct_answer: str
    evidence_cards: List[EvidenceCard] = Field(default_factory=list)
    opinion_comparison: List[OpinionComparisonItem] = Field(default_factory=list)
    ikhtilaf_analysis: Optional[IkhtilafAnalysis] = None
    confidence: float
    next_lesson: Optional[LearningObjective] = None
    safety_notice: Optional[str] = None
    abstained: bool = False
    validation: ValidationResult = Field(default_factory=ValidationResult)


class QuizGenerateRequest(BaseModel):
    session_id: str
    objective_id: str
    num_questions: int = Field(default=3, ge=1, le=10)
    preferred_language: str = Field(default="ar", pattern=r"^(ar|en)$")


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
    profile: str
    qdrant_connected: bool
    postgres_connected: bool
    embedding_provider: str
    embedding_model_name: str
    embedding_dimension: int
    reranker_enabled: bool
    reranker_provider: str
    reranker_model_name: str
    qdrant_collection_vector_size: int
    reindex_required: bool
    citations_valid: bool
    indexed_passages: int
    retrieval_avg_top_score: float
    validation_pass_count: int
    validation_abstain_count: int
    notes: List[str] = Field(default_factory=list)


class ArchitectureDiagramResponse(BaseModel):
    mermaid: str
