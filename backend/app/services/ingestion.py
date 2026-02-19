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
    "verification_date",
    "authenticity_source",
    "review_notes",
]

REQUIRED_ALLOWLIST_COLUMNS = [
    "source_id",
    "license_name",
    "license_url",
    "verified_by",
    "verification_date",
    "status",
    "authenticity_source",
    "review_notes",
]

REQUIRED_SOURCE_FIELDS = [
    "id",
    "title",
    "title_ar",
    "author",
    "author_ar",
    "era",
    "language",
    "license",
    "url",
    "citation_policy",
    "citation_policy_ar",
    "source_type",
    "authenticity_level",
]

REQUIRED_REFERENCE_FIELDS_BY_TYPE = {
    "quran": ("surah", "ayah"),
    "hadith": ("collection", "book", "hadith_number", "grading_authority"),
    "fiqh": ("book", "volume", "page", "madhhab"),
}


@dataclass
class LicenseRecord:
    source_id: str
    license_name: str
    license_url: str
    verification_date: str
    status: str
    authenticity_source: str
    review_notes: str


def load_allowlist(path: Path) -> dict[str, LicenseRecord]:
    records: dict[str, LicenseRecord] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Allowlist is missing header row")
        missing = [col for col in REQUIRED_ALLOWLIST_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Allowlist is missing required columns: {', '.join(missing)}")
        for row in reader:
            records[row["source_id"]] = LicenseRecord(
                source_id=row["source_id"],
                license_name=row["license_name"],
                license_url=row["license_url"],
                verification_date=row["verification_date"],
                status=row["status"],
                authenticity_source=row["authenticity_source"],
                review_notes=row["review_notes"],
            )
    return records


def validate_metadata_rows(rows: Iterable[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        for field in REQUIRED_METADATA:
            if not row.get(field):
                errors.append(f"row {i}: missing {field}")
    return len(errors) == 0, errors


def validate_source_record(source: dict) -> list[str]:
    errors: list[str] = []
    source_id = source.get("id", "<missing-id>")

    for field in REQUIRED_SOURCE_FIELDS:
        if not source.get(field):
            errors.append(f"source {source_id}: missing {field}")

    source_type = source.get("source_type")
    if source_type not in REQUIRED_REFERENCE_FIELDS_BY_TYPE:
        errors.append(
            f"source {source_id}: invalid source_type '{source_type}', expected one of "
            + ", ".join(REQUIRED_REFERENCE_FIELDS_BY_TYPE.keys())
        )

    authenticity = source.get("authenticity_level")
    if source_type == "quran" and authenticity != "qat_i":
        errors.append(f"source {source_id}: quran sources must have authenticity_level='qat_i'")
    if source_type == "hadith" and authenticity not in {"sahih", "hasan"}:
        errors.append(f"source {source_id}: hadith sources must be sahih or hasan")
    if source_type == "fiqh" and authenticity != "mu_tabar":
        errors.append(f"source {source_id}: fiqh sources must have authenticity_level='mu_tabar'")

    passages = source.get("passages", [])
    is_indexable = bool(source.get("indexable", True))
    if not passages:
        errors.append(f"source {source_id}: passages must not be empty")
        return errors

    required_reference_fields = REQUIRED_REFERENCE_FIELDS_BY_TYPE.get(source_type, ())
    for i, passage in enumerate(passages, start=1):
        pid = passage.get("id", f"<missing-passage-id-{i}>")
        if not passage.get("arabic_text"):
            errors.append(f"source {source_id} passage {pid}: missing arabic_text")
        if not passage.get("english_text"):
            errors.append(f"source {source_id} passage {pid}: missing english_text")
        if is_indexable and not passage.get("passage_url"):
            errors.append(f"source {source_id} passage {pid}: missing passage_url for indexable source")
        if not passage.get("reference"):
            errors.append(f"source {source_id} passage {pid}: missing reference object")
            continue

        for ref_field in required_reference_fields:
            if not passage["reference"].get(ref_field):
                errors.append(
                    f"source {source_id} passage {pid}: missing reference.{ref_field}"
                )
        if not passage["reference"].get("display_ar"):
            errors.append(f"source {source_id} passage {pid}: missing reference.display_ar")
    return errors


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
