"""Retrieval metrics.

All metrics work at the *article* level: retrieved chunk ids are mapped to article keys
and de-duplicated (keeping the first occurrence) before ranking.

Why de-duplicate: an article has several paragraphs in two languages. If the top 5 are
four paragraphs of one wrong article plus the right one, without de-duplication the right
article sits at rank 5; with it, rank 2. We report how many *distinct articles* a user has
to look through, which is what matters for a compliance engineer.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from normnavigator.schema import article_key_from_chunk_id


def dedupe_to_articles(chunk_ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for cid in chunk_ids:
        key = article_key_from_chunk_id(cid)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def first_relevant_rank(retrieved_articles: Sequence[str], gold: set[str]) -> int | None:
    for rank, art in enumerate(retrieved_articles, start=1):
        if art in gold:
            return rank
    return None


def hit_at_k(retrieved_articles: Sequence[str], gold: set[str], k: int) -> float:
    """1.0 if any gold article is in the top k, else 0.0."""
    r = first_relevant_rank(retrieved_articles[:k], gold)
    return 1.0 if r is not None else 0.0


def reciprocal_rank(
    retrieved_articles: Sequence[str], gold: set[str], k: int | None = None
) -> float:
    """1/rank of the first gold article (0 if none in top k). Mean over queries = MRR."""
    pool = retrieved_articles[:k] if k else retrieved_articles
    r = first_relevant_rank(pool, gold)
    return 1.0 / r if r else 0.0


def recall_at_k(retrieved_articles: Sequence[str], gold: set[str], k: int) -> float:
    """Fraction of gold articles found in top k (matters for multi-article questions)."""
    if not gold:
        raise ValueError("gold set must not be empty")
    return len(set(retrieved_articles[:k]) & gold) / len(gold)
