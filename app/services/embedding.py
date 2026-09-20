"""Local BGE embedding adapter; model weights never leave the configured path."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from app.core.exceptions import MatchCalculationError

DEFAULT_EMBEDDING_MODEL_PATH = Path("E:/00project/02agent/models/bge-large-zh-v1.5")


class EmbeddingClient(Protocol):
    model_id: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class BGEEmbeddingClient:
    """Lazily load bge-large-zh-v1.5 from local storage."""

    model_id = "bge-large-zh-v1.5"

    def __init__(
        self,
        model_path: Path | str = DEFAULT_EMBEDDING_MODEL_PATH,
        *,
        device: str = "cpu",
        loader: Callable[[Path, str], Any] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.device = device
        self._loader = loader or _load_sentence_transformer
        self._model: Any | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        try:
            encoded = model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            values = encoded.tolist() if hasattr(encoded, "tolist") else encoded
            return [[float(value) for value in vector] for vector in values]
        except Exception:
            raise MatchCalculationError(
                "Local embedding inference failed for bge-large-zh-v1.5."
            ) from None

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        if not self.model_path.is_dir():
            raise MatchCalculationError(
                "Local embedding model directory does not exist: " + str(self.model_path)
            )
        try:
            self._model = self._loader(self.model_path, self.device)
        except Exception:
            raise MatchCalculationError(
                "Local embedding model could not be loaded: bge-large-zh-v1.5."
            ) from None
        return self._model


def _load_sentence_transformer(model_path: Path, device: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        str(model_path),
        device=device,
        local_files_only=True,
    )
