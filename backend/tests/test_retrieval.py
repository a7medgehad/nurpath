from app.schemas import AskResponse
from app.services.citation import CitationValidator
from app.services.retrieval import HybridRetriever


def test_retrieval_returns_passage_level_urls() -> None:
    retriever = HybridRetriever()
    result = retriever.retrieve("ما حكم لمس الزوجة في الوضوء؟", top_k=4)
    assert len(result.evidence_cards) >= 1
    assert all(card.passage_url.startswith("http") for card in result.evidence_cards)


def test_retrieval_prefers_diverse_sources_when_available() -> None:
    retriever = HybridRetriever()
    result = retriever.retrieve("ما اختلاف الفقهاء في لمس المرأة ونقض الوضوء؟", top_k=4)
    source_ids = {card.source_id for card in result.evidence_cards}
    assert len(source_ids) >= 2


def test_retrieval_health_sample_keeps_citation_integrity() -> None:
    retriever = HybridRetriever()
    result = retriever.retrieve("What are key wudu evidences?")
    response = AskResponse(
        direct_answer="Learning-only answer",
        evidence_cards=result.evidence_cards,
        opinion_comparison=[],
        confidence=0.7,
    )
    assert CitationValidator.validate_response(response)


def test_dimension_mismatch_recreates_collection() -> None:
    retriever = HybridRetriever()
    first = retriever.diagnostics()
    assert first["qdrant_collection_vector_size"] == retriever.embedder.dimension
    assert isinstance(first["reindex_required"], bool)
    assert isinstance(first["reranker_enabled"], bool)
    assert isinstance(first["reranker_provider"], str)
    assert isinstance(first["reranker_model_name"], str)
