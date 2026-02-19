from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from sqlmodel import select

from app.core.config import settings
from app.core.db import get_db_session
from app.models import PassageModel, SourceDocumentModel
from app.schemas import Passage, ReferenceData, SourceDocument
from app.services.ingestion import load_allowlist, validate_source_record


@dataclass
class CatalogStore:
    sources: Dict[str, SourceDocument]
    passages: Dict[str, Passage]


TOPIC_ALIASES = {
    "fiqh": {"fiqh", "فقه"},
    "aqidah": {"aqidah", "عقيدة"},
    "akhlaq": {"akhlaq", "أخلاق"},
    "history": {"history", "تاريخ", "سيرة"},
    "language_learning": {"language_learning", "تعلم اللغة"},
}


def _resolve_catalog_path() -> Path:
    # Path is relative to backend/ in default local setup.
    candidate = Path(__file__).resolve().parents[3] / "data" / "samples" / "sources.json"
    if candidate.exists():
        return candidate

    configured = Path(settings.source_catalog_path)
    if configured.exists():
        return configured

    raise FileNotFoundError("Could not resolve sources catalog path.")


def _resolve_allowlist_path() -> Path:
    candidate = Path(__file__).resolve().parents[3] / "data" / "allowlist.csv"
    if candidate.exists():
        return candidate
    raise FileNotFoundError("Could not resolve allowlist path.")


@lru_cache(maxsize=1)
def load_catalog() -> CatalogStore:
    data = json.loads(_resolve_catalog_path().read_text(encoding="utf-8"))
    allowlist = load_allowlist(_resolve_allowlist_path())

    sources: Dict[str, SourceDocument] = {}
    passages: Dict[str, Passage] = {}

    for row in data:
        source_id = row.get("id", "")
        allowlist_row = allowlist.get(source_id)
        if allowlist_row is None or allowlist_row.status.lower() != "approved":
            continue

        validation_errors = validate_source_record(row)
        if validation_errors:
            joined = "; ".join(validation_errors)
            raise ValueError(f"Catalog validation failed for source '{source_id}': {joined}")

        source = SourceDocument(
            id=source_id,
            title=row["title"],
            title_ar=row["title_ar"],
            author=row["author"],
            author_ar=row["author_ar"],
            era=row["era"],
            language=row["language"],
            license=row["license"],
            url=row["url"],
            citation_policy=row["citation_policy"],
            citation_policy_ar=row["citation_policy_ar"],
            source_type=row["source_type"],
            authenticity_level=row["authenticity_level"],
        )
        sources[source.id] = source

        for p in row.get("passages", []):
            passage = Passage(
                id=p["id"],
                source_document_id=source.id,
                arabic_text=p["arabic_text"],
                english_text=p["english_text"],
                passage_url=p["passage_url"],
                topic_tags=p.get("topic_tags", []),
                reference=ReferenceData(**p["reference"]) if p.get("reference") else None,
            )
            passages[passage.id] = passage

    return CatalogStore(sources=sources, passages=passages)


def list_sources() -> List[SourceDocument]:
    return list(load_catalog().sources.values())


def filter_sources(
    language: Optional[str] = None,
    topic: Optional[str] = None,
    q: Optional[str] = None,
    source_type: Optional[str] = None,
    authenticity_level: Optional[str] = None,
) -> List[SourceDocument]:
    catalog = load_catalog()
    candidates = list(catalog.sources.values())

    if language:
        candidates = [s for s in candidates if language.lower() in s.language.lower()]

    if topic:
        topic_l = topic.lower()
        accepted = set([topic_l])
        for canonical, aliases in TOPIC_ALIASES.items():
            if topic_l in aliases:
                accepted = set(aliases).union({canonical})
                break

        source_ids = {
            p.source_document_id
            for p in catalog.passages.values()
            if any(tag.lower() in accepted for tag in p.topic_tags)
        }
        candidates = [s for s in candidates if s.id in source_ids]

    if q:
        q_l = q.lower()
        candidates = [
            s
            for s in candidates
            if q_l in s.title.lower()
            or q_l in s.title_ar.lower()
            or q_l in s.author.lower()
            or q_l in s.author_ar.lower()
            or q_l in s.id.lower()
        ]

    if source_type:
        source_type_l = source_type.lower()
        candidates = [s for s in candidates if s.source_type.lower() == source_type_l]

    if authenticity_level:
        auth_l = authenticity_level.lower()
        candidates = [s for s in candidates if s.authenticity_level.lower() == auth_l]

    return candidates


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
