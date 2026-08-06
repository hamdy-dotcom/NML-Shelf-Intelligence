"""
Text embedding wrapper for genome matching.

Uses intfloat/multilingual-e5-base by default — 768-dim, strong Arabic support.
E5 models require a task prefix: "passage:" for documents being indexed,
"query:" for search-time lookups. Both are used here.

Model is loaded lazily on first call so importing this module is cheap.
"""
import logging

import numpy as np

from shared.config import settings

logger = logging.getLogger(__name__)


class TextEmbedder:
    def __init__(self, model_name: str = settings.genome_embedding_model) -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model %s (first use)", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        """Embed a document (listing title, product name) for storage."""
        vec = self._load().encode(f"passage: {text}", normalize_embeddings=True)
        return vec.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query for similarity lookup."""
        vec = self._load().encode(f"query: {text}", normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents; more efficient than one-by-one."""
        prefixed = [f"passage: {t}" for t in texts]
        vecs = self._load().encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        return vecs.tolist()


_embedder: TextEmbedder | None = None


def get_embedder() -> TextEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedder()
    return _embedder
