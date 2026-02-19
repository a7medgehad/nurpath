from __future__ import annotations

import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.schemas import EvidenceCard, Passage, TopicIntent
from app.services.catalog import load_catalog
from app.services.embeddings import Embedder, get_embedder

SOURCE_TYPE_PRIORITY = {
    "quran": 0.04,
    "hadith": 0.02,
    "fiqh": 0.0,
}

AUTHENTICITY_PRIORITY = {
    "qat_i": 0.04,
    "sahih": 0.03,
    "hasan": 0.02,
    "mu_tabar": 0.01,
}

INTENT_TAGS = {
    TopicIntent.fiqh: {"fiqh", "فقه", "wudu", "وضوء", "tahara", "طهارة"},
    TopicIntent.aqidah: {"aqidah", "عقيدة", "iman", "إيمان", "ihsan", "إحسان", "islam", "إسلام"},
    TopicIntent.akhlaq: {"akhlaq", "أخلاق", "adab", "آداب", "humanity", "إنسانية"},
    TopicIntent.history: {"history", "تاريخ", "sira", "سيرة"},
    TopicIntent.language_learning: {"language_learning", "تعلم", "لغة"},
}

QUERY_EXPANSIONS = {
    TopicIntent.fiqh: ["طهارة", "وضوء", "نواقض الوضوء", "fiqh ruling"],
    TopicIntent.aqidah: ["الإيمان", "أركان الإيمان", "aqidah basics"],
    TopicIntent.akhlaq: ["آداب", "تزكية", "akhlaq manners"],
    TopicIntent.history: ["السيرة", "تاريخ", "seerah"],
    TopicIntent.language_learning: ["لغة عربية", "Arabic terms", "مصطلحات شرعية"],
}


@dataclass
class RetrievalResult:
    evidence_cards: List[EvidenceCard]
    intent: TopicIntent
    avg_top_score: float = 0.0
    used_expansion: bool = False


