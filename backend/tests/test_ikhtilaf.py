from app.schemas import EvidenceCard, Passage
from app.services.ikhtilaf import analyze_ikhtilaf


def _card(passage_id: str) -> EvidenceCard:
    return EvidenceCard(
        source_id="src",
        source_title="src title",
        source_title_ar="عنوان المصدر",
        passage_id=passage_id,
        arabic_quote="",
        english_quote="",
        citation_span=passage_id,
        relevance_score=0.9,
        source_url="https://example.org",
        passage_url="https://example.org/passage",
        source_type="fiqh",
        authenticity_level="mu_tabar",
        reference=None,
    )


def test_detects_ikhtilaf_when_two_schools_conflict() -> None:
    passages = {
        "p_shafii": Passage(
            id="p_shafii",
            source_document_id="src",
            arabic_text="يرى الشافعية أن اللمس ينقض الوضوء",
            english_text="Shafii: direct touching can invalidate wudu.",
            passage_url="https://example.org/p_shafii",
            topic_tags=["fiqh", "wudu", "shafii", "ikhtilaf"],
        ),
        "p_hanafi": Passage(
            id="p_hanafi",
            source_document_id="src",
            arabic_text="يرى الحنفية أن اللمس لا ينقض الوضوء",
            english_text="Hanafi: touching does not invalidate wudu.",
            passage_url="https://example.org/p_hanafi",
            topic_tags=["fiqh", "wudu", "hanafi", "ikhtilaf"],
        ),
    }
    result = analyze_ikhtilaf(
        evidence_cards=[_card("p_shafii"), _card("p_hanafi")],
        passages=passages,
        preferred_language="en",
    )

    assert result.analysis.status == "ikhtilaf"
    assert len(result.analysis.conflict_pairs) == 1
    assert len(result.opinion_comparison) == 2


def test_detects_consensus_when_two_schools_align() -> None:
    passages = {
        "p_shafii": Passage(
            id="p_shafii",
            source_document_id="src",
            arabic_text="يرى الشافعية أن الفعل ينقض الوضوء",
            english_text="Shafii: this act can invalidate wudu.",
            passage_url="https://example.org/p_shafii",
            topic_tags=["fiqh", "wudu", "shafii"],
        ),
        "p_hanbali": Passage(
            id="p_hanbali",
            source_document_id="src",
            arabic_text="يرى الحنابلة أن الفعل ينقض الوضوء",
            english_text="Hanbali: this act can invalidate wudu.",
            passage_url="https://example.org/p_hanbali",
            topic_tags=["fiqh", "wudu", "hanbali"],
        ),
    }
    result = analyze_ikhtilaf(
        evidence_cards=[_card("p_shafii"), _card("p_hanbali")],
        passages=passages,
        preferred_language="en",
    )

    assert result.analysis.status == "consensus"
    assert result.analysis.conflict_pairs == []


def test_insufficient_when_school_annotations_are_missing() -> None:
    passages = {
        "p_generic": Passage(
            id="p_generic",
            source_document_id="src",
            arabic_text="الدليل يركز على الإحسان.",
            english_text="The evidence focuses on ihsan.",
            passage_url="https://example.org/p_generic",
            topic_tags=["aqidah", "ihsan"],
        )
    }
    result = analyze_ikhtilaf(
        evidence_cards=[_card("p_generic")],
        passages=passages,
        preferred_language="en",
    )

    assert result.analysis.status == "insufficient"
    assert result.opinion_comparison == []
