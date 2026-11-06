"""
Verifies the data migration in apps/faqs/migrations/0002_seed_demo_data.py.

By the time Django's test runner builds the test database it has already
run every migration (including this data migration), so the seeded demo
user/FAQEntry rows are simply present in the DB when these tests run - no
need to invoke the migration manually. (The migration module's name starts
with a digit so it isn't importable as `apps.faqs.migrations.0002_...`;
expected values are duplicated here instead of imported.)
"""
from django.test import TestCase

from apps.accounts.models import User
from apps.faqs.models import FAQEntry

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"
EXPECTED_FAQ_COUNT = 15


class SeedMigrationTests(TestCase):
    def test_demo_user_created(self):
        user = User.objects.get(email=DEMO_EMAIL)
        self.assertTrue(user.check_password(DEMO_PASSWORD))
        self.assertTrue(user.is_active)

    def test_seed_faq_count(self):
        user = User.objects.get(email=DEMO_EMAIL)
        count = FAQEntry.objects.filter(user=user).count()
        self.assertEqual(count, EXPECTED_FAQ_COUNT)

    def test_all_seed_faqs_have_embeddings(self):
        user = User.objects.get(email=DEMO_EMAIL)
        for entry in FAQEntry.objects.filter(user=user):
            # pgvector-django returns VectorField values as numpy arrays on
            # Postgres, and assertTrue(array) raises "ambiguous truth value"
            # for arrays with more than one element — assertIsNotNone + len()
            # work identically on both the Postgres array and SQLite's list.
            self.assertIsNotNone(entry.embedding, f"FAQEntry {entry.id} has no embedding")
            self.assertEqual(len(entry.embedding), 1536)

    def test_seed_faqs_have_distinct_questions(self):
        user = User.objects.get(email=DEMO_EMAIL)
        questions = list(FAQEntry.objects.filter(user=user).values_list("question", flat=True))
        self.assertEqual(len(questions), len(set(questions)))
