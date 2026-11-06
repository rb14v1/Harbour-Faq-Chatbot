"""
Embedding column definition, shared by every model that stores a vector
(currently apps.faqs.models.FAQEntry).

Postgres (production / docker-compose): uses pgvector's VectorField, backed
by the `vector` extension (`CREATE EXTENSION vector`, applied by a
RunPython migration guard - see apps/faqs/migrations/0001_initial.py). This
enables fast, index-friendly nearest-neighbour search via
pgvector.django.CosineDistance (see vector_search.py).

SQLite (dev-only, USE_SQLITE=True): pgvector has no SQLite backend, so we
fall back to a plain JSONField storing a list of floats. Similarity search
over SQLite is done in plain Python (see vector_search.py). This keeps the
whole pipeline runnable and testable on a machine with no Postgres/pgvector
install, while Postgres deployments get the real vector column.

Both branches expose a field under the same attribute name/signature so
calling code (models, serializers) never has to branch on backend.
"""
from django.conf import settings
from django.db import models

# Default dimensionality of stored embeddings. OpenAI's text-embedding-3-large
# is natively 3072-dimensional but supports a `dimensions` param to shorten
# the output vector; 1536 is used by default to keep the column smaller.
# Overridable via the OPENAI_EMBEDDING_DIMENSIONS env var (see
# config/settings/base.py, which is what settings.EMBEDDING_DIMENSIONS reads
# from - this module falls back to the same default if settings aren't
# configured for some reason, e.g. being imported outside Django).
EMBEDDING_DIMENSIONS = getattr(settings, "EMBEDDING_DIMENSIONS", 1536)


def EmbeddingField(**kwargs):
    """
    Factory returning the correct field instance for the active database
    backend. Call it at class-definition time in a model, e.g.:

        embedding = EmbeddingField(null=True, blank=True)
    """
    dimensions = kwargs.pop("dimensions", EMBEDDING_DIMENSIONS)

    if getattr(settings, "USE_SQLITE", False):
        return models.JSONField(default=list, **kwargs)

    # Imported lazily so this module (and anything importing it, e.g. for
    # SQLite-only test runs) doesn't require the `pgvector` package's C
    # extension registration machinery unless Postgres is actually in use.
    from pgvector.django import VectorField

    return VectorField(dimensions=dimensions, **kwargs)
