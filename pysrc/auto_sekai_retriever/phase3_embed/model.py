from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Iterable, Protocol

from auto_sekai_retriever.config import Phase3Config


class TextEmbedder(Protocol):
    model_name: str
    dimension: int
    pooling: str

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        ...


def l2_normalize(vector: Iterable[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("embedding vector must not be zero")
    return [value / norm for value in values]


def validate_texts(texts: list[str]) -> None:
    if not texts:
        raise ValueError("texts must not be empty")
    for text in texts:
        if not text or not text.strip():
            raise ValueError("text entries must not be empty")


@dataclass
class SentenceTransformerEmbedder:
    config: Phase3Config

    def __post_init__(self) -> None:
        os.environ.setdefault("HF_HOME", str(self.config.cache_root))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(self.config.cache_root))
        os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(self.config.cache_root))
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for phase3 embedding generation. "
                "Run `uv sync` first."
            ) from exc

        self._model = SentenceTransformer(
            self.config.embedding_model,
            cache_folder=str(self.config.cache_root),
            trust_remote_code=False,
        )
        sample = self.encode_texts(["测试"])
        self.model_name = self.config.embedding_model
        self.pooling = self.config.embedding_pooling
        self.dimension = len(sample[0])

    model_name: str = ""
    dimension: int = 0
    pooling: str = "none"

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        validate_texts(texts)
        raw_vectors = self._model.encode(
            texts,
            batch_size=self.config.embedding_batch_size,
            normalize_embeddings=False,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        normalized = [l2_normalize(vector.tolist()) for vector in raw_vectors]
        if not normalized:
            raise ValueError("encoder returned no vectors")
        expected_dimension = len(normalized[0])
        for vector in normalized:
            if len(vector) != expected_dimension:
                raise ValueError("embedding dimensions are inconsistent")
        return normalized
