from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Literal, Protocol

from app.core.config import settings

logger = logging.getLogger("nurpath.embeddings")

EmbeddingMode = Literal["query", "passage"]


def is_e5_model(model_name: str) -> bool:
    return "e5" in model_name.lower()


def prepare_texts_for_embedding(
    texts: list[str], *, mode: EmbeddingMode, model_name: str
) -> list[str]:
    if not is_e5_model(model_name):
        return texts
    prefix = "query: " if mode == "query" else "passage: "
    return [f"{prefix}{text}" for text in texts]


class Embedder(Protocol):
    dimension: int
    provider_name: str
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        ...


class HashEmbedder:
    """
    Deterministic offline embedder.

    It is not as semantically strong as transformer embeddings, but guarantees a
    working vector retrieval path without external model downloads.
    """

    provider_name = "hash"
    model_name = "deterministic-hash"

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    @staticmethod
    def _normalize(text: str) -> list[str]:
        text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
        text = text.lower()
        text = re.sub(r"[^\w\u0600-\u06FF\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text.split()

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = self._normalize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            vector[idx] += sign * weight

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self.embed(texts)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self.embed(texts)


class SentenceTransformerEmbedder:
    provider_name = "sentence_transformers"

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed; use embedding_provider=hash or install it"
            ) from exc

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def _encode(self, texts: list[str], *, mode: EmbeddingMode) -> list[list[float]]:
        prepared = prepare_texts_for_embedding(texts, mode=mode, model_name=self.model_name)
        vectors = self._model.encode(prepared, normalize_embeddings=True)
        return [list(map(float, row)) for row in vectors]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, mode="passage")

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, mode="query")

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, mode="passage")


def get_embedder() -> Embedder:
    if settings.embedding_provider == "sentence_transformers":
        try:
            embedder = SentenceTransformerEmbedder(settings.embedding_model_name)
            logger.info(
                "Embedding provider active: %s (%s), dim=%s",
                embedder.provider_name,
                embedder.model_name,
                embedder.dimension,
            )
            return embedder
        except RuntimeError as exc:
            logger.warning("Falling back to hash embeddings: %s", exc)
            return HashEmbedder(settings.embedding_dimension)
    embedder = HashEmbedder(settings.embedding_dimension)
    logger.info(
        "Embedding provider active: %s (%s), dim=%s",
        embedder.provider_name,
        embedder.model_name,
        embedder.dimension,
    )
    return embedder
