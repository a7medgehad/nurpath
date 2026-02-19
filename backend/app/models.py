from __future__ import annotations

from typing import Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class SourceDocumentModel(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str
    author: str
    era: str
    language: str
    license: str
    url: str
    citation_policy: str


class PassageModel(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source_document_id: str = Field(index=True)
    arabic_text: str
    english_text: str
    topic_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class SessionModel(SQLModel, table=True):
    id: str = Field(primary_key=True)
    preferred_language: str
    level: str
    goals: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    madhhab_preference: Optional[str] = None


class LessonPathModel(SQLModel, table=True):
    session_id: str = Field(primary_key=True)
    objective_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    mastery_state: dict[str, float] = Field(default_factory=dict, sa_column=Column(JSON))
