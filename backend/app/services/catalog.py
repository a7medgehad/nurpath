from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from sqlmodel import select

from app.core.db import get_db_session
from app.models import PassageModel, SourceDocumentModel
from app.core.config import settings
from app.schemas import Passage, SourceDocument


@dataclass
class CatalogStore:
    sources: Dict[str, SourceDocument]
    passages: Dict[str, Passage]


def _resolve_catalog_path() -> Path:
    # Path is relative to backend/ in default local setup.
    candidate = Path(__file__).resolve().parents[3] / "data" / "samples" / "sources.json"
    if candidate.exists():
        return candidate

    configured = Path(settings.source_catalog_path)
    if configured.exists():
        return configured

    raise FileNotFoundError("Could not resolve sources catalog path.")


@lru_cache(maxsize=1)
def load_catalog() -> CatalogStore:
    data = json.loads(_resolve_catalog_path().read_text(encoding="utf-8"))

    sources: Dict[str, SourceDocument] = {}
    passages: Dict[str, Passage] = {}

    for row in data:
        source = SourceDocument(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            era=row["era"],
            language=row["language"],
            license=row["license"],
            url=row["url"],
            citation_policy=row["citation_policy"],
        )
        sources[source.id] = source

        for p in row.get("passages", []):
            passage = Passage(
                id=p["id"],
                source_document_id=source.id,
                arabic_text=p["arabic_text"],
                english_text=p["english_text"],
                topic_tags=p.get("topic_tags", []),
            )
            passages[passage.id] = passage

    return CatalogStore(sources=sources, passages=passages)


def list_sources() -> List[SourceDocument]:
    return list(load_catalog().sources.values())


def seed_catalog_to_db() -> None:
    """
    Seed source/passage catalog into SQL tables once per startup.

    Existing rows are preserved (idempotent).
    """
    catalog = load_catalog()
    with get_db_session() as db:
        for source in catalog.sources.values():
            if db.get(SourceDocumentModel, source.id):
                continue
            db.add(
                SourceDocumentModel(
                    id=source.id,
                    title=source.title,
                    author=source.author,
                    era=source.era,
                    language=source.language,
                    license=source.license,
                    url=source.url,
                    citation_policy=source.citation_policy,
                )
            )

        for passage in catalog.passages.values():
            if db.get(PassageModel, passage.id):
                continue
            db.add(
                PassageModel(
                    id=passage.id,
                    source_document_id=passage.source_document_id,
                    arabic_text=passage.arabic_text,
                    english_text=passage.english_text,
                    topic_tags=passage.topic_tags,
                )
            )

        db.commit()


def count_passages_in_db() -> int:
    with get_db_session() as db:
        return len(db.exec(select(PassageModel.id)).all())
