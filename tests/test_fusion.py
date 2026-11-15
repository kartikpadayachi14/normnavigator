import pytest

from normnavigator.retrieval.fusion import reciprocal_rank_fusion, weighted_fusion


def test_rrf_rewards_docs_ranked_well_by_both():
    bm25 = [("a", 12.0), ("b", 9.0), ("c", 1.0)]
    vec = [("b", 0.91), ("c", 0.80), ("a", 0.10)]
    fused = reciprocal_rank_fusion([bm25, vec], k=60)
    # b: 1/62 + 1/61 ; a: 1/61 + 1/63 ; c: 1/63 + 1/62  -> b > a > c
    assert [d for d, _ in fused] == ["b", "a", "c"]
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_ignores_raw_score_scale():
    # Huge BM25 scores must not matter — only ranks do.
    small = reciprocal_rank_fusion([[("x", 1.0), ("y", 0.5)]])
    huge = reciprocal_rank_fusion([[("x", 1e6), ("y", 5e5)]])
    assert small == huge


def test_rrf_doc_in_one_list_only_still_included():
    fused = dict(reciprocal_rank_fusion([[("a", 1.0)], [("b", 1.0)]]))
    assert set(fused) == {"a", "b"}


def test_rrf_duplicate_in_one_list_counted_once():
    fused = dict(reciprocal_rank_fusion([[("a", 2.0), ("a", 1.0)]], k=60))
    assert fused["a"] == pytest.approx(1 / 61)


def test_rrf_top_n_and_invalid_k():
    assert len(reciprocal_rank_fusion([[("a", 1), ("b", 1), ("c", 1)]], top_n=2)) == 2
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], k=0)


def test_weighted_alpha_extremes_reproduce_single_retriever():
    bm25 = [("a", 10.0), ("b", 5.0), ("c", 0.0)]
    vec = [("c", 0.9), ("b", 0.5), ("a", 0.1)]
    assert [d for d, _ in weighted_fusion(bm25, vec, alpha=0.0)] == ["a", "b", "c"]
    assert [d for d, _ in weighted_fusion(bm25, vec, alpha=1.0)] == ["c", "b", "a"]


def test_weighted_balanced():
    bm25 = [("a", 10.0), ("b", 5.0), ("c", 0.0)]  # normalised: a=1, b=.5, c=0
    vec = [("c", 0.9), ("b", 0.8), ("a", 0.1)]  # normalised: c=1, b=.875, a=0
    fused = dict(weighted_fusion(bm25, vec, alpha=0.5))
    assert fused["b"] == pytest.approx(0.5 * 0.875 + 0.5 * 0.5)
    assert max(fused, key=fused.get) == "b"


def test_weighted_equal_scores_and_bad_alpha():
    fused = dict(weighted_fusion([("a", 3.0), ("b", 3.0)], [], alpha=0.5))
    assert fused == {"a": 0.5, "b": 0.5}
    with pytest.raises(ValueError):
        weighted_fusion([], [], alpha=1.5)
