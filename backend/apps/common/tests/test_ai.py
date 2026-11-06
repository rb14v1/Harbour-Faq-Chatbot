from django.conf import settings
from django.test import TestCase

from apps.common.ai import generate_answer, get_embedding


class StubEmbeddingTests(TestCase):
    """No OPENAI_API_KEY is configured in the test environment, so
    get_embedding() must use the deterministic stub path."""

    def test_embedding_has_configured_dimensions(self):
        vector = get_embedding("What is your refund policy?")
        self.assertEqual(len(vector), settings.EMBEDDING_DIMENSIONS)

    def test_embedding_is_deterministic_for_same_text(self):
        v1 = get_embedding("How do I cancel my subscription?")
        v2 = get_embedding("How do I cancel my subscription?")
        self.assertEqual(v1, v2)

    def test_embedding_differs_for_different_text(self):
        v1 = get_embedding("How do I cancel my subscription?")
        v2 = get_embedding("What payment methods do you accept?")
        self.assertNotEqual(v1, v2)

    def test_embedding_is_l2_normalized(self):
        vector = get_embedding("Some arbitrary question")
        norm = sum(x * x for x in vector) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=5)


class StubAnswerTests(TestCase):
    def test_answer_format_with_matches(self):
        answer = generate_answer("How do I cancel?", ["Cancel: go to settings.", "Other: other answer."])
        self.assertIn("[STUB AI RESPONSE", answer)
        self.assertIn("Found 2 related FAQ(s)", answer)
        self.assertIn("Cancel: go to settings.", answer)

    def test_answer_format_with_no_matches(self):
        answer = generate_answer("Unanswerable question", [])
        self.assertIn("Found 0 related FAQ(s)", answer)
        self.assertIn("Top match: none", answer)
