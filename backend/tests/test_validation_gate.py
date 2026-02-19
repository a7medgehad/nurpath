from app.schemas import AskResponse, EvidenceCard
from app.services.validation import AnswerValidationService


def _evidence_card(passage_id: str = "p_1") -> EvidenceCard:
    return EvidenceCard(
        source_id="src_1",
        source_title="Source 1",
        source_title_ar="المصدر ١",
        passage_id=passage_id,
        arabic_quote="الوضوء عبادة لها شروط معلومة.",
        english_quote="Wudu is worship with known conditions.",
        citation_span=passage_id,
        relevance_score=0.8,
        source_url="https://example.org/book",
        passage_url="https://example.org/book/1",
        source_type="fiqh",
        authenticity_level="mu_tabar",
        reference=None,
    )


def test_validation_gate_passes_grounded_answer() -> None:
    service = AnswerValidationService()
    response = AskResponse(
        direct_answer="Wudu is worship with known conditions.",
        evidence_cards=[_evidence_card("p_1"), _evidence_card("p_2")],
        opinion_comparison=[],
        confidence=0.8,
    )
    evaluated = service.apply(response=response, preferred_language="en")
    assert evaluated.validation.passed is True
    assert evaluated.abstained is False


def test_validation_gate_abstains_on_missing_citation_integrity() -> None:
    service = AnswerValidationService()
    broken_card = _evidence_card("p_x")
    broken_card.citation_span = ""
    response = AskResponse(
        direct_answer="Unsupported answer",
        evidence_cards=[broken_card],
        opinion_comparison=[],
        confidence=0.7,
    )
    evaluated = service.apply(response=response, preferred_language="en")
    assert evaluated.validation.passed is False
    assert evaluated.abstained is True
    assert evaluated.validation.decision_reason == "citation_integrity_failed"


def test_validation_gate_respects_existing_safety_abstention() -> None:
    service = AnswerValidationService()
    response = AskResponse(
        direct_answer="Please consult a scholar.",
        evidence_cards=[_evidence_card()],
        opinion_comparison=[],
        confidence=0.2,
        abstained=True,
        safety_notice="Safety policy",
    )
    evaluated = service.apply(response=response, preferred_language="en")
    assert evaluated.abstained is True
    assert evaluated.validation.decision_reason == "abstained_by_safety_policy"
