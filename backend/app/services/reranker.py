from __future__ import annotations

import logging
import re
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("nurpath.reranker")


class Reranker(Protocol):
    provider_name: str
    model_name: str
    enabled: bool

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        ...


def _normalize(text: str) -> str:
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.lower()
    text = re.sub(r"[^\w\u0600-\u06FF\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _token_overlap_score(query: str, passage: str) -> float:
    q_tokens = set(_normalize(query).split())
    p_tokens = set(_normalize(passage).split())
    if not q_tokens:
        return 0.0
    return len(q_tokens.intersection(p_tokens)) / len(q_tokens)


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    minimum = min(scores)
    maximum = max(scores)
    if maximum == minimum:
        baseline = 1.0 if maximum > 0 else 0.0
        return [baseline for _ in scores]
    return [max(0.0, (score - minimum) / (maximum - minimum)) for score in scores]


class TokenOverlapReranker:
    provider_name = "token_overlap"
    model_name = "token-overlap-reranker"
    enabled = True

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        raw = [_token_overlap_score(query, passage) for passage in passages]
        return _normalize_scores(raw)


class SentenceTransformerReranker:
    provider_name = "sentence_transformers"
    enabled = True

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ModuleNotFoundError as exc:
            raise RuntimeError("sentence-transformers is not installed for reranking") from exc

        self.model_name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        pairs = [(query, passage) for passage in passages]
        raw = self._model.predict(pairs)
        if hasattr(raw, "tolist"):
            scores = [float(v) for v in raw.tolist()]
        else:
            scores = [float(v) for v in raw]
        return _normalize_scores(scores)


class DisabledReranker:
    provider_name = "disabled"
    model_name = "none"
    enabled = False

    def rerank(self, query: str, passages: list[str]) -> list[float]:
        return [0.0 for _ in passages]


def get_reranker() -> Reranker:
    if not settings.reranker_enabled:
        logger.info("Reranker disabled by configuration.")
        return DisabledReranker()

    if settings.reranker_provider == "sentence_transformers":
        try:
            reranker = SentenceTransformerReranker(settings.reranker_model_name)
            logger.info(
                "Reranker active: %s (%s)",
                reranker.provider_name,
                reranker.model_name,
            )
            return reranker
        except RuntimeError as exc:
            logger.warning("Falling back to token overlap reranker: %s", exc)
            return TokenOverlapReranker()

    logger.info("Reranker provider unsupported; using token overlap fallback.")
    return TokenOverlapReranker()
