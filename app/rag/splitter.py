"""Deterministic token-span chunking that preserves original source text."""

import re
from dataclasses import dataclass

from app.core.exceptions import RetrievalError
from app.rag.loader import KnowledgeDocument

TOKEN_PATTERN = re.compile(r"[㐀-鿿]|[A-Za-z0-9_+#.-]+|[^\s]")


@dataclass(frozen=True)
class KnowledgeChunk:
    doc_id: str
    chunk_id: str
    source: str
    content: str


def split_documents(
    documents: list[KnowledgeDocument],
    *,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
) -> list[KnowledgeChunk]:
    if chunk_size < 1 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise RetrievalError("Chunk size must be positive and overlap smaller than the chunk.")
    chunks: list[KnowledgeChunk] = []
    for document in documents:
        spans = [match.span() for match in TOKEN_PATTERN.finditer(document.content)]
        if not spans:
            continue
        start_token = 0
        chunk_index = 0
        while start_token < len(spans):
            end_token = min(start_token + chunk_size, len(spans))
            start_char = spans[start_token][0]
            end_char = spans[end_token - 1][1]
            content = document.content[start_char:end_char].strip()
            if content:
                chunks.append(
                    KnowledgeChunk(
                        doc_id=document.doc_id,
                        chunk_id=f"{document.doc_id}:{chunk_index}",
                        source=document.source,
                        content=content,
                    )
                )
                chunk_index += 1
            if end_token == len(spans):
                break
            start_token = end_token - chunk_overlap
    return chunks
