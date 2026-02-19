from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Sequence

from app.schemas import ConflictPair, EvidenceCard, IkhtilafAnalysis, OpinionComparisonItem, Passage

SCHOOL_DISPLAY_EN = {
    "hanafi": "Hanafi",
    "shafii": "Shafi'i",
    "maliki": "Maliki",
    "hanbali": "Hanbali",
    "jafari": "Ja'fari",
    "zahiri": "Zahiri",
}
SCHOOL_DISPLAY_AR = {
    "hanafi": "الحنفي",
    "shafii": "الشافعي",
    "maliki": "المالكي",
    "hanbali": "الحنبلي",
    "jafari": "الجعفري",
    "zahiri": "الظاهري",
}
SCHOOL_TAGS = set(SCHOOL_DISPLAY_EN.keys())

TOPIC_LABEL_AR = {
    "fiqh": "الفقه",
    "aqidah": "العقيدة",
    "akhlaq": "الأخلاق",
    "history": "التاريخ",
    "wudu": "الوضوء",
    "general": "المسألة",
}

NEGATIVE_STANCE_TOKENS = (
    "does not nullify",
    "do not nullify",
    "does not invalidate",
    "do not invalidate",
    "لا ينقض",
    "لا يَنقُض",
)
POSITIVE_STANCE_TOKENS = (
    "invalidate wudu",
    "invalidating wudu",
    "nullifying wudu",
    "nullify wudu",
    "ينقض الوضوء",
    "ناقض للوضوء",
)
TOPIC_NOISE_TAGS = SCHOOL_TAGS.union({"ikhtilaf"})


@dataclass
class _SchoolOpinion:
    school_key: str
    stance: str
    evidence_ids: List[str]
    topic_tags: set[str]


@dataclass
class IkhtilafDetectionResult:
    opinion_comparison: List[OpinionComparisonItem]
    analysis: IkhtilafAnalysis


def _detect_stance(text: str) -> str:
    normalized = text.lower()
    if any(token in normalized for token in NEGATIVE_STANCE_TOKENS):
        return "does_not_invalidate"
    if any(token in normalized for token in POSITIVE_STANCE_TOKENS):
        return "invalidates"
    return "unclear"


def _extract_school(tags: Sequence[str], text: str, passage_id: str) -> str | None:
    for tag in tags:
        t = tag.lower()
        if t in SCHOOL_TAGS:
            return t

    lookup = f"{text} {passage_id}".lower()
    for school in SCHOOL_TAGS:
        if school in lookup:
            return school

    return None


def _stance_summary(stance: str, preferred_language: str) -> str:
    is_en = preferred_language == "en"
    if stance == "invalidates":
        return (
            "Considers this act nullifying wudu."
            if is_en
            else "يعتبر هذا الفعل ناقضًا للوضوء."
        )
    if stance == "does_not_invalidate":
        return (
            "Does not consider this act by itself nullifying wudu."
            if is_en
            else "لا يعتبر هذا الفعل وحده ناقضًا للوضوء."
        )
    return (
        "Evidence is present without explicit nullification polarity."
        if is_en
        else "الدليل موجود دون تصريح واضح باتجاه الحكم."
    )


def _school_label(school_key: str, preferred_language: str) -> str:
    return (
        SCHOOL_DISPLAY_AR.get(school_key, school_key)
        if preferred_language == "ar"
        else SCHOOL_DISPLAY_EN.get(school_key, school_key)
    )


def _build_summary(status: str, preferred_language: str, topic: str, schools: List[str]) -> str:
    if preferred_language == "en":
        if status == "ikhtilaf":
            return (
                f"Valid disagreement detected on '{topic}' across: "
                + ", ".join(schools)
                + "."
            )
        if status == "consensus":
            return (
                f"Multiple schools align on '{topic}': " + ", ".join(schools) + "."
            )
        return "Not enough cross-school evidence to classify consensus or disagreement."

    topic_ar = TOPIC_LABEL_AR.get(topic, topic)
    if status == "ikhtilaf":
        return f"تم رصد اختلاف معتبر في '{topic_ar}' بين: " + "، ".join(schools) + "."
    if status == "consensus":
        return f"يوجد اتفاق بين أكثر من مذهب في '{topic_ar}': " + "، ".join(schools) + "."
    return "لا توجد أدلة كافية عبر مدارس متعددة للحكم باتفاق أو اختلاف."


