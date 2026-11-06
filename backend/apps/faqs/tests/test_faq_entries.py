from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.test_utils import auth_client, create_user
from apps.faqs.models import FAQEntry


class FAQEntryCRUDTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="owner@example.com")
        self.client = auth_client(self.user)

    def test_create_faq_entry_computes_embedding(self):
        url = reverse("faqentry-list")
        response = self.client.post(url, {"question": "Q1?", "answer": "A1."})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        entry = FAQEntry.objects.get(id=response.data["id"])
        self.assertEqual(entry.user, self.user)
        # pgvector-django returns VectorField values as numpy arrays on
        # Postgres, and assertTrue(array) raises "ambiguous truth value"
        # for arrays with more than one element — assertIsNotNone + len()
        # work identically on both the Postgres array and SQLite's list.
        self.assertIsNotNone(entry.embedding)
        self.assertEqual(len(entry.embedding), 1536)
        # Embedding response should not leak the raw vector over the API.
        self.assertNotIn("embedding", response.data)

    def test_update_faq_entry_recomputes_embedding(self):
        entry = FAQEntry.objects.create(user=self.user, question="Old?", answer="Old answer.")
        old_embedding = list(entry.embedding)

        url = reverse("faqentry-detail", args=[entry.id])
        response = self.client.patch(url, {"answer": "Brand new answer."})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        entry.refresh_from_db()
        # pgvector-django returns VectorField values as numpy arrays on
        # Postgres (vs plain lists from SQLite's JSONField fallback);
        # comparing arrays directly raises "ambiguous truth value" under
        # assertNotEqual, so cast to list first to compare on either backend.
        self.assertNotEqual(list(entry.embedding), old_embedding)

    def test_list_and_delete(self):
        FAQEntry.objects.create(user=self.user, question="Q1?", answer="A1.")
        FAQEntry.objects.create(user=self.user, question="Q2?", answer="A2.")

        list_response = self.client.get(reverse("faqentry-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 2)

        entry_id = list_response.data["results"][0]["id"]
        delete_response = self.client.delete(reverse("faqentry-detail", args=[entry_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FAQEntry.objects.filter(id=entry_id).exists())

    def test_blank_question_rejected(self):
        response = self.client.post(reverse("faqentry-list"), {"question": "   ", "answer": "A."})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_request_rejected(self):
        from rest_framework.test import APIClient

        anon_client = APIClient()
        response = anon_client.get(reverse("faqentry-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FAQEntryCrossUserIsolationTests(APITestCase):
    def setUp(self):
        self.user_a = create_user(email="a@example.com")
        self.user_b = create_user(email="b@example.com")
        self.client_a = auth_client(self.user_a)
        self.client_b = auth_client(self.user_b)

        self.entry_a = FAQEntry.objects.create(user=self.user_a, question="A's question?", answer="A's answer.")
        self.entry_b = FAQEntry.objects.create(user=self.user_b, question="B's question?", answer="B's answer.")

    def test_list_only_shows_own_entries(self):
        response = self.client_a.get(reverse("faqentry-list"))
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(self.entry_a.id, ids)
        self.assertNotIn(self.entry_b.id, ids)

    def test_cannot_retrieve_other_users_entry(self):
        response = self.client_a.get(reverse("faqentry-detail", args=[self.entry_b.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_other_users_entry(self):
        response = self.client_a.patch(reverse("faqentry-detail", args=[self.entry_b.id]), {"answer": "Hacked"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.entry_b.refresh_from_db()
        self.assertEqual(self.entry_b.answer, "B's answer.")

    def test_cannot_delete_other_users_entry(self):
        response = self.client_a.delete(reverse("faqentry-detail", args=[self.entry_b.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(FAQEntry.objects.filter(id=self.entry_b.id).exists())
