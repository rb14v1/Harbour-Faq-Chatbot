from django.test import TestCase

from apps.common.test_utils import create_user, pad_vector
from apps.common.vector_search import similarity_search
from apps.faqs.models import FAQEntry


class SimilaritySearchTests(TestCase):
    """Constructs FAQEntry rows with known, hand-picked embedding vectors
    (bypassing the normal stub-embedding save() path by setting .embedding
    directly after save) so ranking correctness can be verified exactly,
    independent of what get_embedding() happens to produce. Vectors are
    hand-crafted short for readability, then padded to EMBEDDING_DIMENSIONS
    via pad_vector() — real Postgres pgvector columns reject any other
    length, while SQLite's JSONField fallback doesn't enforce one."""

    def setUp(self):
        self.user = create_user(email="search@example.com")

        def make(question, vector):
            entry = FAQEntry.objects.create(user=self.user, question=question, answer="answer")
            entry.embedding = pad_vector(vector)
            entry.save(update_fields=["embedding"])
            return entry

        # Orthonormal-ish basis vectors in a small space so cosine similarity
        # is easy to reason about by hand.
        self.exact_match = make("exact", [1.0, 0.0, 0.0])
        self.close_match = make("close", [0.9, 0.1, 0.0])
        self.orthogonal = make("orthogonal", [0.0, 1.0, 0.0])
        self.opposite = make("opposite", [-1.0, 0.0, 0.0])

    def test_nearest_first_ordering(self):
        query = pad_vector([1.0, 0.0, 0.0])
        qs = FAQEntry.objects.filter(user=self.user)
        results = similarity_search(qs, query, top_k=4, field_name="embedding")

        ids_in_order = [r.id for r in results]
        self.assertEqual(
            ids_in_order,
            [self.exact_match.id, self.close_match.id, self.orthogonal.id, self.opposite.id],
        )

    def test_scores_reflect_cosine_similarity(self):
        query = pad_vector([1.0, 0.0, 0.0])
        qs = FAQEntry.objects.filter(user=self.user)
        results = similarity_search(qs, query, top_k=4, field_name="embedding")
        scores = {r.id: r.similarity_score for r in results}

        self.assertAlmostEqual(scores[self.exact_match.id], 1.0, places=5)
        self.assertAlmostEqual(scores[self.orthogonal.id], 0.0, places=5)
        self.assertAlmostEqual(scores[self.opposite.id], -1.0, places=5)
        self.assertGreater(scores[self.close_match.id], scores[self.orthogonal.id])

    def test_top_k_limits_result_count(self):
        query = pad_vector([1.0, 0.0, 0.0])
        qs = FAQEntry.objects.filter(user=self.user)
        results = similarity_search(qs, query, top_k=2, field_name="embedding")
        self.assertEqual(len(results), 2)
        self.assertEqual([r.id for r in results], [self.exact_match.id, self.close_match.id])

    def test_top_k_zero_returns_empty(self):
        qs = FAQEntry.objects.filter(user=self.user)
        results = similarity_search(qs, pad_vector([1.0, 0.0, 0.0]), top_k=0, field_name="embedding")
        self.assertEqual(results, [])
