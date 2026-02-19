from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import settings
from app.schemas import AskResponse, CitationIntegrityResult, ScoreGateResult, ValidationResult
from app.services.citation import CitationValidator


def _normalize(text: str) -> str:
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.lower()
    text = re.sub(r"[^\w\u0600-\u06FF\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> set[str]:
    return {token for token in _normalize(text).split() if len(token) > 1}


def _claim_count(answer: str) -> int:
    claims = [part.strip() for part in re.split(r"[.!?؟؛\n]+", answer) if part.strip()]
    return max(1, len(claims))


@dataclass
class ValidationStats:
    pass_count: int = 0
    abstain_count: int = 0


class AnswerValidationService:
    def __init__(self, citation_validator: CitationValidator | None = None) -> None:
        self.citation_validator = citation_validator or CitationValidator()
        self.stats = ValidationStats()

    def _grounding_score(self, response: AskResponse) -> float:
        if not response.evidence_cards:
            return 0.0

        answer_tokens = _tokenize(response.direct_answer)
        evidence_tokens: set[str] = set()
        for card in response.evidence_cards:
            evidence_tokens.update(_tokenize(card.arabic_quote))
            evidence_tokens.update(_tokenize(card.english_quote))

        if not answer_tokens or not evidence_tokens:
            overlap = 0.0
        else:
            overlap = len(answer_tokens.intersection(evidence_tokens)) / len(answer_tokens)

        avg_relevance = sum(card.relevance_score for card in response.evidence_cards) / len(
            response.evidence_cards
        )
        return min(1.0, (0.65 * overlap) + (0.35 * avg_relevance))

    def _faithfulness_score(self, response: AskResponse) -> float:
        if not response.evidence_cards:
            return 0.0

        answer_tokens = _tokenize(response.direct_answer)
        if not answer_tokens:
            return 0.0

        citation_tokens = {
            token
            for card in response.evidence_cards
            for token in _tokenize(card.citation_span + " " + card.passage_id)
        }
        evidence_tokens = {
            token
            for card in response.evidence_cards
            for token in _tokenize(card.arabic_quote + " " + card.english_quote)
        }
        covered = answer_tokens.intersection(evidence_tokens.union(citation_tokens))
        unsupported = answer_tokens.difference(evidence_tokens.union(citation_tokens))
        coverage_ratio = len(covered) / len(answer_tokens)
        unsupported_ratio = len(unsupported) / len(answer_tokens)
        score = coverage_ratio * max(0.0, 1 - (0.35 * unsupported_ratio))
        return max(0.0, min(1.0, score))

    def evaluate(self, response: AskResponse) -> ValidationResult:
        citation_pass = self.citation_validator.validate_response(response)
        claims = _claim_count(response.direct_answer)
        coverage = min(1.0, len(response.evidence_cards) / claims) if citation_pass else 0.0
        citation_integrity_passed = citation_pass and coverage >= 1.0

        grounding_score = self._grounding_score(response)
        faithfulness_score = self._faithfulness_score(response)

        grounding = ScoreGateResult(
            score=round(grounding_score, 4),
            threshold=settings.grounding_threshold,
            passed=grounding_score >= settings.grounding_threshold,
        )
        faithfulness = ScoreGateResult(
            score=round(faithfulness_score, 4),
            threshold=settings.faithfulness_threshold,
            passed=faithfulness_score >= settings.faithfulness_threshold,
        )

        if response.abstained:
            return ValidationResult(
                passed=False,
                citation_integrity=CitationIntegrityResult(
                    passed=citation_integrity_passed,
                    coverage=round(coverage, 4),
                ),
                grounding=grounding,
                faithfulness=faithfulness,
                decision_reason="abstained_by_safety_policy",
            )

        if not citation_integrity_passed:
            reason = "citation_integrity_failed"
        elif not grounding.passed:
            reason = "grounding_below_threshold"
        elif not faithfulness.passed:
            reason = "faithfulness_below_threshold"
        else:
            reason = "passed"

        return ValidationResult(
            passed=reason == "passed",
            citation_integrity=CitationIntegrityResult(
                passed=citation_integrity_passed,
                coverage=round(coverage, 4),
            ),
            grounding=grounding,
            faithfulness=faithfulness,
            decision_reason=reason,
        )

    def apply(self, response: AskResponse, preferred_language: str) -> AskResponse:
        report = self.evaluate(response)
        response.validation = report

        # Composite confidence combines retrieval confidence with grounded validation.
        composite_confidence = (0.4 * response.confidence) + (0.3 * report.grounding.score) + (
            0.3 * report.faithfulness.score
        )
        response.confidence = round(min(0.95, composite_confidence), 3)

        if report.passed:
            self.stats.pass_count += 1
            return response

        self.stats.abstain_count += 1
        if response.abstained:
            return response

        response.abstained = True
        if preferred_language == "ar":
            response.safety_notice = "تم تفعيل وضع التحفظ لأن التحقق من الاستناد لم يستوفِ العتبة المطلوبة."
            response.direct_answer = "تعذر تقديم إجابة موثوقة الآن. راجع الأدلة أو أعد صياغة السؤال بدقة أكبر."
        else:
            response.safety_notice = (
                "Response was switched to abstention because validation thresholds were not met."
            )
            response.direct_answer = (
                "Unable to provide a reliable answer right now. Please review the evidence or refine the question."
            )
        return response

    def stats_snapshot(self) -> ValidationStats:
        return ValidationStats(
            pass_count=self.stats.pass_count,
            abstain_count=self.stats.abstain_count,
        )
