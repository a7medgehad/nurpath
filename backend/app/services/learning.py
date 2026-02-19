from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.core.db import get_db_session
from app.models import LessonPathModel, SessionModel
from app.schemas import (
    LearningObjective,
    LessonPath,
    SessionCreateRequest,
    SessionCreateResponse,
    UserLevel,
)


def _base_objectives(level: UserLevel) -> List[LearningObjective]:
    if level == UserLevel.advanced:
        return [
            LearningObjective(
                id="usul-ikhtilaf",
                title="Usul al-Ikhtilaf: Why Scholars Differ",
                difficulty="advanced",
                prerequisites=["fiqh-intro"],
                expected_outcomes=["Understand causes of legal divergence", "Read comparative arguments"],
            ),
            LearningObjective(
                id="fiqh-evidence-weighing",
                title="Evaluating Evidences in Fiqh",
                difficulty="advanced",
                prerequisites=["usul-ikhtilaf"],
                expected_outcomes=["Distinguish explicit text vs interpretation layers"],
            ),
        ]

    if level == UserLevel.intermediate:
        return [
            LearningObjective(
                id="fiqh-intro",
                title="Introduction to Fiqh Method and Evidence",
                difficulty="intermediate",
                expected_outcomes=["Understand school-based reasoning at a high level"],
            ),
            LearningObjective(
                id="wudu-ikhtilaf",
                title="Case Study: Wudu Differences",
                difficulty="intermediate",
                prerequisites=["fiqh-intro"],
                expected_outcomes=["Compare Hanafi and Shafi'i positions fairly"],
            ),
        ]

    return [
        LearningObjective(
            id="islam-iman-ihsan",
            title="Islam, Iman, Ihsan Foundations",
            difficulty="beginner",
            expected_outcomes=["Define Islam, Iman, and Ihsan"],
        ),
        LearningObjective(
            id="purification-basics",
            title="Purification Basics",
            difficulty="beginner",
            prerequisites=["islam-iman-ihsan"],
            expected_outcomes=["Recognize common nullifiers and valid practice basics"],
        ),
    ]

@dataclass
class SessionManager:
    """
    Persistent session manager backed by SQLModel.

    Request payloads and lesson mastery survive process restarts.
    """

    def create(self, req: SessionCreateRequest) -> SessionCreateResponse:
        session_id = str(uuid.uuid4())
        roadmap = _base_objectives(req.level)
        lesson_path = LessonPath(
            session_id=session_id,
            objective_ids=[obj.id for obj in roadmap],
            mastery_state={obj.id: 0.0 for obj in roadmap},
        )

        session_row = SessionModel(
            id=session_id,
            preferred_language=req.preferred_language,
            level=req.level.value,
            goals=req.goals,
            madhhab_preference=req.madhhab_preference,
        )
        lesson_path_row = LessonPathModel(
            session_id=session_id,
            objective_ids=lesson_path.objective_ids,
            mastery_state=lesson_path.mastery_state,
        )

        with get_db_session() as db:
            db.add(session_row)
            db.add(lesson_path_row)
            db.commit()

        return SessionCreateResponse(session_id=session_id, roadmap=roadmap, lesson_path=lesson_path)

    def exists(self, session_id: str) -> bool:
        with get_db_session() as db:
            row = db.get(SessionModel, session_id)
            return row is not None

    def get_session(self, session_id: str) -> Optional[SessionModel]:
        with get_db_session() as db:
            return db.get(SessionModel, session_id)

    def get_roadmap(self, session_id: str) -> List[LearningObjective]:
        session = self.get_session(session_id)
        if session is None:
            return []
        try:
            level = UserLevel(session.level)
        except ValueError:
            level = UserLevel.beginner
        return _base_objectives(level)

    def get_lesson_path(self, session_id: str) -> LessonPath:
        with get_db_session() as db:
            row = db.get(LessonPathModel, session_id)
        if not row:
            return LessonPath(session_id=session_id, objective_ids=[], mastery_state={})
        return LessonPath(
            session_id=session_id,
            objective_ids=row.objective_ids,
            mastery_state=row.mastery_state,
        )

    def update_mastery(self, session_id: str, objective_id: str, delta: float) -> Dict[str, float]:
        with get_db_session() as db:
            row = db.get(LessonPathModel, session_id)
            if row is None:
                raise KeyError(f"Session {session_id} not found")

            mastery_state = dict(row.mastery_state)
            current = mastery_state.get(objective_id, 0.0)
            mastery_state[objective_id] = max(0.0, min(1.0, current + delta))
            row.mastery_state = mastery_state
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.mastery_state
