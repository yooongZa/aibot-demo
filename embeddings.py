"""Embedding-based need matching (stub).

Behaviour:
- If `sentence-transformers` is installed AND a model can be loaded, expose
  `encode(text)` and `cosine(a, b)` so `match_need_semantically()` can rank
  the canonical need labels by similarity to the user's free-form text.
- Otherwise, gracefully fall back to the existing keyword detector in
  data.detect_needs(), so this module is safe to import in any environment.

To activate locally:
    pip install sentence-transformers
    export EMBEDDING_MODEL=jhgan/ko-sroberta-multitask  # Korean SBERT
"""

from __future__ import annotations

import os
from functools import lru_cache

from data import NEED_KEYWORDS, detect_needs

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
SIMILARITY_THRESHOLD = float(os.getenv("EMBEDDING_THRESHOLD", "0.45"))


@lru_cache(maxsize=1)
def _try_load_model():
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        return SentenceTransformer(EMBEDDING_MODEL)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _need_label_embeddings():
    model = _try_load_model()
    if model is None:
        return None
    labels = list(NEED_KEYWORDS.keys())
    vecs = model.encode(labels, normalize_embeddings=True)
    return labels, vecs


def match_need_semantically(text: str) -> list[str]:
    """Return needs ordered by semantic similarity, falling back to keywords.

    Always returns the keyword-based result as the floor, then adds any
    semantically-similar needs not already present (above threshold).
    """
    keyword_needs = detect_needs(text)

    cached = _need_label_embeddings()
    model = _try_load_model()
    if cached is None or model is None:
        return keyword_needs

    labels, label_vecs = cached
    query_vec = model.encode([text], normalize_embeddings=True)[0]
    sims = (label_vecs @ query_vec).tolist()
    ranked = sorted(zip(labels, sims), key=lambda x: x[1], reverse=True)

    extra: list[str] = []
    for label, sim in ranked:
        if sim < SIMILARITY_THRESHOLD:
            break
        if label not in keyword_needs and label not in extra:
            extra.append(label)

    return keyword_needs + extra