class HybridRetriever:
    """Hybrid retriever: vector search (Qdrant) + lexical overlap re-ranking."""

    def __init__(self) -> None:
        self.catalog = load_catalog()
        self.embedder: Embedder = get_embedder()
        self.client = self._build_client()
        total_weight = settings.retrieval_lexical_weight + settings.retrieval_vector_weight
        if total_weight <= 0:
            raise ValueError("Retrieval weights must sum to a positive value.")
        self._top_scores: deque[float] = deque(maxlen=200)
        self._expansion_uses = 0
        self._collection_vector_size = 0
        self._reindex_required = False
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

    def diagnostics(self) -> dict[str, float | int | str | bool]:
        profile = "local" if settings.qdrant_local_mode else "docker-first"
        qdrant_connected = self._is_qdrant_connected()
        avg = sum(self._top_scores) / len(self._top_scores) if self._top_scores else 0.0
        return {
            "profile": profile,
            "qdrant_connected": qdrant_connected,
            "retrieval_avg_top_score": round(avg, 4),
            "retrieval_observations": len(self._top_scores),
            "expansion_uses": self._expansion_uses,
            "embedding_provider": self.embedder.provider_name,
            "embedding_model_name": self.embedder.model_name,
            "embedding_dimension": self.embedder.dimension,
            "qdrant_collection_vector_size": self._collection_vector_size,
            "reindex_required": self._reindex_required,
        }

    def _build_client(self) -> QdrantClient:
        if settings.qdrant_local_mode:
            return QdrantClient(location=":memory:")
        return QdrantClient(url=settings.qdrant_url, check_compatibility=False)

    def _is_qdrant_connected(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if settings.qdrant_collection not in existing:
            self.client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=self.embedder.dimension, distance=Distance.COSINE),
            )
            self._collection_vector_size = self.embedder.dimension
            return

        current_size = self._get_collection_vector_size(settings.qdrant_collection)
        self._collection_vector_size = current_size
        if current_size != self.embedder.dimension:
            self._reindex_required = True
            self.client.delete_collection(collection_name=settings.qdrant_collection)
            self.client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=self.embedder.dimension, distance=Distance.COSINE),
            )
            self._collection_vector_size = self.embedder.dimension

    def _get_collection_vector_size(self, collection_name: str) -> int:
        info = self.client.get_collection(collection_name=collection_name)
        vectors_cfg = info.config.params.vectors
        if hasattr(vectors_cfg, "size"):
            return int(vectors_cfg.size)
        if isinstance(vectors_cfg, dict):
            first = next(iter(vectors_cfg.values()), None)
            if first is not None and hasattr(first, "size"):
                return int(first.size)
        return self.embedder.dimension

    def _upsert_passages(self) -> None:
        passages = list(self.catalog.passages.values())
        if not passages:
            return

        texts = [f"{p.arabic_text}\n{p.english_text}" for p in passages]
        vectors = self.embedder.embed_passages(texts)

        points = [
            PointStruct(
                id=idx + 1,
                vector=vectors[idx],
                payload={
                    "passage_id": passage.id,
                    "source_document_id": passage.source_document_id,
                    "arabic_text": passage.arabic_text,
                    "english_text": passage.english_text,
                    "passage_url": passage.passage_url,
                    "topic_tags": passage.topic_tags,
                    "reference": passage.reference.model_dump() if passage.reference else None,
                    "source_type": self.catalog.sources[passage.source_document_id].source_type,
                    "authenticity_level": self.catalog.sources[
                        passage.source_document_id
                    ].authenticity_level,
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
        shared = q_tokens.intersection(p_tokens)
        if not shared:
            return 0.0
        precision = len(shared) / len(q_tokens)
        recall = len(shared) / max(len(p_tokens), 1)
        return round((0.8 * precision) + (0.2 * recall), 6)

    def _lexical_scores(self, question: str) -> Dict[str, float]:
        return {
            passage.id: self._token_score(question, passage)
            for passage in self.catalog.passages.values()
        }

    def _vector_scores(self, question: str, limit: int) -> Dict[str, float]:
        vector = self.embedder.embed_queries([question])[0]
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
            raw_scores[passage_id] = max(raw_scores.get(passage_id, -1.0), float(hit.score))

        if not raw_scores:
            return {}

        minimum = min(raw_scores.values())
        maximum = max(raw_scores.values())
        if maximum == minimum:
            baseline = 1.0 if maximum > 0 else 0.0
            return {pid: baseline for pid in raw_scores}

        return {
            pid: max(0.0, (score - minimum) / (maximum - minimum))
            for pid, score in raw_scores.items()
        }

    @staticmethod
    def _expanded_query(question: str, intent: TopicIntent) -> str:
        additions = QUERY_EXPANSIONS.get(intent, [])
        if not additions:
            return question
        return f"{question} {' '.join(additions)}"

    def _rank_candidates(self, question: str, intent: TopicIntent, limit: int) -> list[tuple[str, float]]:
        with ThreadPoolExecutor(max_workers=2) as pool:
            lexical_future = pool.submit(self._lexical_scores, question)
            vector_future = pool.submit(self._vector_scores, question, max(limit * 3, 10))
            lexical_scores = lexical_future.result()
            vector_scores = vector_future.result()

        lexical_top = sorted(lexical_scores, key=lexical_scores.get, reverse=True)[: max(limit * 2, 10)]
        candidate_ids = set(lexical_top).union(vector_scores.keys())

        ranked: list[tuple[str, float]] = []
        for passage_id in candidate_ids:
            lexical = lexical_scores.get(passage_id, 0.0)
            vector = vector_scores.get(passage_id, 0.0)
            passage = self.catalog.passages[passage_id]
            source = self.catalog.sources[passage.source_document_id]
            priority_bonus = SOURCE_TYPE_PRIORITY.get(source.source_type, 0.0)
            authenticity_bonus = AUTHENTICITY_PRIORITY.get(source.authenticity_level, 0.0)
            passage_tags = {tag.lower() for tag in passage.topic_tags}
            intent_tags = INTENT_TAGS.get(intent, set())
            intent_bonus = 0.04 if passage_tags.intersection(intent_tags) else 0.0
            combined = (
                (settings.retrieval_lexical_weight * lexical)
                + (settings.retrieval_vector_weight * vector)
                + priority_bonus
                + authenticity_bonus
                + intent_bonus
            )
            if combined <= 0.0:
                continue
            ranked.append((passage_id, combined))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _select_with_diversity(self, ranked: list[tuple[str, float]], top_k: int) -> list[tuple[str, float]]:
        if not ranked:
            return []

        source_count = len(
            {
                self.catalog.passages[passage_id].source_document_id
                for passage_id, _ in ranked
            }
        )
        min_diverse = min(2, source_count)
        selected: list[tuple[str, float]] = []
        seen_passages: set[str] = set()
        seen_sources: set[str] = set()

        for passage_id, score in ranked:
            source_id = self.catalog.passages[passage_id].source_document_id
            if source_id in seen_sources:
                continue
            selected.append((passage_id, score))
            seen_passages.add(passage_id)
            seen_sources.add(source_id)
            if len(seen_sources) >= min_diverse:
                break

        for passage_id, score in ranked:
            if len(selected) >= top_k:
                break
            if passage_id in seen_passages:
                continue
            selected.append((passage_id, score))
            seen_passages.add(passage_id)

        return selected[:top_k]

    def retrieve(self, question: str, top_k: int = 4) -> RetrievalResult:
        intent = self.classify_intent(question)
        ranked = self._rank_candidates(question=question, intent=intent, limit=max(top_k * 3, 10))
        used_expansion = False

        top_score = ranked[0][1] if ranked else 0.0
        if top_score < settings.weak_retrieval_threshold:
            expanded_question = self._expanded_query(question, intent)
            expanded_ranked = self._rank_candidates(
                question=expanded_question,
                intent=intent,
                limit=max(top_k * 4, 12),
            )
            expanded_top = expanded_ranked[0][1] if expanded_ranked else 0.0
            if expanded_top > top_score:
                ranked = expanded_ranked
                top_score = expanded_top
                used_expansion = True
                self._expansion_uses += 1

        chosen = self._select_with_diversity(ranked=ranked, top_k=top_k)
        cards: List[EvidenceCard] = []
        for passage_id, score in chosen:
            passage = self.catalog.passages[passage_id]
            source = self.catalog.sources[passage.source_document_id]
            cards.append(
                EvidenceCard(
                    source_id=source.id,
                    source_title=source.title,
                    source_title_ar=source.title_ar,
                    passage_id=passage.id,
                    arabic_quote=passage.arabic_text,
                    english_quote=passage.english_text,
                    citation_span=passage.id,
                    relevance_score=round(score, 4),
                    source_url=source.url,
                    passage_url=passage.passage_url,
                    source_type=source.source_type,
                    authenticity_level=source.authenticity_level,
                    reference=passage.reference,
                )
            )

        avg_top_score = 0.0
        if chosen:
            avg_top_score = sum(score for _, score in chosen) / len(chosen)
        self._top_scores.append(top_score)

        return RetrievalResult(
            evidence_cards=cards,
            intent=intent,
            avg_top_score=round(avg_top_score, 4),
            used_expansion=used_expansion,
        )
