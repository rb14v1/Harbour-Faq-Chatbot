"""
Backend-agnostic nearest-neighbour similarity search, matching the dual
storage strategy in embedding_field.py.

On Postgres, `field_name` is a pgvector VectorField, so the DB itself can
rank rows by cosine distance via an ORDER BY clause (fast, index-friendly
with pgvector's ivfflat/hnsw indexes).

On SQLite, `field_name` is a plain JSONField (list of floats). There is no
DB-side vector math available, so candidates are pulled into Python and
ranked there. Fine for small dev datasets; not meant to scale.

Both branches return a plain list of model instances (not a queryset),
nearest-first, length <= top_k, so callers never need to know which backend
produced the result.
"""
import math

from django.conf import settings


def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def similarity_search(queryset, query_vector, top_k=3, field_name="embedding"):
    """
    Return the top_k instances in `queryset` whose `field_name` embedding is
    most similar (cosine similarity) to `query_vector`, nearest-first.

    Each returned instance gets a `similarity_score` attribute (float in
    [-1, 1], higher = more similar) attached, so callers can display it
    without recomputing.
    """
    if top_k <= 0:
        return []

    if getattr(settings, "USE_SQLITE", False):
        candidates = list(queryset)
        scored = []
        for obj in candidates:
            vector = getattr(obj, field_name) or []
            if not vector:
                continue
            score = _cosine_similarity(query_vector, vector)
            scored.append((score, obj))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:top_k]
        results = []
        for score, obj in top:
            obj.similarity_score = score
            results.append(obj)
        return results

    # Postgres: let pgvector do the ranking in the database.
    from pgvector.django import CosineDistance

    annotated = queryset.annotate(
        _distance=CosineDistance(field_name, query_vector)
    ).order_by("_distance")[:top_k]

    results = []
    for obj in annotated:
        # Cosine distance (pgvector) = 1 - cosine similarity.
        obj.similarity_score = 1 - obj._distance
        results.append(obj)
    return results
