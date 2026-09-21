"""Load a small, manually curated UTF-8 learning knowledge base."""

from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import RetrievalError

SUPPORTED_SUFFIXES = {".md", ".txt"}
MAX_DOCUMENT_BYTES = 1_000_000


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    source: str
    content: str


def load_knowledge_documents(directory: Path | str) -> list[KnowledgeDocument]:
    root = Path(directory)
    if not root.is_dir():
        raise RetrievalError("Knowledge directory does not exist or is not a directory.")

    documents: list[KnowledgeDocument] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path.suffix.casefold() not in SUPPORTED_SUFFIXES:
            continue
        if path.is_symlink():
            raise RetrievalError("Knowledge files must not be symbolic links.")
        try:
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                raise RetrievalError("Knowledge document exceeds the 1 MB limit.")
            content = path.read_text(encoding="utf-8-sig").strip()
        except UnicodeDecodeError:
            raise RetrievalError("Knowledge documents must be valid UTF-8 text.") from None
        except OSError:
            raise RetrievalError("Knowledge document could not be read.") from None
        if not content:
            continue
        relative = path.relative_to(root).as_posix()
        doc_id = relative.rsplit(".", 1)[0].replace("/", ":")
        documents.append(KnowledgeDocument(doc_id=doc_id, source=relative, content=content))
    return documents