def analyze_ikhtilaf(
    evidence_cards: List[EvidenceCard],
    passages: Dict[str, Passage],
    preferred_language: str,
) -> IkhtilafDetectionResult:
    opinions: Dict[str, _SchoolOpinion] = {}

    for card in evidence_cards:
        passage = passages.get(card.passage_id)
        if passage is None:
            continue

        text = f"{passage.arabic_text} {passage.english_text}"
        school_key = _extract_school(passage.topic_tags, text=text, passage_id=passage.id)
        if not school_key:
            continue

        stance = _detect_stance(text)
        topic_tags = {t.lower() for t in passage.topic_tags if t.lower() not in TOPIC_NOISE_TAGS}
        opinion = opinions.get(school_key)
        if opinion is None:
            opinions[school_key] = _SchoolOpinion(
                school_key=school_key,
                stance=stance,
                evidence_ids=[card.passage_id],
                topic_tags=topic_tags,
            )
            continue

        opinion.evidence_ids.append(card.passage_id)
        opinion.topic_tags.update(topic_tags)
        if opinion.stance == "unclear" and stance != "unclear":
            opinion.stance = stance
        elif opinion.stance != stance and stance != "unclear":
            opinion.stance = "unclear"

    opinion_comparison: List[OpinionComparisonItem] = []
    for school_key in sorted(opinions.keys()):
        opinion = opinions[school_key]
        opinion_comparison.append(
            OpinionComparisonItem(
                school_or_scholar=_school_label(school_key, preferred_language),
                stance_summary=_stance_summary(opinion.stance, preferred_language),
                stance_type=opinion.stance,
                evidence_passage_ids=sorted(set(opinion.evidence_ids)),
            )
        )

    if not opinions:
        analysis = IkhtilafAnalysis(
            status="insufficient",
            summary=_build_summary("insufficient", preferred_language, "general", []),
            compared_schools=[],
            shared_topic_tags=[],
            conflict_pairs=[],
        )
        return IkhtilafDetectionResult(opinion_comparison=opinion_comparison, analysis=analysis)

    compared_school_names = [_school_label(k, preferred_language) for k in sorted(opinions.keys())]
    topic_sets = [entry.topic_tags for entry in opinions.values() if entry.topic_tags]
    if topic_sets:
        shared_tags = sorted(set.intersection(*topic_sets)) if len(topic_sets) > 1 else sorted(topic_sets[0])
    else:
        shared_tags = []
    issue_topic = shared_tags[0] if shared_tags else "general"

    explicit_stances = {entry.stance for entry in opinions.values() if entry.stance != "unclear"}
    if len(opinions) >= 2 and len(explicit_stances) >= 2:
        status = "ikhtilaf"
    elif len(opinions) >= 2 and len(explicit_stances) == 1:
        status = "consensus"
    else:
        status = "insufficient"

    conflict_pairs: List[ConflictPair] = []
    if status == "ikhtilaf":
        for school_a, school_b in combinations(sorted(opinions.keys()), 2):
            a = opinions[school_a]
            b = opinions[school_b]
            if "unclear" in {a.stance, b.stance} or a.stance == b.stance:
                continue
            conflict_pairs.append(
                ConflictPair(
                    school_a=_school_label(school_a, preferred_language),
                    school_b=_school_label(school_b, preferred_language),
                    issue_topic=issue_topic,
                    evidence_passage_ids=sorted(set(a.evidence_ids + b.evidence_ids)),
                )
            )

    analysis = IkhtilafAnalysis(
        status=status,
        summary=_build_summary(status, preferred_language, issue_topic, compared_school_names),
        compared_schools=compared_school_names,
        shared_topic_tags=shared_tags,
        conflict_pairs=conflict_pairs,
    )
    return IkhtilafDetectionResult(opinion_comparison=opinion_comparison, analysis=analysis)
