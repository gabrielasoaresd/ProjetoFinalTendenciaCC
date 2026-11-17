from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Protocol


class Embedder(Protocol):
    dimension: int
    def encode(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Vetorizador offline por n-gramas de caracteres com dimensão fixa.

    É útil para reprodução sem download de modelos; não equivale a embeddings semânticos
    produzidos por Transformers. Para avaliação semântica, use SentenceTransformerEmbedder.
    """
    def __init__(self, dimension: int = 384):
        if dimension < 32:
            raise ValueError("A dimensão do embedding deve ser >= 32")
        self.dimension = dimension

    def encode(self, text: str) -> list[float]:
        normalized = re.sub(r"\s+", " ", (text or "").lower().strip())
        if not normalized:
            return [0.0] * self.dimension
        padded = f"  {normalized}  "
        features = Counter()
        words = re.findall(r"[\w-]+", normalized, flags=re.UNICODE)
        for word in words:
            features[f"w:{word}"] += 1.0
        for n in (2, 3, 4, 5):
            for i in range(max(0, len(padded) - n + 1)):
                features[f"c:{padded[i:i+n]}"] += 0.35
        vector = [0.0] * self.dimension
        for feature, count in features.items():
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            slot = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[slot] += sign * count
        norm = math.sqrt(sum(v * v for v in vector))
        if norm:
            vector = [v / norm for v in vector]
        return vector


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, dimension: int = 384):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Instale requirements-semantic.txt para usar embeddings semânticos."
            ) from exc
        self.model = SentenceTransformer(model_name)
        self.dimension = int(self.model.get_sentence_embedding_dimension())
        if self.dimension != dimension:
            raise ValueError(
                f"Modelo retorna {self.dimension} dimensões, mas EMBEDDING_DIMENSIONS={dimension}."
            )

    def encode(self, text: str) -> list[float]:
        vector = self.model.encode(text, normalize_embeddings=True)
        return [float(value) for value in vector.tolist()]


def make_embedder(provider: str = "hash", dimension: int = 384, model_name: str = "") -> Embedder:
    if provider in {"sentence-transformers", "sentence_transformers", "transformer"}:
        return SentenceTransformerEmbedder(model_name, dimension)
    if provider == "hash":
        return HashEmbedder(dimension)
    raise ValueError(f"EMBEDDING_PROVIDER não suportado: {provider}")
