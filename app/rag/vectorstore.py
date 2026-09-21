"""Minimal in-memory FAISS vector store for the curated learning corpus."""

import math
from typing import Any

from app.core.exceptions import RetrievalError
from app.rag.splitter import KnowledgeChunk
from app.schemas.learning import RetrievedDocument
from app.services.embedding import EmbeddingClient


class FaissVectorStore:
    def __init__(self, embedding: EmbeddingClient) -> None:
        self.embedding = embedding
        self._index: Any | None = None
        self._chunks: list[KnowledgeChunk] = []

    @property
    def size(self) -> int:
        return len(self._chunks)

    def build(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            self._index = None
            self._chunks = []
            return
        vectors = self.embedding.embed_documents([chunk.content for chunk in chunks])
        _validate_vectors(vectors, len(chunks))
        try:
            import faiss
            import numpy as np

            matrix = np.asarray(vectors, dtype="float32")
            index = faiss.IndexFlatIP(matrix.shape[1])
            index.add(matrix)
        except Exception:
            raise RetrievalError("FAISS index could not be built.") from None
        self._index = index
        self._chunks = list(chunks)

    def search(
        self,
        query: str,
        *,
        top_k: int = 4,
        min_score: float | None = None,
    ) -> list[RetrievedDocument]:
        if not query.strip():
            raise RetrievalError("Retrieval query must not be empty.")
        if top_k < 1:
            raise RetrievalError("top_k must be at least 1.")
        if self._index is None or not self._chunks:
            return []
        vectors = self.embedding.embed_documents([query])
        _validate_vectors(vectors, 1)
        try:
            import numpy as np

            scores, indexes = self._index.search(
                np.asarray(vectors, dtype="float32"),
                min(top_k, len(self._chunks)),
            )
        except Exception:
            raise RetrievalError("FAISS search failed.") from None
        results: list[RetrievedDocument] = []
        for score, index in zip(scores[0].tolist(), indexes[0].tolist()):
            if index < 0 or (min_score is not None and score < min_score):
                continue
            chunk = self._chunks[index]
            results.append(
                RetrievedDocument(
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    source=chunk.source,
                    score=float(score),
                )
            )
        return results


def _validate_vectors(vectors: list[list[float]], expected_count: int) -> None:
    if len(vectors) != expected_count or not vectors:
        raise RetrievalError("Embedding client returned an unexpected vector count.")
    dimension = len(vectors[0])
    if dimension < 1 or any(len(vector) != dimension for vector in vectors):
        raise RetrievalError("Embedding client returned inconsistent dimensions.")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise RetrievalError("Embedding client returned non-finite values.")
