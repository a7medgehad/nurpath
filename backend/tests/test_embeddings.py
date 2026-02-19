from app.services.embeddings import (
    HashEmbedder,
    prepare_texts_for_embedding,
)


def test_e5_query_prefix_is_applied() -> None:
    texts = prepare_texts_for_embedding(
        ["ما حكم لمس الزوجة؟"],
        mode="query",
        model_name="intfloat/multilingual-e5-large",
    )
    assert texts[0].startswith("query: ")


def test_e5_passage_prefix_is_applied() -> None:
    texts = prepare_texts_for_embedding(
        ["ومس المرأة مختلف فيه بين الفقهاء."],
        mode="passage",
        model_name="intfloat/multilingual-e5-large",
    )
    assert texts[0].startswith("passage: ")


def test_non_e5_models_do_not_prefix() -> None:
    raw = ["hello world"]
    texts = prepare_texts_for_embedding(
        raw,
        mode="query",
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    assert texts == raw


def test_hash_embedder_keeps_dimension_consistent() -> None:
    embedder = HashEmbedder(384)
    vectors = embedder.embed_queries(["a", "b"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
