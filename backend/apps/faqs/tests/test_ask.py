from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.test_utils import auth_client, create_user
from apps.faqs.models import ChatLog, FAQEntry


class AskEndpointTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="asker@example.com")
        self.client = auth_client(self.user)
        self.faq1 = FAQEntry.objects.create(
            user=self.user, question="How do I cancel?", answer="Go to settings and cancel."
        )
        self.faq2 = FAQEntry.objects.create(
            user=self.user, question="How do I upgrade?", answer="Go to billing and upgrade."
        )

    def test_ask_returns_stub_answer_and_matches(self):
        url = reverse("faq-ask")
        response = self.client.post(url, {"question": "How do I cancel my plan?"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertIn("[STUB AI RESPONSE", response.data["answer"])
        self.assertIn("Found 2 related FAQ(s)", response.data["answer"])

        matched_faqs = response.data["matched_faqs"]
        self.assertEqual(len(matched_faqs), 2)
        matched_ids = {m["id"] for m in matched_faqs}
        self.assertEqual(matched_ids, {self.faq1.id, self.faq2.id})
        for match in matched_faqs:
            self.assertIn("question", match)
            self.assertIn("answer", match)
            self.assertIn("score", match)

    def test_ask_creates_chat_log(self):
        url = reverse("faq-ask")
        self.assertEqual(ChatLog.objects.count(), 0)
        response = self.client.post(url, {"question": "How do I cancel?"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(ChatLog.objects.count(), 1)
        log = ChatLog.objects.first()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.question_asked, "How do I cancel?")
        self.assertEqual(log.generated_answer, response.data["answer"])
        self.assertEqual(set(log.matched_faq_ids), {self.faq1.id, self.faq2.id})

    def test_ask_with_no_faqs_returns_empty_matches(self):
        FAQEntry.objects.all().delete()
        response = self.client.post(reverse("faq-ask"), {"question": "Anything?"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matched_faqs"], [])
        self.assertIn("Found 0 related FAQ(s)", response.data["answer"])

    def test_ask_requires_question(self):
        response = self.client.post(reverse("faq-ask"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ask_respects_top_k_setting(self):
        from django.test import override_settings

        FAQEntry.objects.create(user=self.user, question="Q3", answer="A3")
        with override_settings(ASK_TOP_K=1):
            response = self.client.post(reverse("faq-ask"), {"question": "cancel"})
        self.assertEqual(len(response.data["matched_faqs"]), 1)


class AskEndpointIsolationTests(APITestCase):
    def setUp(self):
        self.user_a = create_user(email="a@example.com")
        self.user_b = create_user(email="b@example.com")
        self.client_a = auth_client(self.user_a)

        self.faq_a = FAQEntry.objects.create(user=self.user_a, question="A question?", answer="A answer.")
        self.faq_b = FAQEntry.objects.create(user=self.user_b, question="B question?", answer="B answer.")

    def test_ask_never_matches_another_users_faqs(self):
        response = self.client_a.post(reverse("faq-ask"), {"question": "question"})
        matched_ids = {m["id"] for m in response.data["matched_faqs"]}
        self.assertIn(self.faq_a.id, matched_ids)
        self.assertNotIn(self.faq_b.id, matched_ids)

    def test_chat_log_list_isolated_per_user(self):
        self.client_a.post(reverse("faq-ask"), {"question": "question A"})

        client_b = auth_client(self.user_b)
        client_b.post(reverse("faq-ask"), {"question": "question B"})

        response_a = self.client_a.get(reverse("chatlog-list"))
        questions_a = [row["question_asked"] for row in response_a.data["results"]]
        self.assertIn("question A", questions_a)
        self.assertNotIn("question B", questions_a)

    def test_cannot_retrieve_other_users_chat_log(self):
        self.client_a.post(reverse("faq-ask"), {"question": "question A"})
        from apps.faqs.models import ChatLog

        log_a = ChatLog.objects.get(user=self.user_a)

        client_b = auth_client(self.user_b)
        response = client_b.get(reverse("chatlog-detail", args=[log_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
