"""Score fusion for hybrid retrieval.

Problem: BM25 scores (unbounded, e.g. 0..30) and cosine similarities (-1..1) live on
different scales, so you cannot just add them.

Two standard fixes, both implemented so we can compare them in the evaluation:

1. Reciprocal Rank Fusion (RRF, Cormack et al. 2009): ignore raw scores, use only ranks.
   score(d) = sum over retrievers of 1 / (k + rank(d)).  k=60 is the value from the paper;
   it damps the influence of the very top ranks so one retriever cannot dominate.
   Pro: no tuning, robust to scale. Con: throws away how *confident* each retriever was.

2. Weighted score fusion: min-max normalise each retriever's scores to 0..1, then
   score(d) = alpha * vector + (1 - alpha) * bm25.
   Pro: keeps confidence information. Con: alpha must be tuned, and min-max is sensitive
   to outliers in a single query's result list.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

RankedList = Sequence[tuple[str, float]]  # [(doc_id, score), ...] best first


def reciprocal_rank_fusion(
    ranked_lists: Sequence[RankedList], k: int = 60, top_n: int | None = None
) -> list[tuple[str, float]]:
    if k <= 0:
        raise ValueError("k must be positive")
    fused: dict[str, float] = {}
    for ranked in ranked_lists:
        seen: set[str] = set()
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            if doc_id in seen:  # a retriever should not vote twice for the same doc
                continue
            seen.add(doc_id)
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank)
    # Sort by score desc, then doc_id for deterministic tie-breaking (stable tests/evals).
    result = sorted(fused.items(), key=lambda x: (-x[1], x[0]))
    return result[:top_n] if top_n else result


def _min_max(scores: Mapping[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi == lo:  # all equal -> no information to rank by; give everyone 1.0
        return {d: 1.0 for d in scores}
    return {d: (s - lo) / (hi - lo) for d, s in scores.items()}


def weighted_fusion(
    bm25: RankedList, vector: RankedList, alpha: float = 0.5, top_n: int | None = None
) -> list[tuple[str, float]]:
    """alpha = weight of the vector retriever (0 = BM25 only, 1 = vector only).

    A doc missing from one list gets 0 from that retriever (it was not in its top results).
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    b = _min_max(dict(bm25))
    v = _min_max(dict(vector))
    fused = {d: alpha * v.get(d, 0.0) + (1 - alpha) * b.get(d, 0.0) for d in set(b) | set(v)}
    result = sorted(fused.items(), key=lambda x: (-x[1], x[0]))
    return result[:top_n] if top_n else result
