import pytest

from normnavigator.eval.metrics import (
    dedupe_to_articles,
    hit_at_k,
    recall_at_k,
    reciprocal_rank,
)
from normnavigator.schema import Chunk, article_key_from_chunk_id

RETRIEVED = [
    "2023/1230:en:art3:p1",
    "2023/1230:de:art3:p2",  # same article as above, other language -> deduped
    "2023/1230:en:art18:p2",
    "2024/1689:de:art6",
]


def test_chunk_ids_and_article_key():
    c = Chunk(regulation="2023/1230", lang="de", article="18", paragraph="2", text="...")
    assert c.chunk_id == "2023/1230:de:art18:p2"
    assert c.article_key == "2023/1230:art18"
    assert article_key_from_chunk_id(c.chunk_id) == c.article_key
    with pytest.raises(ValueError):
        article_key_from_chunk_id("garbage")


def test_dedupe_keeps_first_occurrence_across_languages():
    assert dedupe_to_articles(RETRIEVED) == ["2023/1230:art3", "2023/1230:art18", "2024/1689:art6"]


def test_hit_and_rr():
    arts = dedupe_to_articles(RETRIEVED)
    gold = {"2023/1230:art18"}
    assert hit_at_k(arts, gold, 1) == 0.0
    assert hit_at_k(arts, gold, 2) == 1.0
    assert reciprocal_rank(arts, gold) == pytest.approx(0.5)
    assert reciprocal_rank(arts, {"missing:art1"}) == 0.0
    assert reciprocal_rank(arts, gold, k=1) == 0.0  # cut-off respected


def test_recall_multi_gold():
    arts = dedupe_to_articles(RETRIEVED)
    gold = {"2023/1230:art18", "2024/1689:art6", "2023/988:art9"}
    assert recall_at_k(arts, gold, 3) == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        recall_at_k(arts, set(), 3)
