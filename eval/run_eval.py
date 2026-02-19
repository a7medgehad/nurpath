#!/usr/bin/env python3
"""Minimal local evaluator for NurPath API behavior."""

from __future__ import annotations

import json
from pathlib import Path

import requests

BASE = "http://localhost:8000"


def read_dataset(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def main() -> None:
    session = requests.post(
        f"{BASE}/v1/sessions",
        json={"preferred_language": "en", "level": "beginner", "goals": ["evaluation"]},
        timeout=30,
    )
    session.raise_for_status()
    sid = session.json()["session_id"]

    total = 0
    citation_ok = 0
    abstains = 0

    for row in read_dataset(Path(__file__).parent / "sample_qa.jsonl"):
        total += 1
        r = requests.post(
            f"{BASE}/v1/ask",
            json={"session_id": sid, "question": row["question"], "preferred_language": "en"},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()

        if body.get("abstained"):
            abstains += 1

        cards = body.get("evidence_cards", [])
        if body.get("abstained") or (cards and all(c["citation_span"] == c["passage_id"] for c in cards)):
            citation_ok += 1

    print(
        json.dumps(
            {
                "total": total,
                "citation_integrity_rate": round(citation_ok / max(total, 1), 3),
                "abstain_rate": round(abstains / max(total, 1), 3),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
