from django.conf import settings
from django.db import models

from apps.common.ai import get_embedding
from apps.common.embedding_field import EmbeddingField


class FAQEntry(models.Model):
    """A curated FAQ question/answer pair owned by a single user. Its
    embedding (of "question\\nanswer") is (re)computed on every save() so it
    always reflects the latest text, per the RAG pipeline used by
    apps.faqs.views.AskView."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faq_entries")
    question = models.TextField()
    answer = models.TextField()
    embedding = EmbeddingField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:60]

    def compute_embedding(self):
        """Embed "question\\nanswer" as a single unit, per spec, so the
        stored vector captures both what's being asked and how it's
        answered."""
        text = f"{self.question}\n{self.answer}"
        self.embedding = get_embedding(text)

    def save(self, *args, **kwargs):
        # Recompute on create (no update_fields) and on any save that
        # touches question/answer, since that's what the embedding is
        # derived from. Skip recompute when update_fields explicitly
        # targets other fields only (e.g. directly setting .embedding in
        # tests, or touching unrelated fields) so that path isn't clobbered.
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "question" in update_fields or "answer" in update_fields:
            self.compute_embedding()
        super().save(*args, **kwargs)


class ChatLog(models.Model):
    """History of questions asked through /api/ask/, with the answer that
    was generated and which FAQEntry ids were used as context."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_logs")
    question_asked = models.TextField()
    generated_answer = models.TextField()
    matched_faq_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question_asked[:60]
