from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REQUIRED_METADATA = [
    "source_url",
    "license_name",
    "license_url",
    "attribution_text",
    "verification_date",
]


@dataclass
class LicenseRecord:
    source_id: str
    status: str


def load_allowlist(path: Path) -> dict[str, LicenseRecord]:
    records: dict[str, LicenseRecord] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records[row["source_id"]] = LicenseRecord(source_id=row["source_id"], status=row["status"])
    return records


def validate_metadata_rows(rows: Iterable[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        for field in REQUIRED_METADATA:
            if not row.get(field):
                errors.append(f"row {i}: missing {field}")
    return len(errors) == 0, errors


def chunk_text(text: str, chunk_size: int = 320, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = words[start : start + chunk_size]
        if not chunk:
            break
        chunks.append(" ".join(chunk))
        if start + chunk_size >= len(words):
            break
    return chunks


def load_json_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))
