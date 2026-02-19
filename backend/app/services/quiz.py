from __future__ import annotations

from typing import Dict

from app.schemas import QuizGenerateResponse, QuizGradeResponse, QuizQuestion
from app.services.learning import SessionManager


class QuizService:
    def __init__(self, sessions: SessionManager) -> None:
        self.sessions = sessions

    def generate(
        self,
        objective_id: str,
        num_questions: int,
        preferred_language: str = "ar",
    ) -> QuizGenerateResponse:
        questions = []
        is_ar = preferred_language == "ar"
        for i in range(num_questions):
            questions.append(
                QuizQuestion(
                    id=f"{objective_id}-q{i+1}",
                    prompt=(
                        "اكتب نقطة علمية أساسية واحدة من هذا الدرس بأسلوبك."
                        if is_ar
                        else f"Summarize one key point for objective '{objective_id}' in your own words."
                    ),
                    expected_keywords=(
                        ["دليل", "عالم", "اختلاف", "مرجع"]
                        if is_ar
                        else ["evidence", "scholar", "difference"]
                    ),
                )
            )
        return QuizGenerateResponse(objective_id=objective_id, questions=questions)

    def grade(self, session_id: str, objective_id: str, answers: Dict[str, str]) -> QuizGradeResponse:
        feedback: Dict[str, str] = {}
        passed = 0
        session = self.sessions.get_session(session_id)
        is_ar = (session.preferred_language if session else "en") == "ar"
        expected_keywords = (
            ["دليل", "عالم", "اختلاف", "مرجع", "استدلال"]
            if is_ar
            else ["evidence", "scholar", "difference", "citation"]
        )

        for qid, answer in answers.items():
            score = 0
            tokens = answer.lower().split()
            for kw in expected_keywords:
                if kw in tokens:
                    score += 1

            if score >= 1:
                passed += 1
                feedback[qid] = (
                    "جيد: احرص في المرة القادمة على ذكر مرجع محدد."
                    if is_ar
                    else "Good: include explicit source references next time."
                )
            else:
                feedback[qid] = (
                    "يحتاج إلى تحسين: اذكر الدليل والسياق العلمي."
                    if is_ar
                    else "Needs improvement: mention evidence and scholarly context."
                )

        total = max(len(answers), 1)
        ratio = passed / total
        delta = 0.2 if ratio >= 0.6 else 0.05
        updated = self.sessions.update_mastery(session_id=session_id, objective_id=objective_id, delta=delta)

        return QuizGradeResponse(
            objective_id=objective_id,
            score=ratio,
            feedback=feedback,
            updated_mastery=updated,
        )
