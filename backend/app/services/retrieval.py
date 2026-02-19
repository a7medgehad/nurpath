from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.schemas import EvidenceCard, Passage, TopicIntent
from app.services.catalog import load_catalog


@dataclass
class RetrievalResult:
    evidence_cards: List[EvidenceCard]
    intent: TopicIntent


class HybridRetriever:
    """
    Dense + lexical placeholder retriever.

    This MVP implementation uses token overlap scoring so the API works out of the box
    without requiring model downloads. It is intentionally replaceable with Qdrant +
    embedding/reranker stack in production.
    """

    def __init__(self) -> None:
        self.catalog = load_catalog()

    @staticmethod
    def classify_intent(question: str) -> TopicIntent:
        q = question.lower()
        if any(word in q for word in ["wudu", "وضوء", "طهارة", "fiqh", "حكم"]):
            return TopicIntent.fiqh
        if any(word in q for word in ["aqidah", "عقيدة", "iman", "إيمان"]):
            return TopicIntent.aqidah
        if any(word in q for word in ["akhlaq", "أخلاق", "adab", "تزكية"]):
            return TopicIntent.akhlaq
        if any(word in q for word in ["history", "سيرة", "تاريخ"]):
            return TopicIntent.history
        return TopicIntent.language_learning

    @staticmethod
    def _token_score(question: str, passage: Passage) -> float:
        q_tokens = set(question.lower().split())
        p_tokens = set((passage.arabic_text + " " + passage.english_text).lower().split())
        if not q_tokens:
            return 0.0
        overlap = len(q_tokens.intersection(p_tokens))
        return overlap / len(q_tokens)

    def retrieve(self, question: str, top_k: int = 4) -> RetrievalResult:
        intent = self.classify_intent(question)

        scored = [
            (passage, self._token_score(question, passage))
            for passage in self.catalog.passages.values()
        ]
        scored.sort(key=lambda item: item[1], reverse=True)

        cards: List[EvidenceCard] = []
        for passage, score in scored:
            # Keep only evidence with minimal lexical support to avoid false confidence.
            if score <= 0:
                continue
            source = self.catalog.sources[passage.source_document_id]
            cards.append(
                EvidenceCard(
                    source_id=source.id,
                    source_title=source.title,
                    passage_id=passage.id,
                    arabic_quote=passage.arabic_text,
                    english_quote=passage.english_text,
                    citation_span=passage.id,
                    relevance_score=round(score, 4),
                    source_url=source.url,
                )
            )
            if len(cards) >= top_k:
                break

        return RetrievalResult(evidence_cards=cards, intent=intent)
