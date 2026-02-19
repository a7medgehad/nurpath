from app.services.reranker import TokenOverlapReranker


def test_token_overlap_reranker_scores_relevant_passage_higher() -> None:
    reranker = TokenOverlapReranker()
    query = "ما حكم الوضوء عند لمس المرأة"
    passages = [
        "هذه فقرة عن الصيام والزكاة دون ذكر الوضوء.",
        "الفقهاء اختلفوا في لمس المرأة وهل ينقض الوضوء.",
    ]
    scores = reranker.rerank(query, passages)
    assert len(scores) == 2
    assert scores[1] > scores[0]


def test_token_overlap_reranker_normalizes_scores() -> None:
    reranker = TokenOverlapReranker()
    scores = reranker.rerank("وضوء", ["وضوء", "صيام"])
    assert all(0.0 <= score <= 1.0 for score in scores)
