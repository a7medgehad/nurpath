from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from app.core.config import settings


class Embedder(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class HashEmbedder:
    """
    Deterministic offline embedder.

    It is not as semantically strong as transformer embeddings, but guarantees a
    working vector retrieval path without external model downloads.
    """

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


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed; use embedding_provider=hash or install it"
            ) from exc

        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, row)) for row in vectors]


def get_embedder() -> Embedder:
    if settings.embedding_provider == "sentence_transformers":
        try:
            return SentenceTransformerEmbedder(settings.embedding_model_name)
        except RuntimeError:
            return HashEmbedder(settings.embedding_dimension)
    return HashEmbedder(settings.embedding_dimension)
