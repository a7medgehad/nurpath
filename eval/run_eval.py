#!/usr/bin/env python3
"""Local evaluator for NurPath retrieval and answer quality."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

BASE = "http://localhost:8000"


def read_dataset(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE)
    parser.add_argument("--profile-label", default="active")
    args = parser.parse_args()

    session = requests.post(
        f"{args.base_url}/v1/sessions",
        json={"preferred_language": "en", "level": "beginner", "goals": ["evaluation"]},
        timeout=30,
    )
    session.raise_for_status()
    sid = session.json()["session_id"]

    total = 0
    hit_at_k = 0
    citation_ok = 0
    validation_passed = 0
    abstains = 0
    ikhtilaf_expected = 0
    ikhtilaf_detected = 0

    for row in read_dataset(Path(__file__).parent / "sample_qa.jsonl"):
        total += 1
        r = requests.post(
            f"{args.base_url}/v1/ask",
            json={"session_id": sid, "question": row["question"], "preferred_language": "en"},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()

        cards = body.get("evidence_cards", [])
        if cards:
            hit_at_k += 1

        validation = body.get("validation", {})
        citation_integrity = validation.get("citation_integrity", {})
        if citation_integrity.get("passed"):
            citation_ok += 1
        if validation.get("passed"):
            validation_passed += 1
        if body.get("abstained"):
            abstains += 1

        if row.get("requires_ikhtilaf"):
            ikhtilaf_expected += 1
            if body.get("ikhtilaf_analysis", {}).get("status") == "ikhtilaf":
                ikhtilaf_detected += 1

    print(
        json.dumps(
            {
                "profile_label": args.profile_label,
                "total": total,
                "retrieval_hit_at_k": round(hit_at_k / max(total, 1), 3),
                "citation_integrity_rate": round(citation_ok / max(total, 1), 3),
                "validation_pass_rate": round(validation_passed / max(total, 1), 3),
                "abstain_rate": round(abstains / max(total, 1), 3),
                "ikhtilaf_detection_rate": round(ikhtilaf_detected / max(ikhtilaf_expected, 1), 3),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
