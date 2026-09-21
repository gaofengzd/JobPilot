"""Build and query the Day 6 learning-only retrieval pipeline."""

from pathlib import Path

from app.rag.loader import load_knowledge_documents
from app.rag.splitter import split_documents
from app.rag.vectorstore import FaissVectorStore
from app.schemas.gap import SkillGap
from app.schemas.learning import RetrievedDocument
from app.services.embedding import EmbeddingClient


class KnowledgeRetriever:
    def __init__(
        self,
        embedding: EmbeddingClient,
        *,
        top_k: int = 4,
        min_score: float | None = None,
    ) -> None:
        self.store = FaissVectorStore(embedding)
        self.top_k = top_k
        self.min_score = min_score

    def index_directory(self, directory: Path | str) -> int:
        chunks = split_documents(load_knowledge_documents(directory))
        self.store.build(chunks)
        return len(chunks)

    def retrieve(self, gap: SkillGap) -> list[RetrievedDocument]:
        query = (
            f"Learn {gap.skill}. Requirement type: {gap.requirement_type}. "
            f"Goal: practical concepts, implementation steps, and a verifiable exercise."
        )
        return self.store.search(query, top_k=self.top_k, min_score=self.min_score)
