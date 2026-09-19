"""Deterministic local embedding baseline for project relevance."""

import hashlib
import math
import re
from typing import Protocol

TOKEN_PATTERN = re.compile(r"[\w+#.-]+", re.UNICODE)


class EmbeddingClient(Protocol):
    model_id: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbeddingClient:
    """Map lexical features to fixed vectors without network or mutable state."""

    model_id = "local-hash-v1"

    def __init__(self, dimensions: int = 384) -> None:
        if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions < 8:
            raise ValueError("Embedding dimensions must be an integer of at least 8.")
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for feature in _features(text):
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


def _features(text: str) -> list[str]:
    tokens = [token.casefold().strip("._-") for token in TOKEN_PATTERN.findall(text)]
    tokens = [token for token in tokens if token]
    features = [f"word:{token}" for token in tokens]
    features.extend(f"pair:{left}|{right}" for left, right in zip(tokens, tokens[1:]))
    return features
