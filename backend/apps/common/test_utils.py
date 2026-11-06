from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


def create_user(email="user@example.com", password="StrongPass123!", **kwargs):
    return User.objects.create_user(email=email, password=password, **kwargs)


def pad_vector(short_vector):
    """Pad a short, hand-crafted test vector (e.g. [1.0, 0.0, 0.0]) out to
    EMBEDDING_DIMENSIONS with trailing zeros. Cosine similarity depends only
    on the non-zero components, so this preserves the exact similarity math
    the test authors intended while satisfying Postgres pgvector's strict
    VectorField(dimensions=N) column constraint (SQLite's JSONField fallback
    has no such constraint, which is why short vectors worked there but
    raise `DataError: expected N dimensions, not 3` against real Postgres)."""
    dims = getattr(settings, "EMBEDDING_DIMENSIONS", 1536)
    return list(short_vector) + [0.0] * (dims - len(short_vector))


def auth_client(user) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client
