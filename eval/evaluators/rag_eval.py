"""Reproducible Hit@K calculation for the fixed Day 6 retrieval cases."""

from typing import Protocol

from app.schemas.learning import RetrievedDocument


class Searcher(Protocol):
    def search(self, query: str, *, top_k: int) -> list[RetrievedDocument]: ...


def evaluate_hit_at_k(
    searcher: Searcher,
    cases: list[dict],
    *,
    top_k: int = 4,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    hits = 0
    for case in cases:
        retrieved = searcher.search(case["query"], top_k=top_k)
        actual = [document.doc_id for document in retrieved]
        expected = set(case["expected_doc_ids"])
        hit = bool(expected & set(actual))
        hits += int(hit)
        results.append(
            {
                "id": case["id"],
                "hit": hit,
                "expected_doc_ids": sorted(expected),
                "retrieved_doc_ids": actual,
            }
        )
    total = len(cases)
    return {
        "metric": f"Hit@{top_k}",
        "hits": hits,
        "total": total,
        "value": hits / total if total else 0.0,
        "cases": results,
    }
