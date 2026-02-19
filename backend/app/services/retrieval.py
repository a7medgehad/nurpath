from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.schemas import EvidenceCard, Passage, TopicIntent
from app.services.catalog import load_catalog
from app.services.embeddings import Embedder, get_embedder


@dataclass
class RetrievalResult:
    evidence_cards: List[EvidenceCard]
    intent: TopicIntent


class HybridRetriever:
    """Hybrid retriever: vector search (Qdrant) + lexical overlap re-ranking."""

    def __init__(self) -> None:
        self.catalog = load_catalog()
        self.embedder: Embedder = get_embedder()
        self.client = self._build_client()
        self._ensure_collection()
        self._upsert_passages()

    @staticmethod
    def _normalize(text: str) -> str:
        text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
        text = text.lower()
        text = re.sub(r"[^\w\u0600-\u06FF\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def classify_intent(question: str) -> TopicIntent:
        q = HybridRetriever._normalize(question)
        if any(word in q for word in ["wudu", "وضوء", "طهارة", "fiqh", "حكم"]):
            return TopicIntent.fiqh
        if any(word in q for word in ["aqidah", "عقيدة", "iman", "إيمان"]):
            return TopicIntent.aqidah
        if any(word in q for word in ["akhlaq", "أخلاق", "adab", "تزكية"]):
            return TopicIntent.akhlaq
        if any(word in q for word in ["history", "سيرة", "تاريخ"]):
            return TopicIntent.history
        return TopicIntent.language_learning

    def _build_client(self) -> QdrantClient:
        if settings.qdrant_local_mode:
            return QdrantClient(location=":memory:")
        return QdrantClient(url=settings.qdrant_url)

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if settings.qdrant_collection in existing:
            return
        self.client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=self.embedder.dimension, distance=Distance.COSINE),
        )

    def _upsert_passages(self) -> None:
        passages = list(self.catalog.passages.values())
        if not passages:
            return

        texts = [f"{p.arabic_text}\n{p.english_text}" for p in passages]
        vectors = self.embedder.embed(texts)

        points = [
            PointStruct(
                id=idx + 1,
                vector=vectors[idx],
                payload={
                    "passage_id": passage.id,
                    "source_document_id": passage.source_document_id,
                    "arabic_text": passage.arabic_text,
                    "english_text": passage.english_text,
                    "topic_tags": passage.topic_tags,
                },
            )
            for idx, passage in enumerate(passages)
        ]
        self.client.upsert(collection_name=settings.qdrant_collection, points=points)

    def _token_score(self, question: str, passage: Passage) -> float:
        q_tokens = set(self._normalize(question).split())
        p_tokens = set(self._normalize(passage.arabic_text + " " + passage.english_text).split())
        if not q_tokens:
            return 0.0
        return len(q_tokens.intersection(p_tokens)) / len(q_tokens)

    def _vector_scores(self, question: str, limit: int) -> Dict[str, float]:
        vector = self.embedder.embed([question])[0]
        response = self.client.query_points(
            collection_name=settings.qdrant_collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        hits = response.points

        raw_scores: Dict[str, float] = {}
        for hit in hits:
            payload = hit.payload or {}
            passage_id = payload.get("passage_id")
            if not passage_id:
                continue
            raw_scores[passage_id] = max(raw_scores.get(passage_id, 0.0), float(hit.score))

        if not raw_scores:
            return {}

        max_score = max(raw_scores.values())
        if max_score <= 0:
            return {pid: 0.0 for pid in raw_scores}

        return {pid: score / max_score for pid, score in raw_scores.items()}

    def retrieve(self, question: str, top_k: int = 4) -> RetrievalResult:
        intent = self.classify_intent(question)

        lexical_scores = {
            passage.id: self._token_score(question, passage)
            for passage in self.catalog.passages.values()
        }
        vector_scores = self._vector_scores(question, max(top_k * 4, 8))

        lexical_top = sorted(lexical_scores, key=lexical_scores.get, reverse=True)[: max(top_k * 4, 8)]
        candidate_ids = set(lexical_top).union(vector_scores.keys())

        ranked = []
        for passage_id in candidate_ids:
            lexical = lexical_scores.get(passage_id, 0.0)
            vector = vector_scores.get(passage_id, 0.0)
            combined = (0.35 * lexical) + (0.65 * vector)
            if combined <= 0:
                continue
            ranked.append((passage_id, combined))

        ranked.sort(key=lambda item: item[1], reverse=True)

        cards: List[EvidenceCard] = []
        for passage_id, score in ranked[:top_k]:
            passage = self.catalog.passages[passage_id]
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

        return RetrievalResult(evidence_cards=cards, intent=intent)
