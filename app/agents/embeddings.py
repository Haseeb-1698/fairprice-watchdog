"""
embeddings.py — 384-dim sentence embeddings (matches Eman's Vector(384) column).

Uses sentence-transformers `all-MiniLM-L6-v2` (384 dims). Lazy + optional: if the
package/model isn't available, `embed()` returns None and callers fall back to
keyword matching. The model is cached after first load.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384
_model = None
_unavailable = False


def _get_model():
    global _model, _unavailable
    if _model is not None or _unavailable:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Loaded embedding model %s (%d dims)", MODEL_NAME, DIM)
        return _model
    except Exception as e:
        logger.warning("Embeddings unavailable (%s) — Law-Mapper will use keyword matching", e)
        _unavailable = True
        return None


def available() -> bool:
    return _get_model() is not None


def embed(texts: list[str]) -> Optional[list[list[float]]]:
    """Embed a list of texts → list of 384-float vectors, or None if unavailable."""
    model = _get_model()
    if model is None:
        return None
    try:
        vecs = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
    except Exception as e:
        logger.warning("embed() failed: %s", e)
        return None


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity. Vectors are L2-normalized on encode, so this is a dot product."""
    return sum(x * y for x, y in zip(a, b))
