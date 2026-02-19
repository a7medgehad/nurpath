from app.services.ingestion import validate_metadata_rows, validate_source_record


def test_validate_metadata_rows_requires_authenticity_fields() -> None:
    ok, errors = validate_metadata_rows(
        [
            {
                "source_url": "https://example.org",
                "license_name": "Public Domain",
                "license_url": "https://example.org/license",
                "verification_date": "2026-02-19",
            }
        ]
    )
    assert ok is False
    assert any("authenticity_source" in err for err in errors)
    assert any("review_notes" in err for err in errors)


def test_validate_source_record_rejects_missing_arabic_fields() -> None:
    source = {
        "id": "src_x",
        "title": "Sample",
        "author": "Author",
        "author_ar": "المؤلف",
        "era": "classical",
        "language": "ar",
        "license": "Public Domain",
        "url": "https://example.org",
        "citation_policy": "policy",
        "source_type": "quran",
        "authenticity_level": "qat_i",
        "passages": [
            {
                "id": "p_x",
                "arabic_text": "نص عربي",
                "english_text": "english text",
                "passage_url": "https://example.org/passage/1",
                "topic_tags": ["fiqh"],
                "reference": {"surah": "1", "ayah": "1", "display_ar": "سورة الفاتحة، الآية ١"},
            }
        ],
    }
    errors = validate_source_record(source)
    assert any("title_ar" in err for err in errors)
    assert any("citation_policy_ar" in err for err in errors)


def test_validate_source_record_accepts_complete_fiqh_source() -> None:
    source = {
        "id": "src_fiqh_ok",
        "title": "Fiqh Source",
        "title_ar": "مرجع فقهي",
        "author": "Author",
        "author_ar": "المؤلف",
        "era": "classical",
        "language": "ar",
        "license": "Public Domain",
        "url": "https://example.org",
        "citation_policy": "Cite book/page",
        "citation_policy_ar": "اذكر الكتاب والصفحة",
        "source_type": "fiqh",
        "authenticity_level": "mu_tabar",
        "passages": [
            {
                "id": "p_ok",
                "arabic_text": "نص عربي فقهي",
                "english_text": "A fiqh excerpt",
                "passage_url": "https://example.org/fiqh/1/17",
                "topic_tags": ["fiqh", "wudu", "hanafi"],
                "reference": {
                    "book": "Al-Hidaya",
                    "volume": "1",
                    "page": "17",
                    "madhhab": "Hanafi",
                    "display_ar": "الهداية، الجزء ١، الصفحة ١٧",
                },
            }
        ],
    }
    errors = validate_source_record(source)
    assert errors == []


def test_validate_source_record_rejects_missing_passage_url_for_indexable_source() -> None:
    source = {
        "id": "src_no_passage_url",
        "title": "Sample",
        "title_ar": "عينة",
        "author": "Author",
        "author_ar": "المؤلف",
        "era": "classical",
        "language": "ar",
        "license": "Public Domain",
        "url": "https://example.org",
        "citation_policy": "Cite",
        "citation_policy_ar": "اذكر المرجع",
        "source_type": "hadith",
        "authenticity_level": "sahih",
        "passages": [
            {
                "id": "p_no_url",
                "arabic_text": "نص",
                "english_text": "text",
                "topic_tags": ["hadith"],
                "reference": {
                    "collection": "Sahih al-Bukhari",
                    "book": "Book",
                    "hadith_number": "10",
                    "grading_authority": "Sahih",
                    "display_ar": "مرجع",
                },
            }
        ],
    }
    errors = validate_source_record(source)
    assert any("missing passage_url" in err for err in errors)
