from __future__ import annotations

from typing import List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.schemas import (
    AskResponse,
    EvidenceCard,
    IkhtilafAnalysis,
    LearningObjective,
    OpinionComparisonItem,
    TopicIntent,
)
from app.services.ikhtilaf import analyze_ikhtilaf
from app.services.learning import SessionManager
from app.services.retrieval import HybridRetriever, RetrievalResult


class TutorState(TypedDict):
    session_id: str
    question: str
    preferred_language: str
    intent: TopicIntent
    evidence_cards: List[EvidenceCard]
    opinion_comparison: List[OpinionComparisonItem]
    ikhtilaf_analysis: IkhtilafAnalysis
    direct_answer: str
    confidence: float
    safety_notice: Optional[str]
    abstained: bool
    next_lesson: Optional[LearningObjective]


class NurPathAgentPipeline:
    def __init__(self, retriever: HybridRetriever, sessions: SessionManager) -> None:
        self.retriever = retriever
        self.sessions = sessions
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(TutorState)
        builder.add_node("intent", self._intent_node)
        builder.add_node("retrieve", self._retrieve_node)
        builder.add_node("compare", self._compare_node)
        builder.add_node("tutor", self._tutor_node)
        builder.add_node("safety", self._safety_node)

        builder.add_edge(START, "intent")
        builder.add_edge("intent", "retrieve")
        builder.add_edge("retrieve", "compare")
        builder.add_edge("compare", "tutor")
        builder.add_edge("tutor", "safety")
        builder.add_edge("safety", END)

        return builder.compile()

    def _intent_node(self, state: TutorState) -> TutorState:
        state["intent"] = self.retriever.classify_intent(state["question"])
        return state

    def _retrieve_node(self, state: TutorState) -> TutorState:
        result: RetrievalResult = self.retriever.retrieve(state["question"])
        state["evidence_cards"] = result.evidence_cards
        return state

    def _compare_node(self, state: TutorState) -> TutorState:
        cards = state["evidence_cards"]
        detection = analyze_ikhtilaf(
            evidence_cards=cards,
            passages=self.retriever.catalog.passages,
            preferred_language=state["preferred_language"],
        )
        state["opinion_comparison"] = detection.opinion_comparison
        state["ikhtilaf_analysis"] = detection.analysis
        return state

    def _tutor_node(self, state: TutorState) -> TutorState:
        cards = state["evidence_cards"]
        avg_relevance = 0.0
        if cards:
            avg_relevance = sum(card.relevance_score for card in cards) / len(cards)
        confidence = min(0.95, 0.2 + (len(cards) * 0.15) + (avg_relevance * 0.4))

        if state["preferred_language"] == "en":
            answer = (
                "Here is a learning-focused answer grounded in cited evidence. "
                "Review the evidence cards and compare differences before selecting practice."
            )
            if state["ikhtilaf_analysis"].status == "ikhtilaf":
                answer += " This topic contains valid scholarly disagreement (ikhtilaf)."
            elif state["ikhtilaf_analysis"].status == "consensus":
                answer += " Retrieved schools align on the core ruling."
        else:
            answer = (
                "هذه إجابة تعليمية مبنية على الأدلة الموثقة. "
                "راجع بطاقات الأدلة وقارن بين الأقوال قبل الترجيح أو العمل."
            )
            if state["ikhtilaf_analysis"].status == "ikhtilaf":
                answer += " تظهر هنا مساحة اختلاف معتبر بين الأقوال."
            elif state["ikhtilaf_analysis"].status == "consensus":
                answer += " المدارس المسترجعة متفقة على أصل الحكم."

        next_obj = None
        lesson_path = self.sessions.get_lesson_path(state["session_id"])
        for oid in lesson_path.objective_ids:
            if lesson_path.mastery_state.get(oid, 0.0) < 0.6:
                next_obj = LearningObjective(
                    id=oid,
                    title=oid.replace("-", " ").title(),
                    difficulty="adaptive",
                    expected_outcomes=["Improve evidence-based reasoning"],
                )
                break

        state["direct_answer"] = answer
        state["confidence"] = round(confidence, 3)
        state["next_lesson"] = next_obj
        state["abstained"] = False
        state["safety_notice"] = None
        return state

    def _safety_node(self, state: TutorState) -> TutorState:
        q = state["question"].lower()
        sensitive = any(
            keyword in q
            for keyword in [
                "my divorce",
                "طلاقي",
                "specific fatwa",
                "fatwa",
                "فتوى",
                "personal ruling",
                "case-specific",
                "حالتي الشخصية",
            ]
        )

        if state["confidence"] < settings.confidence_threshold or sensitive:
            state["abstained"] = True
            if state["preferred_language"] == "en":
                state["direct_answer"] = (
                    "I cannot provide a binding ruling for this case. "
                    "Please consult a qualified scholar and use the cited material for study only."
                )
                state["safety_notice"] = "Educational guidance only. Escalate to a qualified scholar."
            else:
                state["direct_answer"] = (
                    "لا يمكنني إصدار فتوى مُلزِمة لهذه الحالة. "
                    "يرجى الرجوع إلى عالم مؤهل، واستخدام الأدلة هنا للتعلّم فقط."
                )
                state["safety_notice"] = "إرشاد تعليمي فقط. يلزم الرجوع إلى عالم مؤهل."

        return state

    def run(self, session_id: str, question: str, preferred_language: str) -> AskResponse:
        initial_state: TutorState = {
            "session_id": session_id,
            "question": question,
            "preferred_language": preferred_language,
            "intent": TopicIntent.language_learning,
            "evidence_cards": [],
            "opinion_comparison": [],
            "ikhtilaf_analysis": IkhtilafAnalysis(
                status="insufficient",
                summary="No analysis available.",
                compared_schools=[],
                shared_topic_tags=[],
                conflict_pairs=[],
            ),
            "direct_answer": "",
            "confidence": 0.0,
            "safety_notice": None,
            "abstained": False,
            "next_lesson": None,
        }

        result = self.graph.invoke(initial_state)

        return AskResponse(
            direct_answer=result["direct_answer"],
            evidence_cards=result["evidence_cards"],
            opinion_comparison=result["opinion_comparison"],
            ikhtilaf_analysis=result["ikhtilaf_analysis"],
            confidence=result["confidence"],
            next_lesson=result["next_lesson"],
            safety_notice=result["safety_notice"],
            abstained=result["abstained"],
        )

    def mermaid(self) -> str:
        return self.graph.get_graph().draw_mermaid()
