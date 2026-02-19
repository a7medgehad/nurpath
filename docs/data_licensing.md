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
- `attribution_text`
- `verification_date`

## Enforcement

The ingestion job rejects rows missing any required metadata fields.
