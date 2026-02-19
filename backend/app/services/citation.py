from __future__ import annotations

from app.schemas import AskResponse


class CitationValidator:
    @staticmethod
    def validate_response(response: AskResponse) -> bool:
        if response.abstained:
            return True

        if not response.evidence_cards:
            return False

        for card in response.evidence_cards:
            if not card.citation_span or card.passage_id != card.citation_span:
                return False

        return True
