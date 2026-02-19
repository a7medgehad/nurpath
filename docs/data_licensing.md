# Data Licensing Policy

## Objective

Only ingest sources with clear permission for storage, transformation, and model-assisted retrieval.

## Allowed by Default

- Public-domain texts
- Explicitly open-licensed datasets (CC-BY, CC0, etc.)
- Source collections with documented redistribution rights

## Blocked by Default

- Unlicensed scraped materials
- Ambiguous publisher rights
- Content that forbids redistribution/derivative processing

## Required Metadata

- `source_url`
- `license_name`
- `license_url`
- `verification_date`
- `authenticity_source`
- `review_notes`

## Enforcement

The ingestion job rejects:
- allowlist rows missing required metadata fields
- source entries missing Arabic display metadata (`title_ar`, `citation_policy_ar`)
- source entries without `status=approved` in allowlist
- source entries missing structured authenticity references by source type:
  - Quran: `surah`, `ayah`
  - Hadith: `collection`, `book`, `hadith_number`, `grading_authority`
  - Fiqh: `book`, `volume`, `page`, `madhhab`
