from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.ai import generate_answer, get_embedding
from apps.common.vector_search import similarity_search
from apps.faqs.models import ChatLog, FAQEntry
from apps.faqs.serializers import (
    AskRequestSerializer,
    AskResponseSerializer,
    ChatLogSerializer,
    FAQEntrySerializer,
)


class FAQEntryViewSet(viewsets.ModelViewSet):
    serializer_class = FAQEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FAQEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only history of the user's own /api/ask/ requests."""

    serializer_class = ChatLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatLog.objects.filter(user=self.request.user)


class AskView(APIView):
    """
    RAG endpoint: embed the question, find the user's own top-k most similar
    FAQEntry rows, generate an answer grounded in them, log the exchange,
    and return the answer plus the matched FAQs (with similarity scores).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_serializer = AskRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        question = request_serializer.validated_data["question"]

        query_vector = get_embedding(question)

        top_k = getattr(settings, "ASK_TOP_K", 3)
        user_faqs = FAQEntry.objects.filter(user=request.user)
        top_matches = similarity_search(user_faqs, query_vector, top_k=top_k, field_name="embedding")

        context_snippets = [f"{faq.question}: {faq.answer}" for faq in top_matches]
        answer = generate_answer(question, context_snippets)

        matched_faq_ids = [faq.id for faq in top_matches]
        ChatLog.objects.create(
            user=request.user,
            question_asked=question,
            generated_answer=answer,
            matched_faq_ids=matched_faq_ids,
        )

        matched_faqs = [
            {
                "id": faq.id,
                "question": faq.question,
                "answer": faq.answer,
                "score": faq.similarity_score,
            }
            for faq in top_matches
        ]

        response_serializer = AskResponseSerializer({"answer": answer, "matched_faqs": matched_faqs})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
